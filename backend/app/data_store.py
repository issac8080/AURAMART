"""
In-memory data store for sessions, events, and user preferences.
Used for real-time personalization and recommendation context.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.models import EventPayload, Product, EventType

# Load synthetic products once
PRODUCTS_PATH = Path(__file__).resolve().parent.parent / "data" / "products.json"
_products: List[Product] = []
_products_by_id: Dict[str, Product] = {}

# Session events: session_id -> list of events
_events: Dict[str, List[dict]] = {}

# User preference profiles (derived from events): session_id -> profile
_profiles: Dict[str, dict] = {}

# Cart per session: session_id -> list of product_ids
_carts: Dict[str, List[str]] = {}

# Recommendation cache: (session_id, context_hash) -> list of recs (optional TTL)
_rec_cache: Dict[str, List[dict]] = {}
_CACHE_MAX = 500


def load_products() -> List[Product]:
    global _products, _products_by_id
    if _products:
        return _products
    try:
        if not PRODUCTS_PATH.exists():
            return _products
        with open(PRODUCTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
        _products = []
        for p in data:
            try:
                _products.append(Product(**p))
            except Exception:
                continue
        _products_by_id = {p.id: p for p in _products}
        return _products
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


def get_cart(session_id: str) -> List[str]:
    return list(_carts.get(session_id, []))


def add_to_cart(session_id: str, product_id: str) -> None:
    if session_id not in _carts:
        _carts[session_id] = []
    if product_id not in _carts[session_id]:
        _carts[session_id].append(product_id)


def remove_from_cart(session_id: str, product_id: str) -> None:
    if session_id in _carts and product_id in _carts[session_id]:
        _carts[session_id].remove(product_id)


def clear_cart(session_id: str) -> None:
    """Clear all items from cart."""
    if session_id in _carts:
        _carts[session_id] = []


def set_profile(session_id: str, profile: dict) -> None:
    _profiles[session_id] = profile


def get_profile(session_id: str) -> dict:
    return _profiles.get(session_id, {})


def get_session_context(session_id: str) -> dict:
    """Build context for AI: events, cart, profile, viewed product IDs."""
    events = get_events(session_id, 80)
    cart_ids = get_cart(session_id)
    profile = get_profile(session_id)
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


def cache_recommendations(session_id: str, context_key: str, recs: List[dict]) -> None:
    key = f"{session_id}:{context_key}"
    _rec_cache[key] = recs
    if len(_rec_cache) > _CACHE_MAX:
        # Evict oldest (simple: remove first few keys)
        for k in list(_rec_cache.keys())[:_CACHE_MAX // 2]:
            del _rec_cache[k]


def get_cached_recommendations(session_id: str, context_key: str) -> Optional[List[dict]]:
    return _rec_cache.get(f"{session_id}:{context_key}")
