"""
Unified chatbot: agent actions (cancel/reorder/book/deliver), order, recommend (RAG), FAQ (RAG), and general chat.
Single entry for all chat; uses recommend RAG + app order/wallet/data_store for full context.
"""
import os
import re
from typing import Optional, List, Dict, Any

from recommend.agent_actions import parse_agent_intent, execute_agent_action
from recommend.agentic_order import process_order_from_message, process_order
from recommend.rag_products import recommend_products_rag
from recommend.rag_faq import answer_faq_with_llm


INTENT_ORDER = "order"
INTENT_RECOMMEND = "recommend"
INTENT_FAQ = "faq"
INTENT_GENERAL = "general"
INTENT_OTHER = "other"


def _get_user_context(user_id: str) -> Dict[str, Any]:
    """Load cart, orders, wallet, profile from app layer for agent actions and general chat."""
    ctx = {
        "cart_items": [],
        "cart_total": 0,
        "orders_info": [],
        "wallet_info": {"balance": 0, "pending_points": 0, "total_earned": 0, "expiring_soon": 0},
        "profile_name": "there",
        "profile_address": None,
        "categories": [],
        "session_context": {},
    }
    try:
        from app.data_store import (
            get_session_context,
            get_product,
            load_products,
            get_categories,
        )
        session_ctx = get_session_context(user_id, user_id)
        ctx["session_context"] = session_ctx
        cart_ids = session_ctx.get("cart_ids", [])
        if cart_ids:
            items = [get_product(pid) for pid in cart_ids]
            ctx["cart_items"] = [p for p in items if p]
            ctx["cart_total"] = sum(p.price for p in ctx["cart_items"])
        ctx["categories"] = get_categories()
    except Exception:
        pass
    try:
        from app.order_service import get_user_orders, get_user_profile
        orders = get_user_orders(user_id)
        for o in orders[:5]:
            ctx["orders_info"].append({
                "id": o.id,
                "total": o.total,
                "status": o.status.value if hasattr(o.status, "value") else str(o.status),
                "items_count": len(o.items),
            })
        profile = get_user_profile(user_id)
        if profile and getattr(profile, "name", None):
            ctx["profile_name"] = profile.name
        if profile and getattr(profile, "addresses", None):
            addrs = profile.addresses if isinstance(profile.addresses, list) else []
            if addrs:
                ctx["profile_address"] = addrs[0]
    except Exception:
        pass
    try:
        from app.wallet_service import get_wallet_summary
        ws = get_wallet_summary(user_id)
        ctx["wallet_info"] = {
            "balance": ws.get("balance", 0),
            "pending_points": ws.get("pending_points", 0),
            "total_earned": ws.get("total_earned", 0),
            "expiring_soon": ws.get("expiring_soon", 0),
        }
    except Exception:
        pass
    return ctx


def _classify_intent_keyword_fallback(message: str) -> str:
    """Fallback when LLM is unavailable or returns invalid intent."""
    msg = (message or "").strip().lower()
    order_keywords = ["order", "buy", "purchase", "add to cart", "get me", "send me", "place order", "checkout"]
    faq_keywords = ["return", "policy", "refund", "delivery", "ship", "track", "wallet", "aurapoints", "cancel", "how do i", "how to", "what is", "faq"]
    general_keywords = ["hi", "hello", "hey", "help", "what can you do", "cart", "balance", "my order", "status"]
    if any(k in msg for k in order_keywords) and "recommend" not in msg and "suggest" not in msg:
        return INTENT_ORDER
    if any(k in msg for k in faq_keywords) and "recommend" not in msg:
        return INTENT_FAQ
    if any(k in msg for k in general_keywords) or "recommend" in msg or "suggest" in msg or "best " in msg or "find " in msg:
        if any(k in msg for k in general_keywords):
            return INTENT_GENERAL
        return INTENT_RECOMMEND
    return INTENT_RECOMMEND


