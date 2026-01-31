"""
Agent actions: cancel order, reorder last, book at store, deliver cart.
Parse user intent (LLM or rules) and execute via app.order_service and app.data_store.
Used by recommend.chatbot so the chatbot can handle everything.
"""
import json
from typing import List, Optional, Dict, Any

# Lazy imports for app layer to avoid circular import
def _get_order_service():
    from app.order_service import (
        get_user_orders,
        get_order,
        update_order_status,
        create_order,
        get_available_stores,
    )
    return get_user_orders, get_order, update_order_status, create_order, get_available_stores


def _get_openai_client():
    import os
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:
        return None


def parse_agent_intent(message: str, orders_info: List[dict], cart_count: int) -> Dict[str, Any]:
    """
    Parse user message into agent intent + params.
    Returns {"intent": "cancel_order"|"reorder_last"|"book_at_store"|"deliver_cart"|"none", "order_id": "last"|"ORD-XXX"|null}.
    """
    msg = (message or "").strip().lower()
    if not msg:
        return {"intent": "none", "order_id": None}

    # Rule-based fallback
    order_ids = [o["id"] for o in orders_info[:5]] if orders_info else []

    # Cancel: "cancel (my) (last) order", "cancel ORD-XXX"
    if "cancel" in msg:
        oid = None
        if "last" in msg or "my order" in msg or "this order" in msg:
            oid = "last"
        else:
            import re
            m = re.search(r"(ORD-\w+)", msg, re.I)
            if m:
                oid = m.group(1)
        return {"intent": "cancel_order", "order_id": oid or ("last" if order_ids else None)}

    # Reorder: "reorder", "repeat (my) last order", "order again"
    if any(w in msg for w in ["reorder", "repeat", "order again", "take my last order", "last order again"]):
        return {"intent": "reorder_last", "order_id": None}

    # Store pickup: "book at store", "store pickup", "pick up at store"
    if any(w in msg for w in ["book at store", "store pickup", "pick up at store", "pickup at store", "collect at store"]):
        return {"intent": "book_at_store", "order_id": None}

    # Home delivery: "deliver", "home delivery", "ship it"
    if any(w in msg for w in ["deliver", "home delivery", "ship it", "deliver to me", "ship to me"]):
        return {"intent": "deliver_cart", "order_id": None}

    # LLM parse when available
    client = _get_openai_client()
    if not client:
        return {"intent": "none", "order_id": None}
    prompt = f"""You are an intent parser for a shopping assistant. The user can ask to:
- cancel an order (e.g. "cancel this", "cancel my order", "cancel my last order", "cancel order ORD-XXX")
- reorder / repeat last order (e.g. "take my last order", "reorder", "repeat my last order", "order again")
- book cart at store / store pickup (e.g. "book me this at store", "store pickup", "I'll pick up at store")
- deliver cart / home delivery (e.g. "deliver me this", "home delivery", "ship it")

User message: "{message}"

User's orders (newest first): {order_ids or "none"}
User's cart has {cart_count} items.

Reply with ONLY a JSON object, no other text:
{{"intent": "cancel_order"|"reorder_last"|"book_at_store"|"deliver_cart"|"none", "order_id": "last"|"ORD-XXX"|null}}

Rules:
- For cancel: use "cancel_order", order_id "last" means their most recent order, or use exact order ID if user said it.
- For reorder/repeat last order: use "reorder_last", order_id null.
- For store pickup: use "book_at_store", order_id null.
- For home delivery: use "deliver_cart", order_id null.
- If unclear or not an action request: use "none", order_id null."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=80,
        )
        text = (resp.choices[0].message.content or "").strip()
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        data = json.loads(text)
        intent = (data.get("intent") or "none").strip().lower()
        if intent not in ("cancel_order", "reorder_last", "book_at_store", "deliver_cart", "none"):
            intent = "none"
        order_id = data.get("order_id")
        if order_id and isinstance(order_id, str):
            order_id = order_id.strip()
        else:
            order_id = None
        return {"intent": intent, "order_id": order_id}
    except Exception:
        return {"intent": "none", "order_id": None}


def execute_agent_action(
    session_id: str,
    intent: str,
    order_id_param: Optional[str],
    orders_info: List[dict],
    cart_items: List,
    profile_name: str,
    profile_address: Optional[str],
) -> Optional[tuple]:
    """
    Execute agent action: cancel_order, reorder_last, book_at_store, deliver_cart.
    cart_items: list of app.models.Product (or objects with .id, .price).
    Returns (content, product_ids) or None if action not taken.
    """
    get_user_orders, get_order, update_order_status, create_order, get_available_stores = _get_order_service()
    from app.models import OrderItem, OrderStatus, DeliveryMethod
    from app.data_store import add_to_cart, clear_cart

    if intent == "cancel_order":
        order_id = order_id_param
        if order_id == "last" and orders_info:
            order_id = orders_info[0]["id"]
        if not order_id:
            return (f"Hi {profile_name}! I need to know which order to cancel. Say 'cancel my last order' or give the order ID (e.g. ORD-XXX).", [])
        order = get_order(order_id)
        if not order or order.user_id != session_id:
            return (f"Order {order_id} not found or it's not yours. I can only cancel your orders.", [])
        if order.status.value == "cancelled":
            return (f"Order {order_id} is already cancelled.", [])
        update_order_status(order_id, OrderStatus.CANCELLED)
        return (f"Done! I've cancelled your order **{order_id}**. You can place a new order anytime.", [])

    if intent == "reorder_last":
        if not orders_info:
            return (f"Hi {profile_name}! You don't have any previous orders to reorder.", [])
        last_order = get_order(orders_info[0]["id"])
        if not last_order or not last_order.items:
            return (f"Hi {profile_name}! Your last order has no items to add.", [])
        added = []
        for item in last_order.items:
            add_to_cart(session_id, item.product_id)
            added.append(item.product_id)
        return (f"I've added your last order items to the cart. You can checkout when ready. Go to [Cart](/cart) or say 'book at store' / 'deliver to me'.", list(dict.fromkeys(added))[:6])

    if intent == "book_at_store":
        if not cart_items:
            return (f"Hi {profile_name}! Your cart is empty. Add items first, then say 'book at store' or 'store pickup'.", [])
        stores = get_available_stores()
        store_id = stores[0]["id"] if stores else "store_1"
        store_name = stores[0]["name"] if stores else "Store"
        items = [OrderItem(product_id=p.id, quantity=1, price=p.price) for p in cart_items]
        order = create_order(
            user_id=session_id,
            items=items,
            delivery_method=DeliveryMethod.STORE_PICKUP,
            store_location=store_id,
        )
        clear_cart(session_id)
        return (f"Done! I've placed your order for **store pickup**. Order ID: **{order.id}**. Show the QR code at {store_name} to collect. View order: [Order {order.id}](/orders/{order.id})", [])

    if intent == "deliver_cart":
        if not cart_items:
            return (f"Hi {profile_name}! Your cart is empty. Add items first, then say 'deliver to me' or 'home delivery'.", [])
        address = profile_address or "Default address (update in Profile)"
        items = [OrderItem(product_id=p.id, quantity=1, price=p.price) for p in cart_items]
        order = create_order(
            user_id=session_id,
            items=items,
            delivery_method=DeliveryMethod.HOME_DELIVERY,
            delivery_address=address,
        )
        clear_cart(session_id)
        return (f"Done! I've placed your order for **home delivery**. Order ID: **{order.id}**. We'll deliver to {address[:30]}... View order: [Order {order.id}](/orders/{order.id})", [])

    return None
