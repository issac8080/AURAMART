"""
In-memory data store for sessions, events, and user preferences.
Products and carts are read/written from recommend DB only. JSON is synced into DB on startup (db_sync).
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.models import EventPayload, Product, EventType

# Products: loaded from recommend DB (cached in memory)
_products: List[Product] = []
_products_by_id: Dict[str, Product] = {}
_products_loaded = False

# Session events: session_id -> list of events
_events: Dict[str, List[dict]] = {}

# User preference profiles (derived from events): session_id -> profile
_profiles: Dict[str, dict] = {}

# Recommendation cache: (session_id, context_hash) -> list of recs (optional TTL)
_rec_cache: Dict[str, List[dict]] = {}
_CACHE_MAX = 500


def _db_product_to_app(db_p: Any) -> Product:
    """Map recommend.models_db.Product to app.models.Product."""
    return Product(
        id=db_p.id,
        name=db_p.name or "",
        description=db_p.description or "",
        price=float(db_p.price) if db_p.price is not None else 0.0,
        currency=db_p.currency or "INR",
        category=db_p.category or "",
        subcategory=db_p.subcategory,
        brand=db_p.brand,
        rating=float(db_p.rating) if db_p.rating is not None else 0.0,
        review_count=int(db_p.review_count) if db_p.review_count is not None else 0,
        colors=list(db_p.colors) if db_p.colors is not None else [],
        sizes=list(db_p.sizes) if db_p.sizes is not None else [],
        image_url=db_p.image_url,
        tags=list(db_p.tags) if db_p.tags is not None else [],
        in_stock=db_p.in_stock if db_p.in_stock is not None else True,
        stock_count=db_p.stock_count,
    )


def load_products() -> List[Product]:
    """Load products from recommend DB only (cached in memory)."""
    global _products, _products_by_id, _products_loaded
    if _products_loaded and _products:
        return _products
    _products_loaded = True
    try:
        from recommend.db import get_session
        from recommend.models_db import Product as DbProduct

        session = get_session()
        try:
            rows = session.query(DbProduct).all()
            _products = []
            for p in rows:
                try:
                    _products.append(_db_product_to_app(p))
                except Exception:
                    continue
            _products_by_id = {p.id: p for p in _products}
            return _products
        finally:
            session.close()
    except Exception:
        _products = []
        _products_by_id = {}
    return _products


def get_product(product_id: str) -> Optional[Product]:
    load_products()
    return _products_by_id.get(product_id)


def get_categories() -> List[str]:
    """Return sorted list of unique categories from the product catalog."""
    load_products()
    return sorted({p.category for p in _products})


def get_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    colors: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Product]:
    load_products()
    out = list(_products)
    if category:
        out = [p for p in out if p.category == category]
    if min_price is not None:
        out = [p for p in out if p.price >= min_price]
    if max_price is not None:
        out = [p for p in out if p.price <= max_price]
    if min_rating is not None:
        out = [p for p in out if p.rating >= min_rating]
    if colors:
        out = [p for p in out if any(c.lower() in [x.lower() for x in p.colors] for c in colors)]
    return out[:limit]


def add_event(payload: EventPayload) -> None:
    session_id = payload.session_id
    if session_id not in _events:
        _events[session_id] = []
    _events[session_id].append({
        **payload.model_dump(),
        "timestamp": datetime.utcnow().isoformat(),
    })
    # Keep last 500 events per session
    _events[session_id] = _events[session_id][-500:]


def get_events(session_id: str, limit: int = 100) -> List[dict]:
    return list(reversed(_events.get(session_id, [])[:limit]))


def _actor_id(session_id: str, user_id: Optional[str] = None) -> str:
    """Use user_id when provided (logged-in), else session_id (guest)."""
    return (user_id or "").strip() or session_id


def _cart_query(session, session_id: str, user_id: Optional[str]):
    """Query Cart rows for actor: by user_id if logged in, else by session_id."""
    from recommend.models_db import Cart as DbCart

    if user_id and user_id.strip():
        return session.query(DbCart).filter(DbCart.user_id == user_id.strip()).all()
    return session.query(DbCart).filter(DbCart.session_id == session_id).all()


def get_cart(session_id: str, user_id: Optional[str] = None) -> List[str]:
    """Cart from recommend DB only: list of product_ids (with quantity as repeats)."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Cart as DbCart

        session = get_session()
        try:
            rows = _cart_query(session, session_id, user_id)
            out = []
            for r in rows:
                qty = max(1, int(r.quantity) if r.quantity is not None else 1)
                out.extend([r.product_id] * qty)
            return out
        finally:
            session.close()
    except Exception:
        return []


