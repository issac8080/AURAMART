"""
Aura Wallet Service - AuraPoints rewards system.
Customers earn 5-7% AuraPoints on purchases, valid for 1 month.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app.models import Wallet, WalletTransaction

# In-memory wallet storage
_wallets: Dict[str, Wallet] = {}

# AuraPoints percentage (5-7% based on order value)
AURAPOINTS_RATE_LOW = 0.05  # 5% for orders under ₹1000
AURAPOINTS_RATE_HIGH = 0.07  # 7% for orders ≥ ₹1000
AURAPOINTS_THRESHOLD = 1000  # Threshold for higher points
AURAPOINTS_VALIDITY_DAYS = 30  # 1 month validity


def get_wallet(user_id: str) -> Wallet:
    """Get or create wallet for user."""
    if user_id not in _wallets:
        _wallets[user_id] = Wallet(
            user_id=user_id,
            balance=0.0,
            total_earned=0.0,
            total_spent=0.0,
            transactions=[],
            created_at=datetime.utcnow().isoformat(),
        )
    
    # Clean expired cashback
    _clean_expired_cashback(user_id)
    return _wallets[user_id]


def _clean_expired_cashback(user_id: str):
    """Remove expired AuraPoints from wallet balance."""
    if user_id not in _wallets:
        return
    
    wallet = _wallets[user_id]
    now = datetime.utcnow()
    expired_amount = 0.0
    
    for txn in wallet.transactions:
        if (
            txn.type == "credit" 
            and txn.source == "aurapoints" 
            and txn.expires_at 
            and not txn.is_expired
        ):
            expiry = datetime.fromisoformat(txn.expires_at)
            if now > expiry:
                txn.is_expired = True
                expired_amount += txn.amount
    
    if expired_amount > 0:
        wallet.balance = max(0, wallet.balance - expired_amount)
        _wallets[user_id] = wallet


def calculate_cashback(order_total: float) -> float:
    """Calculate AuraPoints amount based on order total."""
    if order_total >= AURAPOINTS_THRESHOLD:
        return round(order_total * AURAPOINTS_RATE_HIGH, 2)
    else:
        return round(order_total * AURAPOINTS_RATE_LOW, 2)


def get_cashback_rate(order_total: float) -> float:
    """Get AuraPoints rate for display."""
    if order_total >= AURAPOINTS_THRESHOLD:
        return AURAPOINTS_RATE_HIGH * 100  # Return as percentage
    else:
        return AURAPOINTS_RATE_LOW * 100


def add_pending_points(user_id: str, order_id: str, order_total: float) -> WalletTransaction:
    """Add pending AuraPoints to wallet immediately after order placement."""
    wallet = get_wallet(user_id)
    points_amount = calculate_cashback(order_total)
    points_rate = get_cashback_rate(order_total)
    
    now = datetime.utcnow()
    expires_at = now + timedelta(days=AURAPOINTS_VALIDITY_DAYS)
    
    transaction = WalletTransaction(
        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        amount=points_amount,
        type="credit",
        source="aurapoints",
        order_id=order_id,
        description=f"{points_rate:.0f}% AuraPoints on order {order_id}",
        status="pending",  # Pending until delivery
        expires_at=expires_at.isoformat(),
        created_at=now.isoformat(),
        is_expired=False,
    )
    
    # Don't add to balance yet (pending)
    wallet.transactions.append(transaction)
    _wallets[user_id] = wallet
    
    return transaction


def activate_pending_points(order_id: str) -> Optional[WalletTransaction]:
    """Activate pending AuraPoints when order is delivered."""
    # Find the pending transaction for this order
    for user_id, wallet in _wallets.items():
        for txn in wallet.transactions:
            if txn.order_id == order_id and txn.status == "pending" and txn.source == "aurapoints":
                # Activate the points
                txn.status = "active"
                wallet.balance += txn.amount
                wallet.total_earned += txn.amount
                _wallets[user_id] = wallet
                return txn
    return None


def add_cashback(user_id: str, order_id: str, order_total: float) -> WalletTransaction:
    """Add AuraPoints to wallet after order completion (legacy method)."""
    # Check if already pending
    wallet = get_wallet(user_id)
    for txn in wallet.transactions:
        if txn.order_id == order_id and txn.source == "aurapoints":
            # Already exists, just activate it
            return activate_pending_points(order_id) or txn
    
    # Create new active transaction
    points_amount = calculate_cashback(order_total)
    points_rate = get_cashback_rate(order_total)
    
    now = datetime.utcnow()
    expires_at = now + timedelta(days=AURAPOINTS_VALIDITY_DAYS)
    
    transaction = WalletTransaction(
        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        amount=points_amount,
        type="credit",
        source="aurapoints",
        order_id=order_id,
        description=f"{points_rate:.0f}% AuraPoints on order {order_id}",
        status="active",
        expires_at=expires_at.isoformat(),
        created_at=now.isoformat(),
        is_expired=False,
    )
    
    wallet.balance += points_amount
    wallet.total_earned += points_amount
    wallet.transactions.append(transaction)
    _wallets[user_id] = wallet
    
    return transaction


def deduct_from_wallet(user_id: str, amount: float, order_id: str) -> Optional[WalletTransaction]:
    """Deduct amount from wallet for purchase."""
    wallet = get_wallet(user_id)
    
    if wallet.balance < amount:
        return None  # Insufficient balance
    
    now = datetime.utcnow()
    transaction = WalletTransaction(
        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        amount=amount,
        type="debit",
        source="purchase",
        order_id=order_id,
        description=f"Applied to order {order_id}",
        created_at=now.isoformat(),
    )
    
    wallet.balance -= amount
    wallet.total_spent += amount
    wallet.transactions.append(transaction)
    _wallets[user_id] = wallet
    
    return transaction


def add_refund(user_id: str, order_id: str, amount: float) -> WalletTransaction:
    """Add refund to wallet (no expiry)."""
    wallet = get_wallet(user_id)
    now = datetime.utcnow()
    
    transaction = WalletTransaction(
        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        amount=amount,
        type="credit",
        source="refund",
        order_id=order_id,
        description=f"Refund for order {order_id}",
        status="active",
        created_at=now.isoformat(),
    )
    
    wallet.balance += amount
    wallet.total_earned += amount
    wallet.transactions.append(transaction)
    _wallets[user_id] = wallet
    
    return transaction


def add_money_to_wallet(user_id: str, amount: float, payment_method: str = "razorpay") -> WalletTransaction:
    """Add money to wallet (top-up)."""
    wallet = get_wallet(user_id)
    now = datetime.utcnow()
    
    transaction = WalletTransaction(
        id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        amount=amount,
        type="credit",
        source="topup",
        description=f"Added money via {payment_method}",
        status="active",
        created_at=now.isoformat(),
        is_expired=False,
    )
    
    wallet.balance += amount
    wallet.total_earned += amount
    wallet.transactions.append(transaction)
    _wallets[user_id] = wallet
    
    return transaction


def get_wallet_summary(user_id: str) -> dict:
    """Get wallet summary with active, pending, and expiring AuraPoints."""
    wallet = get_wallet(user_id)
    now = datetime.utcnow()
    soon_expiry = now + timedelta(days=7)  # Expiring in next 7 days
    
    active_points = 0.0
    pending_points = 0.0
    expiring_soon = 0.0
    
    for txn in wallet.transactions:
        if (
            txn.type == "credit" 
            and txn.source == "aurapoints" 
            and not txn.is_expired 
            and txn.expires_at
        ):
            expiry = datetime.fromisoformat(txn.expires_at)
            if expiry > now:
                if txn.status == "pending":
                    pending_points += txn.amount
                elif txn.status == "active":
                    active_points += txn.amount
                    if expiry <= soon_expiry:
                        expiring_soon += txn.amount
    
    return {
        "balance": wallet.balance,
        "total_earned": wallet.total_earned,
        "total_spent": wallet.total_spent,
        "active_points": active_points,
        "pending_points": pending_points,
        "expiring_soon": expiring_soon,
        "transaction_count": len(wallet.transactions),
    }


def get_recent_transactions(user_id: str, limit: int = 10) -> List[WalletTransaction]:
    """Get recent wallet transactions."""
    wallet = get_wallet(user_id)
    return sorted(wallet.transactions, key=lambda t: t.created_at, reverse=True)[:limit]
