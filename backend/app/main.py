"""
AuraShop Backend - AI Shopping Assistant API
REST + event tracking + recommendations + chat
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.models import (
    EventPayload,
    ChatRequest,
    CreateOrderRequest,
    UpdateProfileRequest,
    OrderStatus,
)
from app.data_store import (
    load_products,
    get_product,
    get_products,
    get_categories,
    add_event,
    get_events,
    get_cart,
    add_to_cart,
    remove_from_cart,
    get_session_context,
)
from app.ai_service import get_recommendations, chat as ai_chat
from app.order_service import (
    create_order,
    get_order,
    get_user_orders,
    update_order_status,
    verify_pickup_qr,
    complete_pickup,
    get_user_profile,
    create_or_update_profile,
    get_available_stores,
)
from app.wallet_service import (
    get_wallet,
    get_wallet_summary,
    add_cashback,
    deduct_from_wallet,
    get_recent_transactions,
    calculate_cashback,
    get_cashback_rate,
)
from app.discountBackend import (
    get_applicable_discounts,
    get_new_user_discount,
    get_price_drop_notifications,
    record_product_view,
    record_price,
    get_subscription_tiers,
    get_festivals,
    set_user_subscription,
    get_subscription_discount,
    simulate_price_drop,
    AppliedDiscount,
    PriceDropNotification,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_products()
    yield


app = FastAPI(
    title="AuraShop API",
    description="AI-driven personalized shopping assistant",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/categories")
def list_categories():
    """Return all product categories for filtering."""
    return {"categories": get_categories()}


@app.get("/products")
def list_products(
    category: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    min_rating: float | None = Query(None),
    color: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    colors = [color] if color else None
    products = get_products(
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        colors=colors,
        limit=limit,
    )
    return {"products": [p.model_dump() for p in products]}


@app.get("/products/{product_id}")
def product_detail(product_id: str):
    p = get_product(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    return p.model_dump()


@app.post("/events")
def track_event(payload: EventPayload):
    add_event(payload)
    # Optional: update cart for cart_add/cart_remove
    if payload.event_type.value == "cart_add" and payload.product_id:
        add_to_cart(payload.session_id, payload.product_id)
    elif payload.event_type.value == "cart_remove" and payload.product_id:
        remove_from_cart(payload.session_id, payload.product_id)
    return {"ok": True}


@app.get("/recommendations")
def recommendations(
    session_id: str = Query(..., description="Session ID"),
    limit: int = Query(5, le=20),
    max_price: float | None = Query(None),
    category: str | None = Query(None),
    exclude_product_ids: str | None = Query(None),  # comma-separated
):
    exclude = exclude_product_ids.split(",") if exclude_product_ids else None
    recs = get_recommendations(
        session_id=session_id,
        limit=limit,
        max_price=max_price,
        category=category,
        exclude_product_ids=exclude,
    )
    return {"recommendations": recs}


@app.post("/chat")
def chat_endpoint(body: ChatRequest):
    result = ai_chat(
        session_id=body.session_id,
        message=body.message,
        history=body.history,
    )
    return result


@app.get("/session/{session_id}/context")
def session_context(session_id: str):
    """Debug: get current session context (events summary, cart, profile)."""
    ctx = get_session_context(session_id)
    # Don't return full event payloads, just summary
    return {
        "cart_ids": ctx["cart_ids"],
        "viewed_product_ids": ctx["viewed_product_ids"],
        "search_queries": ctx["search_queries"],
        "budget_signals": ctx["budget_signals"],
        "categories_viewed": ctx["categories_viewed"],
        "profile": ctx["profile"],
    }


@app.get("/session/{session_id}/cart")
def get_session_cart(session_id: str):
    cart_ids = get_cart(session_id)
    products = []
    for pid in cart_ids:
        p = get_product(pid)
        if p:
            products.append(p.model_dump())
    return {"cart": products}


# Orders and Store Pickup


@app.get("/stores")
def list_stores():
    """Get available stores for pickup."""
    return {"stores": get_available_stores()}


@app.post("/orders")
def create_new_order(body: CreateOrderRequest):
    """Create a new order (home delivery or store pickup)."""
    order = create_order(
        user_id=body.user_id,
        items=body.items,
        delivery_method=body.delivery_method,
        delivery_address=body.delivery_address,
        store_location=body.store_location,
    )
    return order.model_dump()


@app.get("/orders/{order_id}")
def get_order_detail(order_id: str):
    """Get order details."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.model_dump()


@app.get("/users/{user_id}/orders")
def get_user_order_list(user_id: str):
    """Get all orders for a user."""
    orders = get_user_orders(user_id)
    return {"orders": [o.model_dump() for o in orders]}


@app.post("/orders/{order_id}/status")
def update_order_status_endpoint(order_id: str, status: OrderStatus):
    """Update order status (admin/store use)."""
    order = update_order_status(order_id, status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.model_dump()


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str):
    """Cancel an order."""
    order = update_order_status(order_id, OrderStatus.CANCELLED)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.model_dump()


