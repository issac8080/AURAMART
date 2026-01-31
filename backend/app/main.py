"""
AuraShop Backend - AI Shopping Assistant API
REST + event tracking + recommendations + chat
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import CORS_ORIGINS, RAZORPAY_KEY_ID
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
    set_cart_quantity,
    remove_from_cart,
    clear_cart,
    get_session_context,
)
from app.ai_service import get_recommendations, chat as ai_chat, chat_stream as ai_chat_stream
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
from app.payment_service import (
    create_payment_order,
    verify_payment_signature,
    get_payment_details,
    RAZORPAY_AVAILABLE,
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

# Track payment_ids already credited (Razorpay verify) to avoid double-credit
_verified_payment_ids = set()

# Pending checkout: razorpay_order_id -> CreateOrderRequest (for confirm after payment)
_pending_checkout_orders: dict = {}


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
    exclude = exclude_product_ids.split(",") if exclude_product_ids else None
    try:
        recs = get_recommendations(
            session_id=session_id or "",
            limit=limit,
            max_price=max_price,
            category=category,
            exclude_product_ids=exclude,
        )
        return {"recommendations": recs}
    except Exception:
        return {"recommendations": []}


@app.post("/chat")
def chat_endpoint(body: ChatRequest):
    result = ai_chat(
        session_id=body.session_id,
        message=body.message,
        history=body.history,
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
    """Generate OTP for email and print it in the backend terminal. No password. Only @gmail.com allowed."""
    email = (body.email or "").strip().lower()
    if not email.endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Invalid email. Only Gmail addresses (@gmail.com) are allowed.")
    ok = auth_send_otp(body.email)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid email")
    return {"message": "OTP sent. Check the backend terminal for your OTP.", "success": True}


@app.post("/auth/verify-otp")
def auth_verify_otp_endpoint(body: VerifyOtpRequest):
    """Verify OTP and return success. Frontend can then log the user in (email only)."""
    email = (body.email or "").strip().lower()
    otp = str(body.otp) if body.otp is not None else ""
    ok = auth_verify_otp(email, otp)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    name = email.split("@")[0].replace(".", " ").replace("_", " ")
    if name:
        name = name[0].upper() + name[1:]
    return {"success": True, "email": email, "name": name or "User"}


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
    items = get_cart(session_id)
    products = []
    for item in items:
        p = get_product(item["product_id"])
        if p:
            products.append({**p.model_dump(), "quantity": item["quantity"]})
    return {"cart": products}


@app.patch("/session/{session_id}/cart/item")
def update_cart_item(session_id: str, body: dict):
    """Set quantity for a product. quantity <= 0 removes the item."""
    product_id = body.get("product_id")
    quantity = body.get("quantity")
    if not product_id:
        raise HTTPException(status_code=400, detail="product_id required")
    try:
        q = int(quantity) if quantity is not None else 1
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="quantity must be an integer")
    set_cart_quantity(session_id, product_id, q)
    items = get_cart(session_id)
    products = []
    for i in items:
        p = get_product(i["product_id"])
        if p:
            products.append({**p.model_dump(), "quantity": i["quantity"]})
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
    """Create a new order (home delivery or store pickup). Used when Razorpay is not configured."""
    order = create_order(
        user_id=body.user_id,
        items=body.items,
        delivery_method=body.delivery_method,
        delivery_address=body.delivery_address,
        store_location=body.store_location,
    )
    return order.model_dump()


def _require_logged_in_checkout(x_logged_in: str | None = Header(None, alias="X-Logged-In")):
    if x_logged_in != "true":
        raise HTTPException(status_code=401, detail="Login required")


class CheckoutCreatePaymentRequest(CreateOrderRequest):
    """CreateOrderRequest + optional discounted total for Razorpay amount."""
    order_total: float | None = None  # If set, use for Razorpay amount (after discounts)


@app.post("/checkout/create-payment")
def checkout_create_payment(
    body: CheckoutCreatePaymentRequest,
    x_logged_in: str | None = Header(None, alias="X-Logged-In"),
):
    """Create Razorpay order for checkout total. Returns razorpay_order_id for frontend to open Razorpay."""
    _require_logged_in_checkout(x_logged_in)
    if not RAZORPAY_AVAILABLE or not RAZORPAY_KEY_ID:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    total = body.order_total if body.order_total is not None and body.order_total > 0 else sum(item.price * item.quantity for item in body.items)
    if total <= 0:
        raise HTTPException(status_code=400, detail="Invalid order total")
    import time
    receipt = f"ord{int(time.time() * 1000)}"[:40]
    try:
        order = create_payment_order(amount=total, currency="INR", receipt=receipt, notes={"session_id": body.session_id})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    razorpay_order_id = order["id"]
    _pending_checkout_orders[razorpay_order_id] = body.model_dump()
    return {
        "razorpay_order_id": razorpay_order_id,
        "amount": int(order["amount"]),
        "currency": order["currency"],
        "key_id": RAZORPAY_KEY_ID,
    }


@app.post("/checkout/confirm-payment")
def checkout_confirm_payment(
    body: dict,
    x_logged_in: str | None = Header(None, alias="X-Logged-In"),
):
    """Verify Razorpay payment and create order. Call after successful Razorpay checkout."""
    _require_logged_in_checkout(x_logged_in)
    razorpay_order_id = body.get("razorpay_order_id")
    payment_id = body.get("payment_id")
    signature = body.get("signature")
    if not razorpay_order_id or not payment_id or not signature:
        raise HTTPException(status_code=400, detail="razorpay_order_id, payment_id, signature required")
    if not verify_payment_signature(razorpay_order_id, payment_id, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    pending = _pending_checkout_orders.pop(razorpay_order_id, None)
    if not pending:
        raise HTTPException(status_code=400, detail="Order session expired. Please checkout again.")
    from app.models import CreateOrderRequest
    req = CreateOrderRequest(**pending)
    order = create_order(
        user_id=req.user_id,
        items=req.items,
        delivery_method=req.delivery_method,
        delivery_address=req.delivery_address,
        store_location=req.store_location,
    )
    return {"order_id": order.id}


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


def _require_logged_in(x_logged_in: str | None = Header(None, alias="X-Logged-In")):
    """Require X-Logged-In: true header for payment/wallet endpoints."""
    if x_logged_in != "true":
        raise HTTPException(status_code=401, detail="Login required")


@app.get("/wallet/razorpay-key")
def get_razorpay_key(x_logged_in: str | None = Header(None, alias="X-Logged-In")):
    """Return Razorpay key ID for frontend checkout (public key). Requires login."""
    _require_logged_in(x_logged_in)
    if not RAZORPAY_KEY_ID:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    return {"key_id": RAZORPAY_KEY_ID}


@app.post("/wallet/create-order")
def create_wallet_order(
    user_id: str = Query(...),
    amount: float = Query(...),
    x_logged_in: str | None = Header(None, alias="X-Logged-In"),
):
    """Create a Razorpay order for wallet top-up. Frontend uses order_id to open checkout. Requires login."""
    _require_logged_in(x_logged_in)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if amount > 100000:
        raise HTTPException(status_code=400, detail="Maximum top-up amount is ₹100,000")
    if not RAZORPAY_AVAILABLE or not RAZORPAY_KEY_ID:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env")
    try:
        import time
        # Razorpay receipt max 40 chars; keep unique and short
        receipt = f"w{int(time.time() * 1000)}"[:40]
        order = create_payment_order(
            amount=amount,
            currency="INR",
            receipt=receipt,
            notes={"user_id": user_id, "amount_inr": str(amount)},
        )
        return {
            "order_id": order["id"],
            "amount": int(order["amount"]),
            "currency": order["currency"],
            "key_id": RAZORPAY_KEY_ID,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/wallet/verify-payment")
def verify_wallet_payment(
    user_id: str = Query(...),
    order_id: str = Query(...),
    payment_id: str = Query(...),
    signature: str = Query(...),
):
    """Verify Razorpay payment and credit wallet. Call after successful checkout."""
    if not verify_payment_signature(order_id, payment_id, signature):
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    if payment_id in _verified_payment_ids:
        return {"success": True, "message": "Payment already credited"}
    try:
        payment = get_payment_details(payment_id)
        amount_paise = payment.get("amount") or 0
        amount_inr = round(amount_paise / 100, 2)
        if amount_inr <= 0:
            raise HTTPException(status_code=400, detail="Invalid payment amount")
        transaction = add_money_to_wallet(user_id, amount_inr, "razorpay")
        _verified_payment_ids.add(payment_id)
        return {
            "success": True,
            "transaction": transaction.model_dump(),
            "message": f"Successfully added ₹{amount_inr} to wallet",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/wallet/add-money")
def add_money_endpoint(
    user_id: str = Query(...),
    amount: float = Query(...),
    payment_method: str = Query("razorpay"),
    x_logged_in: str | None = Header(None, alias="X-Logged-In"),
):
    """Add money to wallet (top-up). Used when Razorpay is not configured (instant demo) or as fallback. Requires login."""
    _require_logged_in(x_logged_in)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    if amount > 100000:
        raise HTTPException(status_code=400, detail="Maximum top-up amount is ₹100,000")
    transaction = add_money_to_wallet(user_id, amount, payment_method)
    return {
        "success": True,
        "transaction": transaction.model_dump(),
        "message": f"Successfully added {amount} to wallet",
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


@app.get("/discounts/demo-users")
def get_demo_users_endpoint():
    """Get demo user accounts for discount feature demonstration (e.g. Sujal = all discounts)."""
    import json
    from pathlib import Path
    path = Path(__file__).resolve().parent.parent / "data" / "demo_users.json"
    if not path.exists():
        return {"users": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": []}
