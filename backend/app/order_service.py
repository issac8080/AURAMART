"""
Order management and QR code generation for store pickup.
Orders are read/written from recommend DB only. JSON data is synced into DB on startup (db_sync).
"""
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional
from app.models import Order, OrderStatus, OrderItem, DeliveryMethod, UserProfile

# In-memory user profiles (no profile table in recommend DB; User has name/email/phone only)
_user_profiles: dict = {}


def _db_order_to_app(db_order, db_items) -> Order:
    """Map recommend DB Order + OrderItems to app Order."""
    status_val = (db_order.status or "pending").lower()
    try:
        status = OrderStatus(status_val)
    except ValueError:
        status = OrderStatus.PENDING
    dm_val = (db_order.delivery_method or "home_delivery").lower()
    try:
        dm = DeliveryMethod(dm_val)
    except ValueError:
        dm = DeliveryMethod.HOME_DELIVERY
    items = [
        OrderItem(product_id=it.product_id, quantity=int(it.quantity or 1), price=float(it.price or 0))
        for it in db_items
    ]
    created = db_order.created_at.isoformat() if hasattr(db_order.created_at, "isoformat") else str(db_order.created_at or "")
    updated = db_order.updated_at.isoformat() if hasattr(db_order.updated_at, "isoformat") else str(db_order.updated_at or "")
    return Order(
        id=db_order.id,
        user_id=db_order.user_id,
        items=items,
        total=float(db_order.total or 0),
        delivery_method=dm,
        status=status,
        delivery_address=db_order.delivery_address,
        store_location=db_order.store_location,
        qr_code=db_order.qr_code,
        created_at=created,
        updated_at=updated,
    )


def generate_qr_code_data(order_id: str, total: float, store_location: str = "") -> str:
    """
    Generate QR code data for store pickup.
    Format: ORDER_ID|CHECKSUM|TOTAL|STORE
    """
    secret_key = "AURASHOP_SECRET_2026"
    checksum_input = f"{order_id}{total}{secret_key}"
    checksum = hashlib.sha256(checksum_input.encode()).hexdigest()[:8].upper()
    store_code = store_location.split()[-1] if store_location else "STORE"
    return f"{order_id}|{checksum}|{total:.2f}|{store_code}"


def create_order(
    user_id: str,
    items: List[OrderItem],
    delivery_method: DeliveryMethod,
    delivery_address: Optional[str] = None,
    store_location: Optional[str] = None,
) -> Order:
    """Create a new order in recommend DB only."""
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    total = sum(item.price * item.quantity for item in items)
    now = datetime.utcnow()
    qr_code = None
    if delivery_method == DeliveryMethod.STORE_PICKUP:
        qr_code = generate_qr_code_data(order_id, total, store_location or "")

    try:
        from recommend.db import get_session
        from recommend.models_db import User, Order as DbOrder, OrderItem as DbOrderItem

        session = get_session()
        try:
            existing_user = session.query(User).filter(User.user_id == user_id).first()
            if not existing_user:
                session.add(
                    User(user_id=user_id, name=None, email=None, phone=None, created_at=now)
                )
                session.flush()
            db_order = DbOrder(
                id=order_id,
                user_id=user_id,
                total=total,
                delivery_method=delivery_method.value if hasattr(delivery_method, "value") else str(delivery_method),
                status=OrderStatus.PENDING.value,
                delivery_address=delivery_address,
                store_location=store_location,
                qr_code=qr_code,
                created_at=now,
                updated_at=now,
            )
            session.add(db_order)
            session.flush()
            for it in items:
                session.add(
                    DbOrderItem(
                        order_id=order_id,
                        product_id=it.product_id,
                        quantity=int(it.quantity),
                        price=float(it.price),
                    )
                )
            session.commit()
        finally:
            session.close()
    except Exception as e:
        print(f"order_service: create_order failed {e}")
        raise

    order = Order(
        id=order_id,
        user_id=user_id,
        items=items,
        total=total,
        delivery_method=delivery_method,
        status=OrderStatus.PENDING,
        delivery_address=delivery_address,
        store_location=store_location,
        qr_code=qr_code,
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )

    try:
        from app.wallet_service import add_pending_points
        add_pending_points(user_id, order_id, total)
        print(f"✓ Added pending AuraPoints for order {order_id}")
    except Exception as e:
        print(f"Failed to add pending points for order {order_id}: {e}")

    return order


