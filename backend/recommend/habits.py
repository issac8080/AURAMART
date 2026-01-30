"""
Habit detection: users who buy the same product repeatedly.
Returns "Wanna reorder that?" payload (product_id, user_id) for agentic reorder.
"""
from typing import List
from collections import Counter

from recommend.db import get_session
from recommend.models_db import Order, OrderItem


def get_habit_products(user_id: str, min_orders: int = 2) -> List[dict]:
    """
    Find products the user has ordered multiple times (reorder habits).
    Returns list of { product_id, name, price, order_count } for "Wanna reorder that?".
    """
    session = get_session()
    try:
        orders = (
            session.query(Order)
            .filter(Order.user_id == user_id)
            .all()
        )
        product_counts = Counter()
        for o in orders:
            for item in o.items:
                product_counts[item.product_id] += 1
        habits = [
            {"product_id": pid, "order_count": count}
            for pid, count in product_counts.items()
            if count >= min_orders
        ]
        if not habits:
            return []
        from recommend.models_db import Product
        out = []
        for h in habits:
            p = session.query(Product).filter(Product.id == h["product_id"]).first()
            if p and p.in_stock:
                out.append({
                    "product_id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "order_count": h["order_count"],
                })
        return out
    finally:
        session.close()
