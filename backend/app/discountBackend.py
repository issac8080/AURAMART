"""
Discount Backend - All discount types for AuraShop.
1. New user discount
2. Price drop notification (user searched/viewed, price went down)
3. Loyal customer discount
4. Vendor-side discount
5. Festival discounts
6. Subscription-based discount
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel

# Optional: get_product for price checks
def _get_product(product_id: str):
    try:
        from app.data_store import get_product
        return get_product(product_id)
    except Exception:
        return None


def _get_user_orders_count(user_id: str) -> int:
    try:
        from app.order_service import get_user_orders
        orders = get_user_orders(user_id)
        completed = [o for o in orders if o.status.value in ("delivered", "picked_up")]
        return len(completed)
    except Exception:
        return 0


# ---------- Models ----------

class DiscountType(str, Enum):
    NEW_USER = "new_user"
    PRICE_DROP = "price_drop"
    LOYAL_CUSTOMER = "loyal_customer"
    VENDOR = "vendor"
    FESTIVAL = "festival"
    SUBSCRIPTION = "subscription"


class AppliedDiscount(BaseModel):
    discount_type: DiscountType
    label: str
    description: str
    percent: float = 0.0
    amount: float = 0.0
    code: Optional[str] = None
    product_id: Optional[str] = None  # for vendor/price_drop
    valid_until: Optional[str] = None


class PriceDropNotification(BaseModel):
    product_id: str
    product_name: str
    old_price: float
    new_price: float
    percent_off: float
    image_url: Optional[str] = None


class SubscriptionTier(BaseModel):
    id: str
    name: str
    discount_percent: float
    monthly_price: float


# ---------- Storage (in-memory + JSON for persistence) ----------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PRICE_HISTORY_PATH = DATA_DIR / "price_history.json"
PRICE_ALERTS_PATH = DATA_DIR / "price_alerts.json"
DISCOUNT_DATA_PATH = DATA_DIR / "discount_data.json"

# product_id -> list of { "at": iso datetime, "price": float }
_price_history: Dict[str, List[dict]] = {}
# session_id or user_id -> set of product_ids they want alerts for (viewed/searched)
_watched_products: Dict[str, List[str]] = {}
# user_id -> subscription_tier_id or None
_subscriptions: Dict[str, str] = {}
# vendor discounts: product_id or brand -> percent
_vendor_discounts: Dict[str, float] = {}
# festival: name -> { start, end, percent, label }
_festivals: List[dict] = []

SUBSCRIPTION_TIERS: List[SubscriptionTier] = [
    SubscriptionTier(id="starter", name="Aura Starter", discount_percent=5.0, monthly_price=50),
    SubscriptionTier(id="basic", name="Aura Basic", discount_percent=5.0, monthly_price=99),
    SubscriptionTier(id="plus", name="Aura Plus", discount_percent=10.0, monthly_price=199),
    SubscriptionTier(id="premium", name="Aura Premium", discount_percent=15.0, monthly_price=399),
]


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _load_discount_data() -> None:
    global _price_history, _watched_products, _subscriptions, _vendor_discounts, _festivals
    _price_history = _load_json(PRICE_HISTORY_PATH, {})
    _watched_products = _load_json(PRICE_ALERTS_PATH, {})
    data = _load_json(DISCOUNT_DATA_PATH, {})
    _subscriptions = data.get("subscriptions", _subscriptions)
    _vendor_discounts = data.get("vendor_discounts", _vendor_discounts)
    _festivals = data.get("festivals", _festivals)


def _save_discount_data() -> None:
    _save_json(PRICE_ALERTS_PATH, _watched_products)
    _save_json(DISCOUNT_DATA_PATH, {
        "subscriptions": _subscriptions,
        "vendor_discounts": _vendor_discounts,
        "festivals": _festivals,
    })


# Initialize with demo data if empty
def _ensure_demo_data() -> None:
    _load_discount_data()
    if not _festivals:
        now = datetime.utcnow()
        _festivals.extend([
            {
                "id": "republic_day",
                "label": "Republic Day Sale",
                "percent": 15.0,
                "start": (now - timedelta(days=2)).isoformat(),
                "end": (now + timedelta(days=5)).isoformat(),
            },
            {
                "id": "diwali",
                "label": "Diwali Special",
                "percent": 20.0,
                "start": (now + timedelta(days=30)).isoformat(),
                "end": (now + timedelta(days=37)).isoformat(),
            },
        ])
    if not _vendor_discounts:
        _vendor_discounts["Alisha"] = 10.0
        _vendor_discounts["AW"] = 5.0
        _vendor_discounts["FabHomeDecor"] = 15.0
    _save_discount_data()


# ---------- 1. New user discount ----------

NEW_USER_DISCOUNT_PERCENT = 10.0
NEW_USER_MAX_ORDER_TOTAL = 2000.0  # cap discount on first order value


def get_new_user_discount(user_id: str, order_total: float) -> Optional[AppliedDiscount]:
    _load_discount_data()
    count = _get_user_orders_count(user_id)
    if count > 0:
        return None
    cap = min(order_total * (NEW_USER_DISCOUNT_PERCENT / 100), NEW_USER_MAX_ORDER_TOTAL * (NEW_USER_DISCOUNT_PERCENT / 100))
    return AppliedDiscount(
        discount_type=DiscountType.NEW_USER,
        label="New User Welcome",
        description=f"{NEW_USER_DISCOUNT_PERCENT}% off your first order (max ₹{cap:.0f})",
        percent=NEW_USER_DISCOUNT_PERCENT,
        amount=min(order_total * NEW_USER_DISCOUNT_PERCENT / 100, NEW_USER_MAX_ORDER_TOTAL * NEW_USER_DISCOUNT_PERCENT / 100),
    )


# ---------- 2. Price drop notification ----------

def record_product_view(session_id: str, user_id: Optional[str], product_id: str) -> None:
    """Call when user views or searches a product - they become eligible for price drop alerts."""
    _load_discount_data()
    key = user_id or session_id
    if key not in _watched_products:
        _watched_products[key] = []
    if product_id not in _watched_products[key]:
        _watched_products[key].append(product_id)
    _watched_products[key] = _watched_products[key][-50:]  # keep last 50
    _save_json(PRICE_ALERTS_PATH, _watched_products)


def record_price(product_id: str, price: float) -> None:
    """Record current price for a product (call when price is read/updated)."""
    _load_discount_data()
    if product_id not in _price_history:
        _price_history[product_id] = []
    hist = _price_history[product_id]
    now = datetime.utcnow().isoformat()
    if not hist or hist[-1].get("price") != price:
        hist.append({"at": now, "price": price})
    _price_history[product_id] = hist[-100:]  # keep last 100
    _save_json(PRICE_HISTORY_PATH, _price_history)


def get_price_drop_notifications(session_id: str, user_id: Optional[str] = None) -> List[PriceDropNotification]:
    """Return products that this user/session watched and that have a recorded price drop."""
    _load_discount_data()
    key = user_id or session_id
    watched = _watched_products.get(key, [])
    out: List[PriceDropNotification] = []
    for pid in watched:
        hist = _price_history.get(pid, [])
        if len(hist) < 2:
            continue
        old_price = hist[-2]["price"]
        new_price = hist[-1]["price"]
        if new_price >= old_price:
            continue
        product = _get_product(pid)
        name = product.name if product else pid
        image_url = product.image_url if product else None
        percent_off = round((1 - new_price / old_price) * 100, 1)
        out.append(PriceDropNotification(
            product_id=pid,
            product_name=name,
            old_price=old_price,
            new_price=new_price,
            percent_off=percent_off,
            image_url=image_url,
        ))
    return out


def simulate_price_drop(product_id: str, new_price: float) -> bool:
    """For demo: set a lower price and record history so price-drop notifications appear."""
    product = _get_product(product_id)
    if not product:
        return False
    record_price(product_id, product.price)  # record current as "old"
    # We don't change products.json; we just add a new history entry with new_price
    _load_discount_data()
    if product_id not in _price_history:
        _price_history[product_id] = [{"at": datetime.utcnow().isoformat(), "price": product.price}]
    _price_history[product_id].append({"at": datetime.utcnow().isoformat(), "price": new_price})
    _save_json(PRICE_HISTORY_PATH, _price_history)
    return True


# ---------- 3. Loyal customer discount ----------

LOYAL_ORDER_THRESHOLD = 3
LOYAL_DISCOUNT_PERCENT = 5.0
SUPER_LOYAL_ORDER_THRESHOLD = 10
SUPER_LOYAL_DISCOUNT_PERCENT = 10.0


def get_loyal_customer_discount(user_id: str, order_total: float) -> Optional[AppliedDiscount]:
    count = _get_user_orders_count(user_id)
    if count >= SUPER_LOYAL_ORDER_THRESHOLD:
        return AppliedDiscount(
            discount_type=DiscountType.LOYAL_CUSTOMER,
            label="Super Loyal Customer",
            description=f"Thank you! {SUPER_LOYAL_DISCOUNT_PERCENT}% off for being a top customer.",
            percent=SUPER_LOYAL_DISCOUNT_PERCENT,
            amount=order_total * SUPER_LOYAL_DISCOUNT_PERCENT / 100,
        )
    if count >= LOYAL_ORDER_THRESHOLD:
        return AppliedDiscount(
            discount_type=DiscountType.LOYAL_CUSTOMER,
            label="Loyal Customer",
            description=f"{LOYAL_DISCOUNT_PERCENT}% off for your loyalty ({count} orders).",
            percent=LOYAL_DISCOUNT_PERCENT,
            amount=order_total * LOYAL_DISCOUNT_PERCENT / 100,
        )
    return None


# ---------- 4. Vendor discount ----------

def get_vendor_discount_for_product(product_id: str, product_price: float, brand: Optional[str]) -> Optional[AppliedDiscount]:
    _load_discount_data()
    percent = None
    if product_id in _vendor_discounts:
        percent = _vendor_discounts[product_id]
    if percent is None and brand and brand in _vendor_discounts:
        percent = _vendor_discounts[brand]
    if percent is None:
        return None
    return AppliedDiscount(
        discount_type=DiscountType.VENDOR,
        label="Vendor Offer",
        description=f"{percent}% off from vendor",
        percent=percent,
        amount=product_price * percent / 100,
        product_id=product_id,
    )


# ---------- 5. Festival discount ----------

def get_active_festival_discount() -> Optional[AppliedDiscount]:
    _ensure_demo_data()
    now = datetime.utcnow()
    for f in _festivals:
        start = datetime.fromisoformat(f["start"])
        end = datetime.fromisoformat(f["end"])
        if start <= now <= end:
            return AppliedDiscount(
                discount_type=DiscountType.FESTIVAL,
                label=f.get("label", "Festival Sale"),
                description=f"{f['percent']}% off - {f.get('label', '')}",
                percent=float(f["percent"]),
                amount=0,  # applied on cart total
                valid_until=f["end"],
            )
    return None


# ---------- 6. Subscription discount ----------

def set_user_subscription(user_id: str, tier_id: Optional[str]) -> None:
    _load_discount_data()
    if tier_id is None:
        _subscriptions.pop(user_id, None)
    else:
        _subscriptions[user_id] = tier_id
    _save_discount_data()


def get_subscription_discount(user_id: str, order_total: float) -> Optional[AppliedDiscount]:
    _load_discount_data()
    tier_id = _subscriptions.get(user_id)
    if not tier_id:
        return None
    tier = next((t for t in SUBSCRIPTION_TIERS if t.id == tier_id), None)
    if not tier:
        return None
    return AppliedDiscount(
        discount_type=DiscountType.SUBSCRIPTION,
        label=tier.name,
        description=f"{tier.discount_percent}% off with your subscription",
        percent=tier.discount_percent,
        amount=order_total * tier.discount_percent / 100,
    )


# ---------- Aggregate: all applicable discounts for checkout ----------

def get_applicable_discounts(
    user_id: str,
    session_id: str,
    cart_items: List[dict],
    order_total: float,
) -> List[AppliedDiscount]:
    """
    cart_items: list of { "product_id", "price", "quantity", "brand" (optional) }
    Returns list of discounts that can be applied. Frontend/checkout can choose one or stack by policy.
    """
    applied: List[AppliedDiscount] = []
    seen_types: set = set()

    # New user (only one of new_user vs loyal)
    new_user = get_new_user_discount(user_id, order_total)
    if new_user:
        applied.append(new_user)
        seen_types.add(DiscountType.NEW_USER)

    # Loyal customer (only if not new user)
    if DiscountType.NEW_USER not in seen_types:
        loyal = get_loyal_customer_discount(user_id, order_total)
        if loyal:
            applied.append(loyal)
            seen_types.add(DiscountType.LOYAL_CUSTOMER)

    # Festival (stackable with one user-based)
    festival = get_active_festival_discount()
    if festival:
        applied.append(festival)

    # Subscription (stackable)
    sub = get_subscription_discount(user_id, order_total)
    if sub:
        applied.append(sub)

    # Vendor: per-product; aggregate into one line or list
    for item in cart_items:
        pid = item.get("product_id")
        price = item.get("price", 0) * item.get("quantity", 1)
        brand = item.get("brand")
        vd = get_vendor_discount_for_product(pid or "", price, brand)
        if vd:
            applied.append(vd)

    return applied


def get_subscription_tiers() -> List[dict]:
    return [t.model_dump() for t in SUBSCRIPTION_TIERS]


def get_festivals() -> List[dict]:
    _ensure_demo_data()
    return list(_festivals)