def get_order(order_id: str) -> Optional[Order]:
    """Get order by ID from recommend DB."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Order as DbOrder, OrderItem as DbOrderItem

        session = get_session()
        try:
            db_order = session.query(DbOrder).filter(DbOrder.id == order_id).first()
            if not db_order:
                return None
            db_items = session.query(DbOrderItem).filter(DbOrderItem.order_id == order_id).all()
            return _db_order_to_app(db_order, db_items)
        finally:
            session.close()
    except Exception:
        return None


def get_user_orders(user_id: str) -> List[Order]:
    """Get all orders for a user from recommend DB, newest first."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Order as DbOrder, OrderItem as DbOrderItem

        session = get_session()
        try:
            db_orders = (
                session.query(DbOrder)
                .filter(DbOrder.user_id == user_id)
                .order_by(DbOrder.created_at.desc())
                .all()
            )
            out = []
            for db_order in db_orders:
                db_items = session.query(DbOrderItem).filter(DbOrderItem.order_id == db_order.id).all()
                out.append(_db_order_to_app(db_order, db_items))
            return out
        finally:
            session.close()
    except Exception:
        return []


def update_order_status(order_id: str, status: OrderStatus) -> Optional[Order]:
    """Update order status in recommend DB and trigger cashback if completed."""
    try:
        from recommend.db import get_session
        from recommend.models_db import Order as DbOrder, OrderItem as DbOrderItem

        session = get_session()
        try:
            db_order = session.query(DbOrder).filter(DbOrder.id == order_id).first()
            if not db_order:
                return None
            old_status_val = (db_order.status or "").lower()
            db_order.status = status.value if hasattr(status, "value") else str(status)
            db_order.updated_at = datetime.utcnow()
            session.commit()
            db_items = session.query(DbOrderItem).filter(DbOrderItem.order_id == order_id).all()
            order = _db_order_to_app(db_order, db_items)
            completed_vals = ("delivered", "picked_up")
            if status in [OrderStatus.DELIVERED, OrderStatus.PICKED_UP] and old_status_val not in completed_vals:
                try:
                    from app.wallet_service import activate_pending_points
                    result = activate_pending_points(order_id)
                    if result:
                        print(f"✓ Activated AuraPoints for order {order_id}")
                except Exception as e:
                    print(f"Failed to activate points for order {order_id}: {e}")
            return order
        finally:
            session.close()
    except Exception:
        return None


def verify_qr_checksum(order_id: str, checksum: str, total: float) -> bool:
    """Verify QR code checksum for offline validation."""
    secret_key = "AURASHOP_SECRET_2026"
    expected_checksum = hashlib.sha256(f"{order_id}{total}{secret_key}".encode()).hexdigest()[:8].upper()
    return checksum.upper() == expected_checksum


def verify_pickup_qr(qr_code: str) -> Optional[Order]:
    """Verify QR code and return order if valid. Reads from recommend DB."""
    if "|" in qr_code:
        parts = qr_code.split("|")
        if len(parts) >= 3:
            order_id = parts[0]
            checksum = parts[1]
            try:
                total = float(parts[2])
            except ValueError:
                return None
            order = get_order(order_id)
            if order and order.delivery_method == DeliveryMethod.STORE_PICKUP:
                if verify_qr_checksum(order_id, checksum, total):
                    return order
            return None
    # Fallback: match qr_code string
    try:
        from recommend.db import get_session
        from recommend.models_db import Order as DbOrder, OrderItem as DbOrderItem

        session = get_session()
        try:
            db_order = session.query(DbOrder).filter(
                DbOrder.qr_code == qr_code,
                DbOrder.delivery_method == "store_pickup",
            ).first()
            if not db_order:
                return None
            db_items = session.query(DbOrderItem).filter(DbOrderItem.order_id == db_order.id).all()
            return _db_order_to_app(db_order, db_items)
        finally:
            session.close()
    except Exception:
        return None


def complete_pickup(order_id: str) -> Optional[Order]:
    """Mark order as picked up."""
    return update_order_status(order_id, OrderStatus.PICKED_UP)


def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """Get user profile (in-memory; recommend DB User has name/email/phone only)."""
    return _user_profiles.get(user_id)


def create_or_update_profile(
    user_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    addresses: Optional[List[str]] = None,
    preferred_stores: Optional[List[str]] = None,
) -> UserProfile:
    """Create or update user profile (in-memory)."""
    existing = _user_profiles.get(user_id)
    if existing:
        if name is not None:
            existing.name = name
        if email is not None:
            existing.email = email
        if phone is not None:
            existing.phone = phone
        if addresses is not None:
            existing.addresses = addresses
        if preferred_stores is not None:
            existing.preferred_stores = preferred_stores
        return existing
    profile = UserProfile(
        user_id=user_id,
        name=name,
        email=email,
        phone=phone,
        addresses=addresses or [],
        preferred_stores=preferred_stores or [],
        created_at=datetime.utcnow().isoformat(),
    )
    _user_profiles[user_id] = profile
    return profile


AVAILABLE_STORES = [
    {"id": "store_1", "name": "AuraShop Downtown", "address": "123 Main St, City Center"},
    {"id": "store_2", "name": "AuraShop Mall", "address": "456 Shopping Mall, North District"},
    {"id": "store_3", "name": "AuraShop Express", "address": "789 Quick Mart, South Area"},
]


def get_available_stores() -> List[dict]:
    """Get list of available stores for pickup."""
    return AVAILABLE_STORES