def classify_intent(message: str) -> str:
    """
    Classify user message: order vs recommend vs FAQ vs general using LLM.
    Falls back to keyword matching if OPENAI_API_KEY is missing or LLM fails.
    """
    msg = (message or "").strip()
    if not msg:
        return INTENT_RECOMMEND
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return _classify_intent_keyword_fallback(message)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        prompt = """You are an intent classifier for a shopping assistant chatbot. Classify the user message into exactly one intent.

Intents:
- order: user wants to buy, purchase, or place an order for specific product(s) (e.g. "order 2x P00001", "buy me that shirt", "get me a phone").
- recommend: user wants product suggestions, recommendations, or to browse (e.g. "best phones under 20k", "suggest casual shoes", "what do you have for gifts").
- faq: user is asking about policies, help, or how things work (e.g. "return policy", "how do I track", "what is AuraPoints").
- general: greetings, "what can you do", "help", "my cart", "my balance", "order status", or conversational chat.

User message: "{message}"

Reply with exactly one word: order, recommend, faq, or general. No other text.""".format(message=msg[:500])
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        text = (resp.choices[0].message.content or "").strip().lower()
        if text in (INTENT_ORDER, INTENT_RECOMMEND, INTENT_FAQ, INTENT_GENERAL):
            return text
        if "order" in text:
            return INTENT_ORDER
        if "faq" in text:
            return INTENT_FAQ
        if "general" in text:
            return INTENT_GENERAL
        return INTENT_RECOMMEND
    except Exception:
        return _classify_intent_keyword_fallback(message)


def extract_preference(message: str) -> Optional[str]:
    """Extract user preference from message for product boost (e.g. 'under 2000', 'red')."""
    msg = (message or "").strip().lower()
    # Budget: under X, below X, budget X
    m = re.search(r"(?:under|below|within|budget)\s*(?:rs\.?|₹|inr)?\s*(\d+)", msg)
    if m:
        return f"under ₹{m.group(1)}"
    # Color
    colors = ["red", "blue", "black", "white", "green", "grey", "navy", "brown"]
    for c in colors:
        if c in msg:
            return c
    return None


def _build_user_summary(session_context: dict) -> str:
    """Build a short text summary of user context for LLM."""
    profile = session_context.get("profile", {})
    budget = profile.get("max_budget") or (session_context.get("budget_signals") or [None])[-1]
    categories = profile.get("preferred_categories") or session_context.get("categories_viewed", [])
    queries = session_context.get("search_queries", [])
    viewed = session_context.get("viewed_product_ids", [])
    cart = session_context.get("cart_ids", [])
    parts = []
    if budget:
        parts.append(f"Budget signal: under ₹{budget}")
    if categories:
        parts.append(f"Categories of interest: {', '.join(categories[:5])}")
    if queries:
        parts.append(f"Recent searches: {', '.join(queries[:3])}")
    if viewed:
        parts.append(f"Recently viewed product IDs: {', '.join(viewed[:8])}")
    if cart:
        parts.append(f"Cart product IDs: {', '.join(cart)}")
    return "\n".join(parts) if parts else "New user, no history yet."


def _general_fallback(message: str, ctx: Dict[str, Any]) -> tuple:
    """Rule-based reply when OpenAI is unavailable for general chat."""
    msg_lower = (message or "").lower()
    profile_name = ctx.get("profile_name", "there")
    cart_items = ctx.get("cart_items", [])
    cart_total = ctx.get("cart_total", 0)
    orders_info = ctx.get("orders_info", [])
    wallet_info = ctx.get("wallet_info", {})
    product_ids = []

    if any(w in msg_lower for w in ["wallet", "balance", "money", "aurapoints", "points"]):
        content = f"Hi {profile_name}! Your wallet: **₹{wallet_info.get('balance', 0)}** available. "
        if wallet_info.get("pending_points", 0) > 0:
            content += f"Pending AuraPoints: ₹{wallet_info['pending_points']} (after delivery). "
        content += "Go to [Wallet](/wallet) to top up or use balance."
        return content, []

    if any(w in msg_lower for w in ["order", "delivery", "track", "status"]) and orders_info:
        o = orders_info[0]
        content = f"Hi {profile_name}! Latest order **{o['id']}** – {o['status']}, ₹{o['total']}. View [Order](/orders/{o['id']})."
        return content, []

    if any(w in msg_lower for w in ["cart", "basket"]) and cart_items:
        content = f"Hi {profile_name}! Cart: {len(cart_items)} items, **₹{cart_total}**. "
        content += "Go to [Cart](/cart) or [Checkout](/checkout)."
        for p in cart_items[:6]:
            product_ids.append(p.id)
        return content, product_ids

    if any(w in msg_lower for w in ["hi", "hello", "hey", "help", "what can you do"]):
        content = f"Hi {profile_name}! I can: recommend products, help you order, answer FAQs, cancel/reorder, and book at store or deliver. Try: 'phones under 20k', 'my cart', 'cancel my last order'."
        return content, []

    # Default: suggest recommendations
    try:
        from app.data_store import load_products
        products = load_products()
        top = sorted(products, key=lambda p: (-p.rating, -p.price))[:4]
        content = f"Hi {profile_name}! Try: 'best phones under 20k', 'my cart', or 'what is AuraPoints?' Here are some picks: "
        for p in top:
            content += f"**{p.id}** {p.name} ₹{p.price}. "
            product_ids.append(p.id)
        return content, product_ids[:6]
    except Exception:
        return f"Hi {profile_name}! Ask me to recommend products, check your cart, or ask about orders and wallet.", []