def add_to_cart(session_id: str, product_id: str, user_id: Optional[str] = None) -> None:
    """Add one item to cart in recommend DB."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Cart as DbCart

        session = get_session()
        try:
            uid = user_id.strip() if user_id and user_id.strip() else None
            sid = None if uid else session_id
            if uid:
                existing = session.query(DbCart).filter(DbCart.user_id == uid, DbCart.product_id == product_id).first()
            else:
                existing = session.query(DbCart).filter(DbCart.session_id == session_id, DbCart.product_id == product_id).first()
            if existing:
                existing.quantity = (existing.quantity or 1) + 1
            else:
                session.add(
                    DbCart(
                        user_id=uid,
                        session_id=sid,
                        product_id=product_id,
                        quantity=1,
                    )
                )
            session.commit()
        finally:
            session.close()
    except Exception:
        pass


def remove_from_cart(session_id: str, product_id: str, user_id: Optional[str] = None) -> None:
    """Remove one occurrence of product from cart in recommend DB."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Cart as DbCart

        session = get_session()
        try:
            uid = user_id.strip() if user_id and user_id.strip() else None
            if uid:
                row = session.query(DbCart).filter(DbCart.user_id == uid, DbCart.product_id == product_id).first()
            else:
                row = session.query(DbCart).filter(DbCart.session_id == session_id, DbCart.product_id == product_id).first()
            if row:
                if (row.quantity or 1) > 1:
                    row.quantity -= 1
                else:
                    session.delete(row)
                session.commit()
        finally:
            session.close()
    except Exception:
        pass


def clear_cart(session_id: str, user_id: Optional[str] = None) -> None:
    """Clear all items from cart in recommend DB."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Cart as DbCart

        session = get_session()
        try:
            uid = user_id.strip() if user_id and user_id.strip() else None
            if uid:
                session.query(DbCart).filter(DbCart.user_id == uid).delete()
            else:
                session.query(DbCart).filter(DbCart.session_id == session_id).delete()
            session.commit()
        finally:
            session.close()
    except Exception:
        pass


def merge_cart_into_user(session_id: str, user_id: str) -> None:
    """Merge guest cart (session_id) into user cart (user_id) and clear guest cart in recommend DB."""
    if not (user_id and user_id.strip()):
        return
    user_id = user_id.strip()
    try:
        from recommend.db import get_session
        from recommend.models_db import Cart as DbCart

        session = get_session()
        try:
            guest_rows = session.query(DbCart).filter(DbCart.session_id == session_id).all()
            for row in guest_rows:
                existing = session.query(DbCart).filter(DbCart.user_id == user_id, DbCart.product_id == row.product_id).first()
                if existing:
                    existing.quantity = (existing.quantity or 1) + (row.quantity or 1)
                    session.delete(row)
                else:
                    row.session_id = None
                    row.user_id = user_id
            session.commit()
        finally:
            session.close()
    except Exception:
        pass


def set_profile(session_id: str, profile: dict, user_id: Optional[str] = None) -> None:
    key = _actor_id(session_id, user_id)
    _profiles[key] = profile


def get_profile(session_id: str, user_id: Optional[str] = None) -> dict:
    key = _actor_id(session_id, user_id)
    return _profiles.get(key, {})


def get_session_context(session_id: str, user_id: Optional[str] = None) -> dict:
    """Build context for AI: events, cart, profile, viewed product IDs. Uses user_id when provided (logged-in)."""
    events = get_events(session_id, 80)
    cart_ids = get_cart(session_id, user_id)
    profile = get_profile(session_id, user_id)
    viewed_ids = [
        e.get("product_id") for e in events
        if e.get("event_type") in (EventType.PRODUCT_CLICK.value, EventType.PAGE_VIEW.value)
        and e.get("product_id")
    ]
    viewed_ids = list(dict.fromkeys(viewed_ids))[:20]
    search_queries = [e.get("query") for e in events if e.get("event_type") == EventType.SEARCH.value and e.get("query")][-5:]
    budget_signals = [e.get("amount") for e in events if e.get("event_type") == EventType.BUDGET_SIGNAL.value and e.get("amount")][-3:]
    categories_viewed = list(dict.fromkeys([e.get("category") for e in events if e.get("category")]))[-10:]
    # Derive profile from events if not set: preferred categories, max budget
    if not profile and (categories_viewed or budget_signals):
        profile = {
            "preferred_categories": categories_viewed[:5],
            "max_budget": min(budget_signals) if budget_signals else None,
        }
    return {
        "events": events,
        "cart_ids": cart_ids,
        "profile": profile,
        "viewed_product_ids": viewed_ids,
        "search_queries": search_queries,
        "budget_signals": budget_signals,
        "categories_viewed": categories_viewed,
    }


def cache_recommendations(session_id: str, context_key: str, recs: List[dict], user_id: Optional[str] = None) -> None:
    actor = _actor_id(session_id, user_id)
    key = f"{actor}:{context_key}"
    _rec_cache[key] = recs
    if len(_rec_cache) > _CACHE_MAX:
        for k in list(_rec_cache.keys())[:_CACHE_MAX // 2]:
            del _rec_cache[k]


def get_cached_recommendations(session_id: str, context_key: str, user_id: Optional[str] = None) -> Optional[List[dict]]:
    actor = _actor_id(session_id, user_id)
    return _rec_cache.get(f"{actor}:{context_key}")
