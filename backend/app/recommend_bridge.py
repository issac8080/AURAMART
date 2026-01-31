"""
Bridge: expose recommend module with the same API shape as ai_service so the app keeps working.
- get_recommendations(session_id, ...) -> RAG-based recs when available; else fast data_store-only.
- chat(session_id, message, history) -> recommend.chatbot when available; else simple reply.
Frontend uses only this bridge (same as ai_service contract); no direct ai_service dependency.
"""
import hashlib
from typing import List, Optional

from app.config import USE_FAST_RECOMMEND, USE_FAST_CHAT
from app.data_store import (
    get_product,
    get_products,
    get_session_context,
    get_cached_recommendations,
    cache_recommendations,
)


def _get_recommendations_from_data_store(
    session_id: str,
    limit: int = 5,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    exclude_product_ids: Optional[List[str]] = None,
) -> List[dict]:
    """Fast path: recommendations from JSON products only (no Chroma/RAG). Same response shape as get_recommendations."""
    exclude = set(exclude_product_ids or [])
    products = get_products(category=category, max_price=max_price, limit=max(limit * 3, 20))
    out = []
    for p in products:
        if p.id in exclude or len(out) >= limit:
            break
        out.append({
            "product_id": p.id,
            "reason": f"Top pick in {p.category}" if p.category else "Recommended for you",
            "confidence": 0.8,
            "product": p.model_dump(),
        })
    return out


def get_recommendations(
    session_id: str,
    limit: int = 5,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    exclude_product_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> List[dict]:
    """
    Hybrid: use recommend RAG (recommend_products_rag) with a query built from context.
    When user_id is provided (logged in), cart/profile context comes from user data.
    Returns list of { product_id, reason, confidence, product } to match ai_service shape.
    """
    exclude = set(exclude_product_ids or [])
    context_key = hashlib.md5(
        f"{limit}_{max_price}_{category}_{sorted(exclude)}".encode()
    ).hexdigest()
    cached = get_cached_recommendations(session_id, context_key, user_id)
    if cached is not None:
        return cached

    # Fast path: no RAG/Chroma (instant, no heavy deps)
    if USE_FAST_RECOMMEND:
        out = _get_recommendations_from_data_store(
            session_id, limit=limit, max_price=max_price, category=category, exclude_product_ids=exclude_product_ids
        )
        cache_recommendations(session_id, context_key, out, user_id)
        return out

    # Build query for RAG from category / max_price / session context (user context when logged in)
    ctx = get_session_context(session_id, user_id)
    parts = []
    if category:
        parts.append(f"products in {category}")
    else:
        cats = (ctx.get("profile") or {}).get("preferred_categories") or ctx.get("categories_viewed", [])
        if cats:
            parts.append(f"products in {', '.join(cats[:3])}")
    if max_price is not None:
        parts.append(f"under ₹{max_price}")
    if not parts:
        parts.append("recommend products")
    query = " ".join(parts)

    result: List[dict] = []
    try:
        from recommend.rag_products import recommend_products_rag
        recs = recommend_products_rag(
            query=query,
            top_semantic=15,
            top_rerank=limit + len(exclude),
            user_preference=f"under ₹{max_price}" if max_price else None,
        )
        valid_ids = set()
        for r in recs:
            pid = r.get("product_id") or (r.get("metadata") or {}).get("product_id")
            if not pid or pid in exclude or pid in valid_ids:
                continue
            if max_price is not None:
                price = (r.get("metadata") or {}).get("price")
                if price is not None and price > max_price:
                    continue
            if category and (r.get("metadata") or {}).get("category") != category:
                continue
            valid_ids.add(pid)
            reason = r.get("reason") or (r.get("metadata") or {}).get("name") or "Recommended for you"
            result.append({
                "product_id": pid,
                "reason": reason[:200],
                "confidence": float(r.get("score", 0.8)),
            })
            if len(result) >= limit:
                break
    except Exception:
        pass

    # Fallback: recommend engine by category (session_id as user_id)
    if not result:
        try:
            from recommend.recommendation_engine import recommend_by_category
            fallback = recommend_by_category(user_id=session_id, limit=limit + len(exclude))
            for p in fallback:
                pid = p.get("id")
                if not pid or pid in exclude:
                    continue
                if max_price is not None and (p.get("price") or 0) > max_price:
                    continue
                if category and p.get("category") != category:
                    continue
                result.append({
                    "product_id": pid,
                    "reason": f"High rating, {p.get('category', '')}",
                    "confidence": 0.75,
                })
                if len(result) >= limit:
                    break
        except Exception:
            pass

    # Final fallback: data_store only (no recommend module)
    if not result:
        result_data = _get_recommendations_from_data_store(
            session_id, limit=limit, max_price=max_price, category=category, exclude_product_ids=list(exclude)
        )
        out = result_data
        cache_recommendations(session_id, context_key, out, user_id)
        return out

    # Attach full product from app data_store for frontend (same as ai_service)
    out = []
    for r in result:
        prod = get_product(r["product_id"])
        if prod:
            out.append({**r, "product": prod.model_dump()})
    cache_recommendations(session_id, context_key, out, user_id)
    return out


def chat(
    session_id: str,
    message: str,
    history: Optional[List[dict]] = None,
    user_id: Optional[str] = None,
) -> dict:
    """
    Delegate to recommend.chatbot.chat when available. Use user_id when provided (logged-in), else session_id (guest).
    Returns { content, product_ids } and optionally order_id, success (for frontend).
    With USE_FAST_CHAT=1, returns a short static reply (no Chroma/LLM load).
    """
    # Fast path: no recommend.chatbot (instant, no heavy deps)
    if USE_FAST_CHAT:
        return {
            "content": "I'm your AuraShop assistant. Try: \"recommend phones under 20000\", \"best laptops\", or \"what's in my cart?\". You can browse by category or use the search bar.",
            "product_ids": [],
        }
    try:
        from recommend.chatbot import chat as recommend_chat
        uid = user_id or session_id
        resp = recommend_chat(user_id=uid, message=message, history=history)
        # Match previous API: content, product_ids; add order_id and success if present
        out = {
            "content": resp.get("content", ""),
            "product_ids": resp.get("product_ids", [])[:6],
        }
        if "order_id" in resp:
            out["order_id"] = resp["order_id"]
        if "success" in resp:
            out["success"] = resp["success"]
        return out
    except Exception as e:
        return {
            "content": "Sorry, I couldn't process that. Please try again.",
            "product_ids": [],
            "success": False,
        }
