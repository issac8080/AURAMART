"""
Core recommendation engine: 6 recommendation types.
- category: user buying one category -> more from same category
- search_no_buy: user searched but didn't buy -> recommend matching
- already_bought: cross-sell from order history
- out_of_stock_notify: subscribe to restock, show probable time + notify
- festival: suggest by current/upcoming festival (delegates to festivals.py)
- habits: reorder suggestions (delegates to habits.py)
"""
from datetime import datetime, timedelta
from typing import List, Optional

from recommend.db import get_session
from recommend.models_db import (
    User,
    Product,
    Order,
    OrderItem,
    Event,
    StockNotify,
)
from recommend.festivals import get_festival_recommendations
from recommend.habits import get_habit_products


def _product_to_dict(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "price": p.price,
        "category": p.category,
        "rating": p.rating,
        "in_stock": p.in_stock,
        "stock_count": p.stock_count,
    }


def recommend_by_category(user_id: str, limit: int = 10) -> List[dict]:
    """
    User bought or browsed one category -> recommend more from same category.
    Uses order history and events to infer category affinity.
    """
    session = get_session()
    try:
        categories = []
        orders = session.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(20).all()
        for o in orders:
            for it in o.items:
                p = session.query(Product).filter(Product.id == it.product_id).first()
                if p and p.category:
                    categories.append(p.category)
        events = (
            session.query(Event)
            .filter(Event.user_id == user_id, Event.category.isnot(None))
            .order_by(Event.timestamp.desc())
            .limit(30)
            .all()
        )
        for e in events:
            if e.category:
                categories.append(e.category)
        if not categories:
            # Fallback: top-rated products from any category
            products = (
                session.query(Product)
                .filter(Product.in_stock == True)
                .order_by(Product.rating.desc())
                .limit(limit)
                .all()
            )
            return [_product_to_dict(p) for p in products]
        from collections import Counter
        top_cat = Counter(categories).most_common(1)[0][0]
        products = (
            session.query(Product)
            .filter(Product.category == top_cat, Product.in_stock == True)
            .order_by(Product.rating.desc(), Product.review_count.desc())
            .limit(limit)
            .all()
        )
        return [_product_to_dict(p) for p in products]
    finally:
        session.close()


def recommend_search_no_buy(user_id: str, limit: int = 10) -> List[dict]:
    """
    Recent search queries without corresponding purchase -> recommend matching products.
    Uses keyword match on product name, tags, category.
    """
    session = get_session()
    try:
        search_queries = (
            session.query(Event.query)
            .filter(Event.user_id == user_id, Event.event_type == "search", Event.query.isnot(None))
            .order_by(Event.timestamp.desc())
            .limit(10)
            .all()
        )
        queries = [q[0].strip().lower() for q in search_queries if q[0] and q[0].strip()]
        if not queries:
            products = (
                session.query(Product)
                .filter(Product.in_stock == True)
                .order_by(Product.rating.desc())
                .limit(limit)
                .all()
            )
            return [_product_to_dict(p) for p in products]
        # Products user already bought (exclude)
        bought_ids = set()
        for o in session.query(Order).filter(Order.user_id == user_id).all():
            for it in o.items:
                bought_ids.add(it.product_id)
        # Keyword match: name, tags, category, description
        q = session.query(Product).filter(Product.in_stock == True)
        if bought_ids:
            q = q.filter(~Product.id.in_(bought_ids))
        candidates = q.limit(2000).all()
        if bought_ids and not candidates:
            candidates = session.query(Product).filter(Product.in_stock == True).limit(2000).all()
        scored = []
        for p in candidates:
            text = " ".join([
                (p.name or "").lower(),
                (p.category or "").lower(),
                (p.description or "")[:200].lower(),
                " ".join((p.tags or [])),
            ])
            score = sum(1 for q in queries[:3] if q in text)
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda x: (-x[0], -x[1].rating))
        if scored:
            return [_product_to_dict(p) for _, p in scored[:limit]]
        # Fallback: top by rating
        fallback = (
            session.query(Product)
            .filter(Product.in_stock == True)
            .order_by(Product.rating.desc())
            .limit(limit)
            .all()
        )
        return [_product_to_dict(p) for p in fallback]
    finally:
        session.close()


