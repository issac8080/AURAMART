"""
Agentic AI for autonomous order and payment, using LangGraph.
Workflow: parse_intent -> extract_order_items (LLM) -> resolve_products (RAG/DB) -> create_order -> format_response.
Also exposes process_order(user_id, product_quantities, ...) for direct (product_id, qty) calls (e.g. habit reorder).
"""
import json
import os
import re
from datetime import datetime
from typing import List, Tuple, Optional, TypedDict, Literal

from app.models import OrderItem, DeliveryMethod
from app.order_service import create_order as order_service_create_order

from recommend.db import get_session
from recommend.models_db import Product, Order as DBOrder, OrderItem as DBOrderItem, User as DBUser
from recommend.rag_products import semantic_search_products, hybrid_search


# ----- Low-level: direct (product_id, qty) order (used by habit reorder and by graph's create_order node) -----


def resolve_items(product_quantities: List[Tuple[str, int]]) -> List[OrderItem]:
    """
    Resolve (product_id, quantity) to OrderItem list using current prices from DB.
    Skips products not found or out of stock.
    """
    session = get_session()
    try:
        items = []
        for pid, qty in product_quantities:
            if not pid or qty < 1:
                continue
            p = session.query(Product).filter(Product.id == pid).first()
            if not p:
                continue
            if not p.in_stock:
                continue
            items.append(
                OrderItem(product_id=pid, quantity=qty, price=float(p.price))
            )
        return items
    finally:
        session.close()


def _parse_iso(s: Optional[str]):
    if not s:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def _save_order_to_db(order) -> None:
    """Persist the created order (app.models.Order) to the recommend MySQL DB."""
    session = get_session()
    try:
        existing = session.query(DBOrder).filter(DBOrder.id == order.id).first()
        if existing:
            return
        user = session.query(DBUser).filter(DBUser.user_id == order.user_id).first()
        if not user:
            session.add(DBUser(user_id=order.user_id, name=None, email=None, phone=None))
            session.flush()
        created = _parse_iso(getattr(order, "created_at", None))
        updated = _parse_iso(getattr(order, "updated_at", None))
        db_order = DBOrder(
            id=order.id,
            user_id=order.user_id,
            total=float(order.total),
            delivery_method=order.delivery_method.value if hasattr(order.delivery_method, "value") else str(order.delivery_method),
            status=order.status.value if hasattr(order.status, "value") else str(order.status),
            delivery_address=order.delivery_address,
            store_location=order.store_location,
            qr_code=order.qr_code,
            created_at=created,
            updated_at=updated,
        )
        session.add(db_order)
        session.flush()
        for it in order.items:
            session.add(
                DBOrderItem(
                    order_id=order.id,
                    product_id=it.product_id,
                    quantity=it.quantity,
                    price=float(it.price),
                )
            )
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"Warning: could not save order to DB: {e}")
    finally:
        session.close()


def process_order(
    user_id: str,
    product_quantities: List[Tuple[str, int]],
    delivery_method: str = "home_delivery",
    delivery_address: Optional[str] = None,
    store_location: Optional[str] = None,
) -> dict:
    """
    Create order via order_service. Used by graph's create_order node and by habit reorder.
    Also persists the order to the recommend MySQL DB.
    Returns { success, order_id, total, message }.
    """
    items = resolve_items(product_quantities)
    if not items:
        return {
            "success": False,
            "order_id": None,
            "total": 0.0,
            "message": "No valid items (product not found or out of stock).",
        }
    dm = DeliveryMethod.HOME_DELIVERY if delivery_method == "home_delivery" else DeliveryMethod.STORE_PICKUP
    order = order_service_create_order(
        user_id=user_id,
        items=items,
        delivery_method=dm,
        delivery_address=delivery_address,
        store_location=store_location,
    )
    _save_order_to_db(order)
    total = sum(it.price * it.quantity for it in order.items)
    return {
        "success": True,
        "order_id": order.id,
        "total": round(total, 2),
        "message": f"Order {order.id} placed. Total ₹{total:.2f}. Status: {order.status.value}.",
    }


# ----- LangGraph state and workflow -----


