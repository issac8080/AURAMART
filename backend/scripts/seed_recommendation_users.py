"""
Seed synthetic users, orders, events for recommendation testing.
Also seeds festivals and FAQ.
Run from backend: python -m scripts.seed_recommendation_users [--users 100]
"""
import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from recommend.db import get_session, init_db
from recommend.models_db import User, Product, Order, OrderItem, Event, Festival, FAQ


EVENT_TYPES = ["page_view", "product_click", "search", "cart_add", "cart_remove", "budget_signal", "category_view"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=100, help="Number of synthetic users")
    args = ap.parse_args()
    n_users = max(10, min(args.users, 500))
    init_db()
    session = get_session()
    try:
        product_ids = [r.id for r in session.query(Product.id).limit(5000).all()]
        if not product_ids:
            print("Run load_products_to_mysql.py first.")
            return 1
        categories = list(
            set(
                r[0]
                for r in session.query(Product.category).filter(Product.category.isnot(None)).distinct().all()
                if r[0]
            )
        )[:20]
        existing_user_ids = {r.user_id for r in session.query(User.user_id).all()}
        # Create users U1, U2, ...
        for i in range(1, n_users + 1):
            uid = f"U{i}"
            if uid in existing_user_ids:
                continue
            session.add(
                User(
                    user_id=uid,
                    name=f"User {i}",
                    email=f"user{i}@example.com",
                    phone=f"+91{9000000000 + i}",
                    created_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                )
            )
            existing_user_ids.add(uid)
        session.commit()
        print(f"Created/kept {n_users} users (U1..U{n_users})")
        # For each user: some orders, some events (search without buy, habits)
        existing_order_ids = {r.id for r in session.query(Order.id).all()}
        for i in range(1, n_users + 1):
            uid = f"U{i}"
            # 0–4 orders per user
            n_orders = random.randint(0, 4)
            for _ in range(n_orders):
                oid = f"ORD-SEED-{uuid.uuid4().hex[:8].upper()}"
                if oid in existing_order_ids:
                    continue
                existing_order_ids.add(oid)
                n_items = random.randint(1, 4)
                items_ids = random.sample(product_ids, min(n_items, len(product_ids)))
                total = 0.0
                order_items = []
                for pid in items_ids:
                    p = session.query(Product).filter(Product.id == pid).first()
                    if not p:
                        continue
                    qty = random.randint(1, 2)
                    price = p.price
                    total += price * qty
                    order_items.append((pid, qty, price))
                if not order_items:
                    continue
                created = datetime.utcnow() - timedelta(days=random.randint(1, 90))
                session.add(
                    Order(
                        id=oid,
                        user_id=uid,
                        total=round(total, 2),
                        delivery_method=random.choice(["home_delivery", "store_pickup"]),
                        status=random.choice(["pending", "confirmed", "delivered", "picked_up"]),
                        delivery_address="123 Seed St" if random.random() > 0.5 else None,
                        store_location=random.choice(["store_1", "store_2", "store_3"]) if random.random() > 0.5 else None,
                        qr_code=None,
                        created_at=created,
                        updated_at=created,
                    )
                )
                for pid, qty, price in order_items:
                    session.add(
                        OrderItem(order_id=oid, product_id=pid, quantity=qty, price=price)
                    )
            # Events: search, product_click, cart_add (some searches never lead to purchase)
            for _ in range(random.randint(3, 15)):
                event_type = random.choice(EVENT_TYPES)
                ts = datetime.utcnow() - timedelta(hours=random.randint(1, 720))
                session.add(
                    Event(
                        session_id=f"sess_{uid}_{uuid.uuid4().hex[:8]}",
                        user_id=uid,
                        event_type=event_type,
                        product_id=random.choice(product_ids) if event_type in ("product_click", "cart_add", "cart_remove") else None,
                        category=random.choice(categories) if event_type == "category_view" else None,
                        query=random.choice(["shirt", "phone", "shoes", "gift", "watch", "bag", "electronics"]) if event_type == "search" else None,
                        amount=random.choice([500, 1000, 2000, 5000]) if event_type == "budget_signal" else None,
                        timestamp=ts,
                    )
                )
        session.commit()
        # Habits: make some users have repeated same product (e.g. U1, U2 bought same product 2+ times)
        habit_users = random.sample([f"U{i}" for i in range(1, n_users + 1)], min(20, n_users))
        for uid in habit_users:
            pid = random.choice(product_ids)
            for _ in range(2):
                oid = f"ORD-HABIT-{uuid.uuid4().hex[:8].upper()}"
                if oid in existing_order_ids:
                    continue
                existing_order_ids.add(oid)
                p = session.query(Product).filter(Product.id == pid).first()
                if not p:
                    continue
                created = datetime.utcnow() - timedelta(days=random.randint(5, 60))
                session.add(
                    Order(
                        id=oid,
                        user_id=uid,
                        total=round(p.price, 2),
                        delivery_method="home_delivery",
                        status="delivered",
                        delivery_address="123 Habit St",
                        store_location=None,
                        qr_code=None,
                        created_at=created,
                        updated_at=created,
                    )
                )
                session.add(OrderItem(order_id=oid, product_id=pid, quantity=1, price=p.price))
        session.commit()
        # Festivals
        if session.query(Festival.id).first() is None:
            now = datetime.utcnow()
            session.add(
                Festival(
                    name="Diwali",
                    start_date=now.replace(month=11, day=1),
                    end_date=now.replace(month=11, day=5),
                    suggested_categories=["Clothing", "Home & Living", "Electronics"],
                    description="Festival of lights",
                )
            )
            session.add(
                Festival(
                    name="Holi",
                    start_date=now.replace(month=3, day=1),
                    end_date=now.replace(month=3, day=10),
                    suggested_categories=["Clothing", "Beauty"],
                    description="Festival of colors",
                )
            )
            session.add(
                Festival(
                    name="Christmas",
                    start_date=now.replace(month=12, day=20),
                    end_date=now.replace(month=12, day=26),
                    suggested_categories=["Clothing", "Toys & Games", "Home & Living"],
                    description="Christmas shopping",
                )
            )
            session.commit()
            print("Seeded festivals (Diwali, Holi, Christmas)")
        # FAQ
        if session.query(FAQ.id).first() is None:
            faqs = [
                ("What is your return policy?", "We offer 7-day returns for most items in unused condition. Keep the original packaging.", "returns"),
                ("How do I track my order?", "Log in and go to Profile > Orders. Click your order to see status and tracking.", "orders"),
                ("What is Aura Wallet / AuraPoints?", "AuraPoints are rewards earned on purchases (5-7%). They are valid for 30 days and can be used for future orders.", "wallet"),
                ("Can I pick up my order in store?", "Yes. Choose Store Pickup at checkout and select a store. You'll get a QR code to show at the store.", "delivery"),
                ("How long does delivery take?", "Home delivery typically takes 3-5 business days. Store pickup is ready within 24-48 hours.", "delivery"),
                ("Do you ship internationally?", "Currently we ship within India only.", "delivery"),
                ("How do I apply AuraPoints at checkout?", "At checkout you can choose to apply your available AuraPoints balance to reduce the order total.", "wallet"),
                ("What payment methods do you accept?", "We accept cards, UPI, net banking, and AuraPoints.", "payment"),
                ("How do I cancel an order?", "Go to Profile > Orders, open the order and use Cancel if it is still in Pending or Confirmed state.", "orders"),
                ("Is my data secure?", "We use secure connections and do not store your card details. Payment is processed by certified providers.", "security"),
            ]
            for q, a, cat in faqs:
                session.add(FAQ(question=q, answer=a, category=cat))
            session.commit()
            print(f"Seeded {len(faqs)} FAQ entries")
    finally:
        session.close()
    print("Seed complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
