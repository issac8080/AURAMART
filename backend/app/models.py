from pydantic import BaseModel
from typing import Optional, List
from enum import Enum
from datetime import datetime


class EventType(str, Enum):
    PAGE_VIEW = "page_view"
    PRODUCT_CLICK = "product_click"
    SEARCH = "search"
    CART_ADD = "cart_add"
    CART_REMOVE = "cart_remove"
    TIME_SPENT = "time_spent"
    BUDGET_SIGNAL = "budget_signal"
    CATEGORY_VIEW = "category_view"


class EventPayload(BaseModel):
    event_type: EventType
    session_id: str
    user_id: Optional[str] = None
    product_id: Optional[str] = None
    category: Optional[str] = None
    query: Optional[str] = None
    amount: Optional[float] = None
    duration_seconds: Optional[float] = None
    metadata: Optional[dict] = None


class Product(BaseModel):
    id: str
    name: str
    description: str
    price: float
    currency: str = "INR"
    category: str
    subcategory: Optional[str] = None
    brand: Optional[str] = None
    rating: float
    review_count: int
    colors: List[str] = []
    sizes: List[str] = []
    image_url: Optional[str] = None
    tags: List[str] = []
    in_stock: bool = True
    stock_count: Optional[int] = None


class RecommendationItem(BaseModel):
    product_id: str
    reason: str
    confidence: float


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    product_ids: Optional[List[str]] = None  # For inline product cards


class ChatRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    message: str
    history: Optional[List[dict]] = None


class DeliveryMethod(str, Enum):
    HOME_DELIVERY = "home_delivery"
    STORE_PICKUP = "store_pickup"


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    READY_FOR_PICKUP = "ready_for_pickup"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    PICKED_UP = "picked_up"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    product_id: str
    quantity: int = 1
    price: float


class CreateOrderRequest(BaseModel):
    session_id: str
    user_id: str
    items: List[OrderItem]
    delivery_method: DeliveryMethod
    delivery_address: Optional[str] = None
    store_location: Optional[str] = None


class Order(BaseModel):
    id: str
    user_id: str
    items: List[OrderItem]
    total: float
    delivery_method: DeliveryMethod
    status: OrderStatus
    delivery_address: Optional[str] = None
    store_location: Optional[str] = None
    qr_code: Optional[str] = None  # For store pickup
    created_at: str
    updated_at: str


class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    addresses: List[str] = []
    preferred_stores: List[str] = []
    created_at: str


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    addresses: Optional[List[str]] = None
    preferred_stores: Optional[List[str]] = None


class WalletTransaction(BaseModel):
    id: str
    user_id: str
    amount: float
    type: str  # "credit" or "debit"
    source: str  # "aurapoints", "refund", "purchase"
    order_id: Optional[str] = None
    description: str
    status: str = "active"  # "pending", "active", "expired"
    expires_at: Optional[str] = None  # For aurapoints with 1 month validity
    created_at: str
    is_expired: bool = False


class Wallet(BaseModel):
    user_id: str
    balance: float = 0.0
    total_earned: float = 0.0
    total_spent: float = 0.0
    transactions: List[WalletTransaction] = []
    created_at: str


class ApplyWalletRequest(BaseModel):
    order_id: str
    amount: float


class AddMoneyRequest(BaseModel):
    user_id: str
    amount: float
    payment_method: str = "razorpay"


class SpinRequest(BaseModel):
    session_id: str


class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    otp: str