def _general_chat(user_id: str, message: str, ctx: Dict[str, Any], history: Optional[List[dict]] = None) -> dict:
    """General conversational chat with full user context (cart, orders, wallet, products)."""
    profile_name = ctx.get("profile_name", "there")
    cart_items = ctx.get("cart_items", [])
    cart_total = ctx.get("cart_total", 0)
    orders_info = ctx.get("orders_info", [])
    wallet_info = ctx.get("wallet_info", {})
    categories = ctx.get("categories", [])
    session_ctx = ctx.get("session_context", {})

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        content, product_ids = _general_fallback(message, ctx)
        return {"content": content, "product_ids": product_ids[:6], "order_id": None, "success": True}

    try:
        from app.data_store import load_products, get_product
        products = load_products()
        by_cat = {}
        for p in products:
            by_cat.setdefault(p.category, []).append(p)
        sampled = []
        for cat_products in by_cat.values():
            sampled.extend(cat_products[:10])
        sampled = (sampled + products)[:100]
        product_list = "\n".join([f"- {p.id}: {p.name}, ₹{p.price}, {p.category}, {p.rating}⭐" for p in sampled])
        user_summary = _build_user_summary(session_ctx)
        cart_summary = ""
        if cart_items:
            cart_summary = f"Cart ({len(cart_items)} items, ₹{cart_total}): " + ", ".join([f"{p.name} (₹{p.price})" for p in cart_items[:3]])
            if len(cart_items) > 3:
                cart_summary += f" +{len(cart_items)-3} more"
        system = f"""You are AuraShop's AI assistant with full context. Be friendly and helpful.

User: {profile_name}
Cart: {len(cart_items)} items, ₹{cart_total}. {cart_summary or "Empty."}
Orders: {len(orders_info)}. {"Latest: " + orders_info[0]["id"] + " - " + orders_info[0]["status"] if orders_info else "None."}
Wallet: ₹{wallet_info.get('balance', 0)}. Pending AuraPoints: ₹{wallet_info.get('pending_points', 0)}.
Activity: {user_summary}
Categories: {', '.join(categories[:12])}
Products (use IDs for cards): {product_list[:4000]}

Reply in 1-3 short paragraphs. Use **bold** for emphasis. Mention product IDs (e.g. P00123) when recommending. Be warm."""
        messages = [{"role": "system", "content": system}]
        if history:
            for h in history[-8:]:
                role = "user" if h.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": (h.get("content") or "")[:1000]})
        messages.append({"role": "user", "content": message[:2000]})

        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
        )
        content = (resp.choices[0].message.content or "").strip()
        product_ids = list(dict.fromkeys(re.findall(r"P\d{3,5}", content)))[:6]
        return {"content": content, "product_ids": product_ids, "order_id": None, "success": True}
    except Exception:
        content, product_ids = _general_fallback(message, ctx)
        return {"content": content, "product_ids": product_ids[:6], "order_id": None, "success": True}


