"""
Order management and QR code generation for store pickup.
Orders are persisted to data/orders.json so they survive server restarts.
"""
import json
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from app.models import Order, OrderStatus, OrderItem, DeliveryMethod, UserProfile

ORDERS_PATH = Path(__file__).resolve().parent.parent / "data" / "orders.json"

# In-memory storage (loaded from file on first access)
_orders: Dict[str, Order] = {}
_user_profiles: Dict[str, UserProfile] = {}
_orders_loaded = False


def _load_orders() -> None:
    global _orders, _orders_loaded
    if _orders_loaded:
        return
    _orders_loaded = True
    if not ORDERS_PATH.exists():
        return
    try:
        with open(ORDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for o in data.get("orders", []):
            order = Order(**o)
            _orders[order.id] = order
    except Exception:
        pass


def _save_orders() -> None:
    ORDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(ORDERS_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"orders": [o.model_dump() for o in _orders.values()]},
                f,
                indent=2,
                default=str,
            )
    except Exception:
        pass


def generate_qr_code_data(order_id: str, total: float, store_location: str = "") -> str:
    """
    Generate QR code data for store pickup.
    
    Format: ORDER_ID|CHECKSUM|TOTAL|STORE
    - ORDER_ID: Human-readable order ID (staff can type if scanner fails)
    - CHECKSUM: 8-char security hash to prevent fraud
    - TOTAL: Order total for quick verification
    - STORE: Store location identifier
    
    This format works offline - staff can see order details immediately.
    """
    # Create checksum using order_id + total + secret key
    secret_key = "AURASHOP_SECRET_2026"  # In production, use env variable
    checksum_input = f"{order_id}{total}{secret_key}"
    checksum = hashlib.sha256(checksum_input.encode()).hexdigest()[:8].upper()
    
    # Format: ORD-ABC12345|A1B2C3D4|99.99|store_1
    store_code = store_location.split()[-1] if store_location else "STORE"
    return f"{order_id}|{checksum}|{total:.2f}|{store_code}"


def create_order(
    user_id: str,
    items: List[OrderItem],
    delivery_method: DeliveryMethod,
    delivery_address: Optional[str] = None,
    store_location: Optional[str] = None,
) -> Order:
    """Create a new order."""
    _load_orders()
    order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
    total = sum(item.price * item.quantity for item in items)
    now = datetime.utcnow().isoformat()
    
    qr_code = None
    if delivery_method == DeliveryMethod.STORE_PICKUP:
        qr_code = generate_qr_code_data(order_id, total, store_location or "")
    
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
        created_at=now,
        updated_at=now,
    )
    _orders[order_id] = order
    _save_orders()
    
    # Add pending AuraPoints immediately
    try:
        from app.wallet_service import add_pending_points
        add_pending_points(user_id, order_id, total)
        print(f"✓ Added pending AuraPoints for order {order_id}")
    except Exception as e:
        print(f"Failed to add pending points for order {order_id}: {e}")
    
    return order


def get_order(order_id: str) -> Optional[Order]:
    """Get order by ID."""
    _load_orders()
    return _orders.get(order_id)


def get_user_orders(user_id: str) -> List[Order]:
    """Get all orders for a user, newest first."""
    _load_orders()
    user_orders = [o for o in _orders.values() if o.user_id == user_id]
    return sorted(user_orders, key=lambda o: o.created_at or "", reverse=True)


def update_order_status(order_id: str, status: OrderStatus) -> Optional[Order]:
    """Update order status and trigger cashback if completed."""
    _load_orders()
    order = _orders.get(order_id)
    if order:
        old_status = order.status
        order.status = status
        order.updated_at = datetime.utcnow().isoformat()
        _orders[order_id] = order
        _save_orders()
        
        # Activate pending AuraPoints when order is completed
        if status in [OrderStatus.DELIVERED, OrderStatus.PICKED_UP] and old_status != status:
            try:
                from app.wallet_service import activate_pending_points
                result = activate_pending_points(order_id)
                if result:
                    print(f"✓ Activated AuraPoints for order {order_id}")
                else:
                    print(f"No pending points found for order {order_id}")
            except Exception as e:
                print(f"Failed to activate points for order {order_id}: {e}")
    return order


def verify_qr_checksum(order_id: str, checksum: str, total: float) -> bool:
    """Verify QR code checksum for offline validation."""
    secret_key = "AURASHOP_SECRET_2026"
    expected_checksum = hashlib.sha256(f"{order_id}{total}{secret_key}".encode()).hexdigest()[:8].upper()
    return checksum.upper() == expected_checksum


def verify_pickup_qr(qr_code: str) -> Optional[Order]:
    """
    Verify QR code and return order if valid.
    
    Supports two formats:
    1. New format: ORDER_ID|CHECKSUM|TOTAL|STORE (offline-capable)
    2. Old format: AURASHOP-PICKUP-HASH (backward compatibility)
    """
    _load_orders()
    
    # Try new format first: ORD-ABC12345|A1B2C3D4|99.99|store_1
    if "|" in qr_code:
        parts = qr_code.split("|")
        if len(parts) >= 3:
            order_id = parts[0]
            checksum = parts[1]
            try:
                total = float(parts[2])
            except ValueError:
                return None
            
            # Find order by ID
            order = _orders.get(order_id)
            if order and order.delivery_method == DeliveryMethod.STORE_PICKUP:
                # Verify checksum
                if verify_qr_checksum(order_id, checksum, total):
                    return order
            return None
    
    # Fall back to old format for backward compatibility
    for order in _orders.values():
        if order.qr_code == qr_code and order.delivery_method == DeliveryMethod.STORE_PICKUP:
            return order
    
    return None


def complete_pickup(order_id: str) -> Optional[Order]:
    """Mark order as picked up."""
    return update_order_status(order_id, OrderStatus.PICKED_UP)


def get_user_profile(user_id: str) -> Optional[UserProfile]:
    """Get user profile."""
    return _user_profiles.get(user_id)


def create_or_update_profile(
    user_id: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    addresses: Optional[List[str]] = None,
    preferred_stores: Optional[List[str]] = None,
) -> UserProfile:
    """Create or update user profile."""
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
    else:
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


# Demo stores
AVAILABLE_STORES = [
    {"id": "store_1", "name": "AuraShop Downtown", "address": "123 Main St, City Center"},
    {"id": "store_2", "name": "AuraShop Mall", "address": "456 Shopping Mall, North District"},
    {"id": "store_3", "name": "AuraShop Express", "address": "789 Quick Mart, South Area"},
]


def get_available_stores() -> List[dict]:
    """Get list of available stores for pickup."""
    return AVAILABLE_STORES
