"""
User identity from database (recommend User table).
get_or_create_user_by_email returns stable user_id for cart, orders, wallet, chat.
"""
import hashlib
from typing import Optional


def _stable_user_id(email: str) -> str:
    """Stable user_id from email (same email always gets same id)."""
    normalized = (email or "").strip().lower()
    if not normalized or "@" not in normalized:
        return ""
    h = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"user_{h}"


def get_or_create_user_by_email(email: str, name: Optional[str] = None) -> dict:
    """
    Get or create user in recommend DB (User table). Returns { user_id, email, name }.
    user_id is stable per email so cart/orders/wallet key by it when logged in.
    """
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return {"user_id": "", "email": email or "", "name": name or "User"}
    user_id = _stable_user_id(email)
    name = (name or email.split("@")[0].replace(".", " ").replace("_", " ")).strip() or "User"
    if name:
        name = name[0].upper() + name[1:]

    try:
        from recommend.db import get_session
        from recommend.models_db import User
        session = get_session()
        try:
            existing = session.query(User).filter(User.user_id == user_id).first()
            if existing:
                if name and (existing.name is None or existing.name != name):
                    existing.name = name
                if existing.email is None or existing.email != email:
                    existing.email = email
                session.commit()
                out = {"user_id": user_id, "email": email, "name": existing.name or name}
            else:
                user = User(user_id=user_id, email=email, name=name, phone=None)
                session.add(user)
                session.commit()
                out = {"user_id": user_id, "email": email, "name": name}
            # Sync to app layer profile (order_service in-memory) so get_user_profile returns name
            try:
                from app.order_service import create_or_update_profile
                create_or_update_profile(user_id, name=out["name"], email=email)
            except Exception:
                pass
            return out
        finally:
            session.close()
    except Exception as e:
        print(f"user_service get_or_create_user_by_email: {e}")
        return {"user_id": user_id, "email": email, "name": name}
