"""
Festival-based recommendations: suggest products by current/upcoming festival.
"""
from datetime import datetime
from typing import List, Optional

from recommend.db import get_session
from recommend.models_db import Festival, Product


def get_current_or_upcoming_festival(days_ahead: int = 14) -> Optional[Festival]:
    """Return a festival that is active or starts within days_ahead."""
    session = get_session()
    try:
        now = datetime.utcnow()
        end = now.replace(hour=23, minute=59, second=59) if days_ahead else now
        if days_ahead:
            from datetime import timedelta
            end = now + timedelta(days=days_ahead)
        festivals = (
            session.query(Festival)
            .filter(Festival.start_date <= end, Festival.end_date >= now)
            .order_by(Festival.start_date)
            .limit(1)
            .all()
        )
        if festivals:
            return festivals[0]
        # Upcoming: start_date in future, within days_ahead
        from datetime import timedelta
        upcoming = (
            session.query(Festival)
            .filter(
                Festival.start_date >= now,
                Festival.start_date <= now + timedelta(days=days_ahead),
            )
            .order_by(Festival.start_date)
            .limit(1)
            .all()
        )
        return upcoming[0] if upcoming else None
    finally:
        session.close()


def get_festival_recommendations(limit: int = 10) -> List[dict]:
    """
    If a festival is current or upcoming, return products from suggested_categories.
    Returns list of product dicts (id, name, price, category, ...).
    """
    fest = get_current_or_upcoming_festival()
    if not fest or not fest.suggested_categories:
        return []
    session = get_session()
    try:
        categories = fest.suggested_categories if isinstance(fest.suggested_categories, list) else []
        if not categories:
            return []
        products = (
            session.query(Product)
            .filter(Product.category.in_(categories), Product.in_stock == True)
            .order_by(Product.rating.desc(), Product.review_count.desc())
            .limit(limit * 2)
            .all()
        )
        # Dedupe and limit
        seen = set()
        out = []
        for p in products:
            if p.id in seen:
                continue
            seen.add(p.id)
            out.append({
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category,
                "rating": p.rating,
                "reason": f"Suggested for {fest.name}",
            })
            if len(out) >= limit:
                break
        return out
    finally:
        session.close()
