"""
AuraShop Backend - AI Shopping Assistant API
REST + event tracking + recommendations + chat
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import CORS_ORIGINS
from app.models import (
    EventPayload,
    ChatRequest,
    CreateOrderRequest,
    UpdateProfileRequest,
    OrderStatus,
    SpinRequest,
    SendOtpRequest,
    VerifyOtpRequest,
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
    clear_cart,
    get_session_context,
)
from app.recommend_bridge import get_recommendations, chat as ai_chat
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
from app.auth_otp import send_otp as auth_send_otp, verify_otp as auth_verify_otp
from app.coupon_game import (
    play as coupon_game_play,
    play_jackpot as coupon_game_jackpot,
    play_scratch as coupon_game_scratch,
    validate_coupon as coupon_validate,
)
from app.wallet_service import (
    get_wallet,
    add_cashback,
    add_pending_points,
    activate_pending_points,
    deduct_from_wallet,
    add_refund,
    add_money_to_wallet,
    get_wallet_summary,
    get_recent_transactions,
    calculate_cashback,
    get_cashback_rate,
    spin_wheel_result,
    is_spin_used,
    add_spin_reward,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        load_products()
    except Exception:
        pass
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
    try:
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
    except Exception:
        return {"products": []}


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
    exclude = [x.strip() for x in exclude_product_ids.split(",")] if exclude_product_ids else None
    recs = get_recommendations(
        session_id=session_id,
        limit=limit,
        max_price=max_price,
        category=category,
        exclude_product_ids=exclude,
    )
    return {"recommendations": recs}


@app.get("/recommendations/engine")
def recommendations_engine(
    user_id: str = Query(..., description="User ID (or session ID for guest)"),
    type: str = Query("category", description="category | search_no_buy | already_bought | out_of_stock_notify | festival | habits"),
    limit: int = Query(10, le=50),
):
    """Recommend module engine: user-based recs by type (category, habits, festival, etc.)."""
    from recommend.recommendation_engine import get_recommendations as engine_get_recommendations
    recs = engine_get_recommendations(user_id=user_id, rec_type=type.strip().lower(), limit=limit)
    return {"recommendations": recs}


@app.post("/chat")
def chat_endpoint(body: ChatRequest):
    result = ai_chat(
        session_id=body.session_id,
        message=body.message,
        history=body.history,
        user_id=body.user_id,
    )
    return result


def _sse_stream(session_id: str, message: str, history: list):
    import json
    for chunk in ai_chat_stream(session_id=session_id, message=message, history=history):
        yield f"data: {json.dumps(chunk)}\n\n"


@app.post("/chat/stream")
def chat_stream_endpoint(body: ChatRequest):
    return StreamingResponse(
        _sse_stream(body.session_id, body.message, body.history or []),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post("/auth/send-otp")
def auth_send_otp_endpoint(body: SendOtpRequest):
    """Generate OTP for email and print it in the backend terminal. No password."""
    ok = auth_send_otp(body.email)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid email")
    return {"message": "OTP sent. Check the backend terminal for your OTP.", "success": True}


@app.post("/auth/verify-otp")
def auth_verify_otp_endpoint(body: VerifyOtpRequest):
    """Verify OTP and return success. Frontend can then log the user in (email only)."""
    ok = auth_verify_otp(body.email, body.otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    name = body.email.split("@")[0].replace(".", " ").replace("_", " ")
    if name:
        name = name[0].upper() + name[1:]
    return {"success": True, "email": body.email.strip().lower(), "name": name or "User"}


@app.post("/home/coupon-game")
def home_coupon_game(body: SpinRequest):
    """Play the home page spin wheel: win ₹1000 off on orders above ₹50k. One play per session."""
    return coupon_game_play(body.session_id)


@app.post("/home/jackpot")
def home_jackpot(body: SpinRequest):
    """Play Jackpot: win ₹2000 off on orders above ₹50k. One play per session."""
    return coupon_game_jackpot(body.session_id)


@app.post("/home/scratch")
def home_scratch(body: SpinRequest):
    """Play Lucky Scratch: win ₹500 off on orders above ₹50k. One play per session."""
    return coupon_game_scratch(body.session_id)


@app.get("/coupons/validate")
def validate_coupon_endpoint(code: str = Query(...), order_total: float = Query(...)):
    """Validate a coupon code for an order total. Returns discount amount or 0."""
    discount = coupon_validate(code, order_total)
    return {"valid": discount is not None, "discount": discount or 0}


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


@app.post("/session/{session_id}/cart/clear")
def clear_cart_endpoint(session_id: str):
    """Clear all items from cart."""
    clear_cart(session_id)
    return {"message": "Cart cleared", "success": True}


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
    """Get order details with product names for each item."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    from app.data_store import get_product
    items_enriched = []
    for item in order.items:
        product = get_product(item.product_id)
        items_enriched.append({
            "product_id": item.product_id,
            "product_name": product.name if product else item.product_id,
            "quantity": item.quantity,
            "price": item.price,
            "image_url": product.image_url if product else None,
        })
    return {**order.model_dump(), "items": items_enriched}


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
    """Cancel an order and revoke any spin/cashback points for that order."""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    from app.wallet_service import revoke_order_rewards
    revoke_order_rewards(order.user_id, order_id)
    order = update_order_status(order_id, OrderStatus.CANCELLED)
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


@app.post("/orders/{order_id}/spin")
def spin_wheel_endpoint(order_id: str, body: SpinRequest):
    """
    Spin the wheel / scratch after order. One spin per order.
    Returns points_won (0, 1, 2, 3, or 10) and message. Credits wallet if points > 0.
    """
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != body.session_id:
        raise HTTPException(status_code=403, detail="Not your order")
    if is_spin_used(order_id):
        return {"points_won": 0, "message": "Already used", "already_used": True}
    points_won = spin_wheel_result()
    add_spin_reward(body.session_id, order_id, points_won)
    if points_won == 0:
        return {"points_won": 0, "message": "Better luck next time!", "already_used": False}
    return {
        "points_won": points_won,
        "message": f"You won {points_won} AuraPoints! Added to your wallet.",
        "already_used": False,
    }


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


@app.post("/wallet/add-money")
def add_money_endpoint(user_id: str = Query(...), amount: float = Query(...), payment_method: str = Query("razorpay")):
    """Add money to wallet (top-up). Payment gateway integration placeholder."""
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if amount > 100000:
        raise HTTPException(status_code=400, detail="Maximum top-up amount is ₹100,000")
    
    # In production, integrate with Razorpay here
    # For now, simulate successful payment
    transaction = add_money_to_wallet(user_id, amount, payment_method)
    return {
        "success": True,
        "transaction": transaction.model_dump(),
        "message": f"Successfully added {amount} to wallet",
    }