@app.post("/pickup/verify")
def verify_pickup_qr_code(qr_code: str = Query(...)):
    """Verify QR code for store pickup."""
    order = verify_pickup_qr(qr_code)
    if not order:
        raise HTTPException(status_code=404, detail="Invalid QR code or order not found")
    return order.model_dump()


@app.post("/pickup/complete/{order_id}")
def complete_store_pickup(order_id: str):
    """Mark order as picked up."""
    order = complete_pickup(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.model_dump()


# User Profile


@app.get("/users/{user_id}/profile")
def get_profile(user_id: str):
    """Get user profile."""
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile.model_dump()


@app.post("/users/{user_id}/profile")
def update_profile(user_id: str, body: UpdateProfileRequest):
    """Create or update user profile."""
    profile = create_or_update_profile(
        user_id=user_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        addresses=body.addresses,
        preferred_stores=body.preferred_stores,
    )
    return profile.model_dump()


# Aura Wallet


@app.get("/users/{user_id}/wallet")
def get_user_wallet(user_id: str):
    """Get user's Aura Wallet details."""
    wallet = get_wallet(user_id)
    summary = get_wallet_summary(user_id)
    return {
        "wallet": wallet.model_dump(),
        "summary": summary,
    }


@app.get("/users/{user_id}/wallet/transactions")
def get_wallet_transactions(user_id: str, limit: int = 20):
    """Get wallet transaction history."""
    transactions = get_recent_transactions(user_id, limit)
    return {"transactions": [t.model_dump() for t in transactions]}


@app.post("/orders/{order_id}/cashback")
def apply_order_cashback(order_id: str):
    """Apply AuraPoints to user's wallet after order completion."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status not in ["delivered", "picked_up"]:
        raise HTTPException(status_code=400, detail="Order not completed yet")
    
    # Add AuraPoints
    transaction = add_cashback(order.user_id, order_id, order.total)
    points_rate = get_cashback_rate(order.total)
    
    return {
        "transaction": transaction.model_dump(),
        "points_amount": transaction.amount,
        "points_rate": f"{points_rate:.0f}%",
        "expires_at": transaction.expires_at,
    }


@app.post("/orders/apply-wallet")
def apply_wallet_to_order(user_id: str, amount: float, order_id: str):
    """Apply wallet balance to order."""
    transaction = deduct_from_wallet(user_id, amount, order_id)
    if not transaction:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
    
    return {
        "transaction": transaction.model_dump(),
        "remaining_balance": get_wallet(user_id).balance,
    }


@app.get("/wallet/preview-cashback")
def preview_cashback(order_total: float):
    """Preview AuraPoints for an order total."""
    points = calculate_cashback(order_total)
    rate = get_cashback_rate(order_total)
    return {
        "order_total": order_total,
        "points_amount": points,
        "points_rate": f"{rate:.0f}%",
        "validity_days": 30,
    }


# ---------- Discount API (discountBackend) ----------


@app.get("/discounts/applicable")
def get_discounts_applicable(
    user_id: str = Query(...),
    session_id: str = Query(...),
    order_total: float = Query(...),
    cart_items: str = Query("[]", description="JSON array of {product_id, price, quantity, brand}"),
):
    """Get all applicable discounts for a user and cart."""
    import json
    try:
        items = json.loads(cart_items)
    except Exception:
        items = []
    discounts = get_applicable_discounts(user_id, session_id, items, order_total)
    return {"discounts": [d.model_dump() for d in discounts]}


@app.get("/discounts/price-drop-notifications")
def get_price_drop_notifications_endpoint(
    session_id: str = Query(...),
    user_id: str | None = Query(None),
):
    """Get price drop notifications for products the user viewed/searched."""
    notifications = get_price_drop_notifications(session_id, user_id)
    return {"notifications": [n.model_dump() for n in notifications]}


@app.post("/discounts/record-view")
def record_product_view_endpoint(
    session_id: str = Query(...),
    product_id: str = Query(...),
    user_id: str | None = Query(None),
):
    """Record that user viewed a product (for price drop alerts)."""
    record_product_view(session_id, user_id, product_id)
    return {"ok": True}


@app.get("/discounts/subscription-tiers")
def get_subscription_tiers_endpoint():
    """Get available subscription tiers."""
    return {"tiers": get_subscription_tiers()}


@app.get("/discounts/festivals")
def get_festivals_endpoint():
    """Get festival discount campaigns."""
    return {"festivals": get_festivals()}


@app.post("/discounts/subscription")
def set_subscription_endpoint(user_id: str = Query(...), tier_id: str | None = Query(None)):
    """Set or clear user subscription tier."""
    set_user_subscription(user_id, tier_id)
    return {"ok": True, "tier_id": tier_id}


@app.post("/discounts/simulate-price-drop")
def simulate_price_drop_endpoint(product_id: str = Query(...), new_price: float = Query(...)):
    """(Demo) Simulate a price drop for a product to trigger notifications."""
    ok = simulate_price_drop(product_id, new_price)
    if not ok:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True, "product_id": product_id, "new_price": new_price}
