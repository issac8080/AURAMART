"""
Sync app data with the recommend module database so RAG, habits, and engine see the same data.
- On order create: write order to recommend DB (users, orders, order_items).
- On startup: ensure recommend DB has tables and sync products from JSON if DB is empty.
"""
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Order


def _parse_iso(s: str | None):
    if not s:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def sync_order_to_recommend_db(order: "Order") -> bool:
    """
    Persist an app order to the recommend DB (users, orders, order_items) so RAG/habits see it.
    Returns True if synced, False on error.
    """
    try:
        from recommend.db import get_session
        from recommend.models_db import User, Order as DbOrder, OrderItem as DbOrderItem

        session = get_session()
        try:
            uid = order.user_id
            if not uid:
                return False
            # Ensure user exists
            existing = session.query(User).filter(User.user_id == uid).first()
            if not existing:
                session.add(
                    User(
                        user_id=uid,
                        name=None,
                        email=None,
                        phone=None,
                        created_at=datetime.utcnow(),
                    )
                )
                session.flush()
            # Check if order already in DB (idempotent)
            existing_order = session.query(DbOrder).filter(DbOrder.id == order.id).first()
            if existing_order:
                session.close()
                return True
            created = _parse_iso(getattr(order, "created_at", None))
            updated = _parse_iso(getattr(order, "updated_at", None))
            db_order = DbOrder(
                id=order.id,
                user_id=uid,
                total=float(order.total),
                delivery_method=getattr(order.delivery_method, "value", str(order.delivery_method)),
                status=getattr(order.status, "value", str(order.status)),
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
                    DbOrderItem(
                        order_id=order.id,
                        product_id=it.product_id,
                        quantity=int(it.quantity),
                        price=float(it.price),
                    )
                )
            session.commit()
            return True
        finally:
            session.close()
    except Exception as e:
        print(f"db_sync: failed to sync order {getattr(order, 'id', '?')} to recommend DB: {e}")
        return False


def init_recommend_db_and_sync_products() -> bool:
    """
    Ensure recommend DB exists and has products. If products table is empty, load from data/products.json.
    Call on backend startup so RAG and app share the same product data.
    Returns True if DB is ready (with or without products), False on critical error.
    """
    try:
        from recommend.db import get_session, init_db
        from recommend.models_db import Product

        init_db()
        session = get_session()
        try:
            count = session.query(Product).count()
            if count == 0:
                # Products table empty: load from products.json
                products_path = Path(__file__).resolve().parent.parent / "data" / "products.json"
                if products_path.exists():
                    import json
                    with open(products_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list) and data:
                        inserted = 0
                        for p in data:
                            pid = p.get("id")
                            if not pid:
                                continue
                            session.add(
                                Product(
                                    id=pid,
                                    name=(p.get("name") or "")[:512],
                                    description=((p.get("description") or "")[:10000]) or None,
                                    price=float(p.get("price", 0)),
                                    currency=p.get("currency", "INR"),
                                    category=(p.get("category") or "")[:128] or None,
                                    subcategory=(p.get("subcategory") or "")[:128] if p.get("subcategory") else None,
                                    brand=(p.get("brand") or "")[:128] if p.get("brand") else None,
                                    rating=float(p.get("rating", 0)),
                                    review_count=int(p.get("review_count", 0)),
                                    colors=p.get("colors") or [],
                                    sizes=p.get("sizes") or [],
                                    image_url=(p.get("image_url") or "")[:1024] or None,
                                    tags=p.get("tags") or [],
                                    in_stock=p.get("in_stock", True),
                                    stock_count=p.get("stock_count"),
                                )
                            )
                            inserted += 1
                        session.commit()
                        if inserted:
                            print(f"db_sync: loaded {inserted} products from JSON into recommend DB")
            # Sync existing orders from JSON so RAG/habits see them (if orders table empty)
            _sync_orders_json_to_db(session)
            # Sync FAQ from JSON so RAG FAQ search has data (if faq table empty)
            _sync_faq_json_to_db(session)
            return True
        finally:
            session.close()
    except Exception as e:
        print(f"db_sync: init/sync products failed: {e}")
        return False


def _sync_orders_json_to_db(session) -> None:
    """If orders table is empty, load orders from data/orders.json into recommend DB."""
    try:
        from recommend.models_db import User, Order as DbOrder, OrderItem as DbOrderItem

        existing_count = session.query(DbOrder).count()
        if existing_count > 0:
            return
        orders_path = Path(__file__).resolve().parent.parent / "data" / "orders.json"
        if not orders_path.exists():
            return
        import json
        with open(orders_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        orders_list = data.get("orders", [])
        if not orders_list:
            return
        existing_users = {r.user_id for r in session.query(User.user_id).all()}
        existing_order_ids = {r.id for r in session.query(DbOrder.id).all()}
        for o in orders_list:
            uid = o.get("user_id")
            if not uid:
                continue
            if uid not in existing_users:
                session.add(
                    User(user_id=uid, name=None, email=None, phone=None, created_at=datetime.utcnow())
                )
                existing_users.add(uid)
            oid = o.get("id")
            if not oid or oid in existing_order_ids:
                continue
            created = _parse_iso(o.get("created_at"))
            updated = _parse_iso(o.get("updated_at"))
            session.add(
                DbOrder(
                    id=oid,
                    user_id=uid,
                    total=float(o.get("total", 0)),
                    delivery_method=o.get("delivery_method", "home_delivery"),
                    status=o.get("status", "pending"),
                    delivery_address=o.get("delivery_address"),
                    store_location=o.get("store_location"),
                    qr_code=o.get("qr_code"),
                    created_at=created,
                    updated_at=updated,
                )
            )
            existing_order_ids.add(oid)
            for it in o.get("items", []):
                session.add(
                    DbOrderItem(
                        order_id=oid,
                        product_id=it.get("product_id", ""),
                        quantity=int(it.get("quantity", 1)),
                        price=float(it.get("price", 0)),
                    )
                )
        session.commit()
        print(f"db_sync: loaded {len(orders_list)} orders from JSON into recommend DB")
    except Exception as e:
        print(f"db_sync: sync orders from JSON failed: {e}")


def _sync_faq_json_to_db(session) -> None:
    """If faq table is empty, load from data/faq.json into recommend DB."""
    try:
        from recommend.models_db import FAQ

        if session.query(FAQ).count() > 0:
            return
        faq_path = Path(__file__).resolve().parent.parent / "data" / "faq.json"
        if not faq_path.exists():
            return
        import json
        with open(faq_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return
        for i, item in enumerate(data):
            q = (item.get("q") or item.get("question") or "")[:2000]
            a = (item.get("a") or item.get("answer") or "")[:5000]
            if not q or not a:
                continue
            session.add(FAQ(question=q, answer=a, category=None))
        session.commit()
        print(f"db_sync: loaded {len(data)} FAQ entries from JSON into recommend DB")
    except Exception as e:
        print(f"db_sync: sync FAQ from JSON failed: {e}")