class OrderAgentState(TypedDict, total=False):
    user_id: str
    message: str
    intent: str
    extracted_items: list
    resolved_items: list
    order_result: dict
    response_message: str
    error: Optional[str]


def _parse_intent(state: OrderAgentState) -> OrderAgentState:
    """Classify if user wants to place an order."""
    msg = (state.get("message") or "").strip().lower()
    order_keywords = ["order", "buy", "purchase", "add to cart", "get me", "send me", "place order", "checkout", "i want", "i need"]
    is_order = any(k in msg for k in order_keywords)
    return {"intent": "order" if is_order else "not_order"}


def _extract_order_items(state: OrderAgentState) -> OrderAgentState:
    """
    Find what to order by: (1) semantic + keyword search on message to get candidate products,
    (2) LLM picks product_id and quantity from that set by understanding the message.
    No hardcoded regex; product IDs are inferred from the message and catalog.
    """
    message = (state.get("message") or "").strip()
    if not message:
        return {"extracted_items": [], "error": "Empty message."}
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return {"extracted_items": [], "error": "OPENAI_API_KEY not set."}

    # 1) Get candidate products by searching the catalog with the message (semantic + keyword)
    candidates = hybrid_search(message, top_k_semantic=25, top_k_keyword=15)
    candidate_ids = set()
    catalog_lines = []
    for c in candidates:
        pid = c.get("product_id") or (c.get("metadata") or {}).get("product_id")
        if not pid or pid in candidate_ids:
            continue
        candidate_ids.add(pid)
        meta = c.get("metadata") or {}
        name = meta.get("name", pid)
        price = meta.get("price", 0)
        category = meta.get("category", "")
        catalog_lines.append(f"- {pid}: {name} (₹{price}, {category})")
        if len(catalog_lines) >= 40:
            break

    # 2) If user mentioned explicit product IDs (e.g. P00001), ensure those are in the candidate set
    session = get_session()
    try:
        for m in re.finditer(r"\bp(\d{3,5})\b", message.lower()):
            raw = m.group(1)
            pid = "P" + raw.upper().zfill(5) if len(raw) <= 5 else "P" + raw
            if pid in candidate_ids:
                continue
            p = session.query(Product).filter(Product.id == pid, Product.in_stock == True).first()
            if p:
                candidate_ids.add(pid)
                catalog_lines.append(f"- {p.id}: {p.name} (₹{p.price}, {p.category})")
    finally:
        session.close()

    if not catalog_lines:
        return {"extracted_items": [], "error": "No matching products found for the message."}

    catalog_text = "\n".join(catalog_lines)

    # 3) LLM: from message + candidates, output list of { product_id, quantity }
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        prompt = f"""You are an order extraction agent. The user said: "{message}"

Available products (use only these product_id values):
{catalog_text}

From the user's message, determine which product(s) they want to order and in what quantity. Infer quantity from words like "two", "2x", "a pair", "one", "1" (default 1). Return a JSON array of objects with exactly "product_id" and "quantity". Use only product_id values from the list above. Pick the best matching product(s) for what the user asked. Max 10 items. Return only the JSON array, no other text.
Example: [{{"product_id": "P00001", "quantity": 2}}, {{"product_id": "P00002", "quantity": 1}}]"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        extracted = json.loads(text)
        if not isinstance(extracted, list):
            extracted = [extracted]
        valid = []
        for item in extracted[:10]:
            if isinstance(item, dict) and item.get("product_id") and item["product_id"] in candidate_ids:
                qty = max(1, int(item.get("quantity", 1)))
                valid.append({"product_id": item["product_id"], "quantity": qty})
        return {"extracted_items": valid}
    except json.JSONDecodeError as e:
        return {"extracted_items": [], "error": f"Could not parse LLM response: {e}"}
    except Exception as e:
        return {"extracted_items": [], "error": str(e)}


def _resolve_products(state: OrderAgentState) -> OrderAgentState:
    """Resolve extracted_items to (product_id, quantity) using product_id or semantic search on description."""
    extracted = state.get("extracted_items") or []
    resolved = []
    session = get_session()
    try:
        for item in extracted:
            if isinstance(item, dict):
                pid = item.get("product_id")
                qty = max(1, int(item.get("quantity", 1)))
                if pid:
                    p = session.query(Product).filter(Product.id == pid, Product.in_stock == True).first()
                    if p:
                        resolved.append((p.id, qty))
                    continue
                desc = item.get("description") or item.get("name") or ""
                if not desc:
                    continue
                # Semantic + keyword search, take top 1
                candidates = hybrid_search(desc, top_k_semantic=5, top_k_keyword=5)
                if candidates:
                    best = candidates[0]
                    pid = best.get("product_id") or (best.get("metadata") or {}).get("product_id")
                    if pid:
                        resolved.append((pid, qty))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                resolved.append((str(item[0]), max(1, int(item[1]))))
        return {"resolved_items": resolved}
    finally:
        session.close()


def _create_order_node(state: OrderAgentState) -> OrderAgentState:
    """Call process_order with resolved_items."""
    user_id = state.get("user_id") or ""
    resolved = state.get("resolved_items") or []
    result = process_order(user_id=user_id, product_quantities=resolved)
    return {"order_result": result}


def _format_response(state: OrderAgentState) -> OrderAgentState:
    """Build final response_message from order_result or error."""
    order_result = state.get("order_result")
    error = state.get("error")
    intent = state.get("intent", "")
    if order_result:
        return {"response_message": order_result.get("message", "Order placed.")}
    if error:
        return {"response_message": f"Could not complete order: {error}"}
    if intent == "not_order":
        return {"response_message": "I didn't detect an order. Try: 'Order 2x P00001' or 'Buy a red shirt under ₹500'."}
    resolved = state.get("resolved_items") or []
    if not resolved:
        return {"response_message": "I couldn't identify which products to order. Please mention product IDs (e.g. P00001) or clear product names."}
    return {"response_message": "Order could not be placed. Please try again."}


def _route_after_intent(state: OrderAgentState) -> Literal["extract_order_items", "format_response"]:
    if state.get("intent") == "order":
        return "extract_order_items"
    return "format_response"


def _route_after_resolve(state: OrderAgentState) -> Literal["create_order", "format_response"]:
    resolved = state.get("resolved_items") or []
    if resolved:
        return "create_order"
    return "format_response"


def build_order_graph():
    """Build and compile the LangGraph order workflow."""
    try:
        from langgraph.graph import StateGraph
    except ImportError:
        raise ImportError("Install langgraph: pip install langgraph langchain-core")
    try:
        from langgraph.graph import START, END
    except ImportError:
        START, END = "__start__", "__end__"
    graph = StateGraph(OrderAgentState)
    graph.add_node("parse_intent", _parse_intent)
    graph.add_node("extract_order_items", _extract_order_items)
    graph.add_node("resolve_products", _resolve_products)
    graph.add_node("create_order", _create_order_node)
    graph.add_node("format_response", _format_response)

    graph.add_edge(START, "parse_intent")
    graph.add_conditional_edges("parse_intent", _route_after_intent)
    graph.add_edge("extract_order_items", "resolve_products")
    graph.add_conditional_edges("resolve_products", _route_after_resolve)
    graph.add_edge("create_order", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()


_order_graph = None


def get_order_graph():
    global _order_graph
    if _order_graph is None:
        _order_graph = build_order_graph()
    return _order_graph


def process_order_from_message(
    user_id: str,
    message: str,
) -> dict:
    """
    Run the agentic order workflow (LangGraph): parse intent -> extract items (LLM) -> resolve products -> create order.
    Returns { success, order_id, total, message } for use by chatbot.
    """
    graph = get_order_graph()
    initial: OrderAgentState = {
        "user_id": user_id,
        "message": message.strip(),
    }
    try:
        final = graph.invoke(initial)
        resp = final.get("response_message") or ""
        order_result = final.get("order_result") or {}
        return {
            "success": order_result.get("success", False),
            "order_id": order_result.get("order_id"),
            "total": order_result.get("total", 0.0),
            "message": resp,
        }
    except Exception as e:
        return {
            "success": False,
            "order_id": None,
            "total": 0.0,
            "message": f"Order failed: {e}",
        }
