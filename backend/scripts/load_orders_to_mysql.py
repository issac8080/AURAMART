"""
Load orders from backend/data/orders.json into MySQL (users, orders, order_items).
Creates users from user_id in orders if not present.
Run from backend: python -m scripts.load_orders_to_mysql
"""
import json
import sys
from pathlib import Path
from datetime import datetime

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from recommend.db import get_session, init_db
from recommend.models_db import User, Order, OrderItem


def parse_iso(s):
    if not s:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return datetime.utcnow()


def main():
    init_db()
    orders_path = backend_dir / "data" / "orders.json"
    if not orders_path.exists():
        print(f"ERROR: {orders_path} not found")
        return 1
    with open(orders_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    orders_list = data.get("orders", [])
    if not orders_list:
        print("No orders in file")
        return 0
    session = get_session()
    try:
        existing_users = {r.user_id for r in session.query(User.user_id).all()}
        existing_order_ids = {r.id for r in session.query(Order.id).all()}
        users_created = 0
        orders_created = 0
        for o in orders_list:
            uid = o.get("user_id")
            if not uid:
                continue
            if uid not in existing_users:
                session.add(
                    User(
                        user_id=uid,
                        name=None,
                        email=None,
                        phone=None,
                        created_at=datetime.utcnow(),
                    )
                )
                existing_users.add(uid)
                users_created += 1
            oid = o.get("id")
            if not oid or oid in existing_order_ids:
                continue
            created = parse_iso(o.get("created_at"))
            updated = parse_iso(o.get("updated_at"))
            order = Order(
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
            session.add(order)
            existing_order_ids.add(oid)
            orders_created += 1
            for it in o.get("items", []):
                session.add(
                    OrderItem(
                        order_id=oid,
                        product_id=it.get("product_id", ""),
                        quantity=int(it.get("quantity", 1)),
                        price=float(it.get("price", 0)),
                    )
                )
        session.commit()
        print(f"Users created: {users_created}, Orders created: {orders_created}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
