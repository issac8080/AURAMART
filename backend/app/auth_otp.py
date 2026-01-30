"""
Email + OTP auth. OTP is printed in the terminal (no email sending).
One OTP per email, 5 min expiry.
"""
import random
from datetime import datetime, timedelta
from typing import Dict

_otp_store: Dict[str, dict] = {}
OTP_EXPIRY_MINUTES = 5
OTP_LENGTH = 6


def _generate_otp() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(OTP_LENGTH))


def send_otp(email: str) -> bool:
    """Generate OTP, store with expiry, print in terminal. Returns True."""
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False
    otp = _generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    _otp_store[email] = {"otp": otp, "expires_at": expires_at}
    print("\n" + "=" * 50)
    print(f"  AuraShop OTP for {email}")
    print(f"  OTP: {otp}")
    print(f"  Valid for {OTP_EXPIRY_MINUTES} minutes. Enter this in the app.")
    print("=" * 50 + "\n")
    return True


def verify_otp(email: str, otp: str) -> bool:
    """Verify OTP for email. Clear on success. Returns True if valid."""
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    if not email or not otp:
        return False
    entry = _otp_store.get(email)
    if not entry:
        return False
    if datetime.utcnow() > entry["expires_at"]:
        del _otp_store[email]
        return False
    if entry["otp"] != otp:
        return False
    del _otp_store[email]
    return True