def chat(user_id: str, message: str, history: Optional[List[dict]] = None) -> dict:
    """
    Unified entry: agent actions first (cancel/reorder/book/deliver), then order / recommend / FAQ / general.
    Returns { content, product_ids, order_id, success }.
    """
    ctx = _get_user_context(user_id)
    orders_info = ctx["orders_info"]
    cart_items = ctx["cart_items"]
    profile_name = ctx["profile_name"]
    profile_address = ctx["profile_address"]

    # 1) Agent actions: cancel order, reorder last, book at store, deliver cart
    agent_result = parse_agent_intent(message, orders_info, len(cart_items))
    if agent_result.get("intent") and agent_result["intent"] != "none":
        action_result = execute_agent_action(
            user_id,
            agent_result["intent"],
            agent_result.get("order_id"),
            orders_info,
            cart_items,
            profile_name,
            profile_address,
        )
        if action_result:
            return {
                "content": action_result[0],
                "product_ids": action_result[1][:6],
                "order_id": None,
                "success": True,
            }

    # 2) Intent routing
    intent = classify_intent(message)
    content = ""
    product_ids: List[str] = []
    order_id = None
    success = True

    if intent == INTENT_ORDER:
        # Checkout / place order with existing cart (no product extraction)
        msg_lower = (message or "").strip().lower()
        checkout_phrases = ["checkout", "place order", "buy my cart", "complete order", "pay for", "buy cart"]
        if cart_items and any(p in msg_lower for p in checkout_phrases):
            content = f"Hi {profile_name}! I can help you complete your purchase.\n\n"
            content += f"Items in your cart: {len(cart_items)}\nTotal: **₹{ctx['cart_total']}**\n"
            content += f"Estimated AuraPoints: ₹{(ctx['cart_total'] * (0.07 if ctx['cart_total'] >= 1000 else 0.05)):.0f}\n\n"
            content += "Go to [Checkout](/checkout) to finalize your order."
            product_ids = [p.id for p in cart_items[:6]]
            return {"content": content, "product_ids": product_ids, "order_id": None, "success": True}
        result = process_order_from_message(user_id=user_id, message=message)
        success = result.get("success", False)
        content = result.get("message", "")
        order_id = result.get("order_id")
        return {"content": content, "product_ids": product_ids, "order_id": order_id, "success": success}

    if intent == INTENT_RECOMMEND:
        preference = extract_preference(message)
        recs = recommend_products_rag(
            query=message,
            top_semantic=15,
            top_rerank=5,
            user_preference=preference,
        )
        if not recs:
            content = "I couldn't find matching products. Try describing what you're looking for (e.g. 'phones under 20k', 'casual shoes')."
        else:
            product_ids = [r.get("product_id") or r.get("metadata", {}).get("product_id") for r in recs if r.get("product_id") or r.get("metadata", {}).get("product_id")]
            product_ids = list(dict.fromkeys(product_ids))[:5]
            lines = [f"- {r.get('metadata', {}).get('name', r.get('product_id', ''))} (₹{r.get('metadata', {}).get('price', 0)}, {r.get('metadata', {}).get('category', '')})" for r in recs[:5]]
            content = "Here are my top picks:\n" + "\n".join(lines)
        return {"content": content, "product_ids": product_ids, "order_id": None, "success": True}

    if intent == INTENT_FAQ:
        content = answer_faq_with_llm(message, top_k=3)
        return {"content": content, "product_ids": [], "order_id": None, "success": True}

    if intent == INTENT_GENERAL or intent == INTENT_OTHER:
        return _general_chat(user_id, message, ctx, history)

    # Fallback: try recommend then generic
    preference = extract_preference(message)
    recs = recommend_products_rag(message, top_semantic=10, top_rerank=5, user_preference=preference)
    if recs:
        product_ids = [r.get("product_id") or (r.get("metadata") or {}).get("product_id") for r in recs if (r.get("product_id") or (r.get("metadata") or {}).get("product_id"))]
        product_ids = list(dict.fromkeys(product_ids))[:5]
        lines = [f"- {r.get('metadata', {}).get('name', r.get('product_id', ''))} (₹{r.get('metadata', {}).get('price', 0)})" for r in recs[:5]]
        content = "Here are some products you might like:\n" + "\n".join(lines)
    else:
        return _general_chat(user_id, message, ctx, history)
    return {"content": content, "product_ids": product_ids, "order_id": None, "success": True}