def recommend_already_bought(user_id: str, limit: int = 10) -> List[dict]:
    """
    Cross-sell / "people also bought": from order history, recommend complementary
    (same category or frequently bought together).
    """
    session = get_session()
    try:
        orders = session.query(Order).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).limit(30).all()
        bought_ids = set()
        categories = []
        for o in orders:
            for it in o.items:
                bought_ids.add(it.product_id)
                p = session.query(Product).filter(Product.id == it.product_id).first()
                if p and p.category:
                    categories.append(p.category)
        if not categories:
            products = (
                session.query(Product)
                .filter(Product.in_stock == True)
                .order_by(Product.rating.desc())
                .limit(limit)
                .all()
            )
            return [_product_to_dict(p) for p in products]
        from collections import Counter
        top_cats = [c for c, _ in Counter(categories).most_common(3)]
        q = (
            session.query(Product)
            .filter(Product.category.in_(top_cats), Product.in_stock == True)
        )
        if bought_ids:
            q = q.filter(~Product.id.in_(bought_ids))
        products = q.order_by(Product.rating.desc()).limit(limit * 2).all()
        seen = set(bought_ids)
        out = []
        for p in products:
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append(_product_to_dict(p))
            if len(out) >= limit:
                break
        return out
    finally:
        session.close()


def out_of_stock_subscribe(user_id: str, product_id: str, probable_restock_days: Optional[int] = None) -> dict:
    """
    Subscribe user to be notified when product is back in stock.
    probable_restock_days: optional; if not set, use product.restock_estimate_days or default 3-5.
    Returns { subscribed, probable_restock_at, message }.
    """
    session = get_session()
    try:
        p = session.query(Product).filter(Product.id == product_id).first()
        if not p:
            return {"subscribed": False, "probable_restock_at": None, "message": "Product not found."}
        if p.in_stock:
            return {"subscribed": False, "probable_restock_at": None, "message": "Product is already in stock."}
        existing = (
            session.query(StockNotify)
            .filter(StockNotify.user_id == user_id, StockNotify.product_id == product_id, StockNotify.notified == False)
            .first()
        )
        days = probable_restock_days or getattr(p, "restock_estimate_days", None) or 5
        probable = datetime.utcnow() + timedelta(days=days)
        if existing:
            existing.probable_restock_at = probable
            session.commit()
            return {
                "subscribed": True,
                "probable_restock_at": probable.isoformat(),
                "message": f"You're already subscribed. Probable restock: ~{days} days.",
            }
        session.add(
            StockNotify(
                user_id=user_id,
                product_id=product_id,
                notified=False,
                probable_restock_at=probable,
                created_at=datetime.utcnow(),
            )
        )
        session.commit()
        return {
            "subscribed": True,
            "probable_restock_at": probable.isoformat(),
            "message": f"We'll notify you when it's back. Probable restock: ~{days} days.",
        }
    finally:
        session.close()


def out_of_stock_recommendations(user_id: str, limit: int = 5) -> List[dict]:
    """
    For products user viewed/searched that are out of stock: show probable restock time
    and option to subscribe (call out_of_stock_subscribe for that).
    Returns list of { product_id, name, probable_restock_at, subscribed }.
    """
    session = get_session()
    try:
        # Products user searched or viewed that are out of stock
        events = (
            session.query(Event)
            .filter(Event.user_id == user_id, Event.product_id.isnot(None))
            .order_by(Event.timestamp.desc())
            .limit(50)
            .all()
        )
        out_of_stock_ids = list(dict.fromkeys([e.product_id for e in events if e.product_id]))
        if not out_of_stock_ids:
            return []
        products = (
            session.query(Product)
            .filter(Product.id.in_(out_of_stock_ids), Product.in_stock == False)
            .limit(limit)
            .all()
        )
        subs = {
            (r.user_id, r.product_id): r
            for r in session.query(StockNotify).filter(
                StockNotify.user_id == user_id,
                StockNotify.product_id.in_([p.id for p in products]),
                StockNotify.notified == False,
            ).all()
        }
        out = []
        for p in products:
            sub = subs.get((user_id, p.id))
            days = getattr(p, "restock_estimate_days", None) or 5
            if sub and sub.probable_restock_at:
                probable = sub.probable_restock_at.isoformat() if hasattr(sub.probable_restock_at, "isoformat") else str(sub.probable_restock_at)
            else:
                probable = (datetime.utcnow() + timedelta(days=days)).isoformat()
            out.append({
                "product_id": p.id,
                "name": p.name,
                "price": p.price,
                "probable_restock_at": probable,
                "probable_restock_days": days,
                "subscribed": bool(sub),
            })
        return out[:limit]
    finally:
        session.close()


def get_recommendations(
    user_id: str,
    rec_type: str,
    limit: int = 10,
) -> List[dict]:
    """
    Dispatch to the right recommendation type.
    rec_type: category | search_no_buy | already_bought | out_of_stock_notify | festival | habits
    """
    if rec_type == "category":
        return recommend_by_category(user_id, limit)
    if rec_type == "search_no_buy":
        return recommend_search_no_buy(user_id, limit)
    if rec_type == "already_bought":
        return recommend_already_bought(user_id, limit)
    if rec_type == "out_of_stock_notify":
        return out_of_stock_recommendations(user_id, limit)
    if rec_type == "festival":
        return get_festival_recommendations(limit)
    if rec_type == "habits":
        return get_habit_products(user_id)  # returns list of { product_id, name, price, order_count }
    return []
