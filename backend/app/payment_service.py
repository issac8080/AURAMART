"""
Razorpay payment gateway integration service.
Handles payment order creation and verification.
"""
try:
    import razorpay
    RAZORPAY_AVAILABLE = True
except ImportError:
    RAZORPAY_AVAILABLE = False
    razorpay = None

from app.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

# Initialize Razorpay client
client = None
if RAZORPAY_AVAILABLE and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception as e:
        print(f"Warning: Failed to initialize Razorpay client: {e}")
        client = None


def create_payment_order(amount: float, currency: str = "INR", receipt: str = None, notes: dict = None):
    """
    Create a Razorpay payment order.
    
    Args:
        amount: Amount in rupees (will be converted to paise)
        currency: Currency code (default: INR)
        receipt: Receipt ID for the order
        notes: Additional notes/metadata
    
    Returns:
        dict: Razorpay order response with order_id and other details
    """
    if not RAZORPAY_AVAILABLE:
        raise ValueError("Razorpay package not installed. Install it with: pip install razorpay")
    
    if not RAZORPAY_KEY_ID:
        raise ValueError("RAZORPAY_KEY_ID not configured. Please set it in .env file")
    
    if not RAZORPAY_KEY_SECRET:
        raise ValueError("RAZORPAY_KEY_SECRET not configured. Please set it in .env file")
    
    # Validate key format (Razorpay keys typically start with rzp_test_ or rzp_live_)
    # Trim whitespace to handle .env file formatting issues
    key_id_trimmed = RAZORPAY_KEY_ID.strip()
    if not key_id_trimmed.startswith(("rzp_test_", "rzp_live_")):
        raise ValueError(f"Invalid RAZORPAY_KEY_ID format. Keys should start with 'rzp_test_' or 'rzp_live_'. Current value: '{RAZORPAY_KEY_ID}'. Get valid keys from https://dashboard.razorpay.com/app/keys")
    
    if not client:
        raise ValueError("Razorpay client initialization failed. Please check your RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env file. Get valid keys from https://dashboard.razorpay.com/app/keys")
    
    # Convert rupees to paise (Razorpay expects amount in smallest currency unit)
    amount_paise = int(amount * 100)
    
    order_data = {
        "amount": amount_paise,
        "currency": currency,
        "payment_capture": 1,  # Auto-capture payment
    }
    
    if receipt:
        order_data["receipt"] = receipt
    
    if notes:
        order_data["notes"] = notes
    
    try:
        order = client.order.create(data=order_data)
        return order
    except Exception as e:
        # Check if it's a Razorpay-specific error
        error_str = str(e)
        if hasattr(razorpay, 'errors'):
            if isinstance(e, razorpay.errors.BadRequestError):
                if "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
                    raise Exception(f"Razorpay authentication failed. Please verify your RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env file. Get valid keys from https://dashboard.razorpay.com/app/keys")
                raise Exception(f"Razorpay API error: {error_str}. Check your API keys and order data.")
            elif isinstance(e, razorpay.errors.ServerError):
                raise Exception(f"Razorpay server error: {error_str}. Please try again later.")
            elif isinstance(e, razorpay.errors.GatewayError):
                raise Exception(f"Razorpay gateway error: {error_str}. Please check your payment gateway settings.")
        # Check for authentication errors even if not a specific Razorpay error type
        if "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
            raise Exception(f"Razorpay authentication failed. Please verify your RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env file. Get valid keys from https://dashboard.razorpay.com/app/keys")
        raise Exception(f"Failed to create Razorpay order: {error_str}")


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    Verify Razorpay payment signature to ensure payment authenticity.
    
    Args:
        order_id: Razorpay order ID
        payment_id: Razorpay payment ID
        signature: Payment signature from Razorpay
    
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not RAZORPAY_AVAILABLE or not client:
        return False
    
    try:
        # Razorpay signature verification
        params_dict = {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
        
        client.utility.verify_payment_signature(params_dict)
        return True
    except Exception as e:
        if hasattr(razorpay, 'errors') and isinstance(e, razorpay.errors.SignatureVerificationError):
            return False
        return False


def get_payment_details(payment_id: str):
    """
    Fetch payment details from Razorpay.
    
    Args:
        payment_id: Razorpay payment ID
    
    Returns:
        dict: Payment details
    """
    if not RAZORPAY_AVAILABLE:
        raise ValueError("Razorpay package not installed. Install it with: pip install razorpay")
    
    if not client:
        raise ValueError("Razorpay credentials not configured")
    
    try:
        payment = client.payment.fetch(payment_id)
        return payment
    except Exception as e:
        raise Exception(f"Failed to fetch payment details: {str(e)}")
