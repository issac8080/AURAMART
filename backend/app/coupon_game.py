"""
Home page games: Spin Wheel, Jackpot, Lucky Scratch.
All use same rule: orders above ₹50,000. One play per game per session.
"""
import random
from typing import Dict, Optional

# Session IDs that already played each game (one play per session per game)
_played_spin: set = set()
_played_jackpot: set = set()
_played_scratch: set = set()

MIN_ORDER_AMOUNT = 50_000

# Spin Wheel: ₹1000 off, 15% win
COUPON_CODE = "GAME1000"
DISCOUNT_AMOUNT = 1_000
WIN_PROBABILITY = 0.15

# Jackpot: ₹2000 off, 5% win
JACKPOT_CODE = "JACKPOT2K"
JACKPOT_DISCOUNT = 2_000
JACKPOT_WIN_PROB = 0.05

# Lucky Scratch: ₹500 off, 25% win
SCRATCH_CODE = "SCRATCH500"
SCRATCH_DISCOUNT = 500
SCRATCH_WIN_PROB = 0.25


def play(session_id: str) -> Dict:
    """
    Play the coupon game. One play per session.
    Returns { "played": bool, "won": bool, "code": str|null, "min_order": int, "discount": int, "message": str }.
    """
    if not session_id or session_id in _played_spin:
        return {
            "game": "spin",
            "played": session_id in _played_spin,
            "won": False,
            "code": None,
            "min_order": MIN_ORDER_AMOUNT,
            "discount": DISCOUNT_AMOUNT,
            "message": "You've already played. One spin per visit!",
        }
    _played_spin.add(session_id)
    won = random.random() < WIN_PROBABILITY
    if won:
        return {
            "game": "spin",
            "played": True,
            "won": True,
            "code": COUPON_CODE,
            "min_order": MIN_ORDER_AMOUNT,
            "discount": DISCOUNT_AMOUNT,
            "message": f"Congratulations! Use code **{COUPON_CODE}** for ₹{DISCOUNT_AMOUNT} off on orders above ₹{MIN_ORDER_AMOUNT:,}.",
        }
    return {
        "game": "spin",
        "played": True,
        "won": False,
        "code": None,
        "min_order": MIN_ORDER_AMOUNT,
        "discount": DISCOUNT_AMOUNT,
        "message": "Better luck next time! Try again on your next visit.",
    }


def play_jackpot(session_id: str) -> Dict:
    """Jackpot game: ₹2000 off on orders above ₹50k. 5% win. One play per session."""
    if not session_id or session_id in _played_jackpot:
        return {
            "game": "jackpot",
            "played": session_id in _played_jackpot,
            "won": False,
            "code": None,
            "min_order": MIN_ORDER_AMOUNT,
            "discount": JACKPOT_DISCOUNT,
            "message": "You've already played Jackpot. One play per visit!",
        }
    _played_jackpot.add(session_id)
    won = random.random() < JACKPOT_WIN_PROB
    if won:
        return {
            "game": "jackpot",
            "played": True,
            "won": True,
            "code": JACKPOT_CODE,
            "min_order": MIN_ORDER_AMOUNT,
            "discount": JACKPOT_DISCOUNT,
            "message": f"Jackpot! Use code **{JACKPOT_CODE}** for ₹{JACKPOT_DISCOUNT:,} off on orders above ₹{MIN_ORDER_AMOUNT:,}.",
        }
    return {
        "game": "jackpot",
        "played": True,
        "won": False,
        "code": None,
        "min_order": MIN_ORDER_AMOUNT,
        "discount": JACKPOT_DISCOUNT,
        "message": "Better luck next time! Try Jackpot again on your next visit.",
    }


def play_scratch(session_id: str) -> Dict:
    """Lucky Scratch: ₹500 off on orders above ₹50k. 25% win. One play per session."""
    if not session_id or session_id in _played_scratch:
        return {
            "game": "scratch",
            "played": session_id in _played_scratch,
            "won": False,
            "code": None,
            "min_order": MIN_ORDER_AMOUNT,
            "discount": SCRATCH_DISCOUNT,
            "message": "You've already played Lucky Scratch. One play per visit!",
        }
    _played_scratch.add(session_id)
    won = random.random() < SCRATCH_WIN_PROB
    if won:
        return {
            "game": "scratch",
            "played": True,
            "won": True,
            "code": SCRATCH_CODE,
            "min_order": MIN_ORDER_AMOUNT,
            "discount": SCRATCH_DISCOUNT,
            "message": f"You won! Use code **{SCRATCH_CODE}** for ₹{SCRATCH_DISCOUNT} off on orders above ₹{MIN_ORDER_AMOUNT:,}.",
        }
    return {
        "game": "scratch",
        "played": True,
        "won": False,
        "code": None,
        "min_order": MIN_ORDER_AMOUNT,
        "discount": SCRATCH_DISCOUNT,
        "message": "Better luck next time! Try again on your next visit.",
    }


def validate_coupon(code: str, order_total: float) -> Optional[float]:
    """Validate coupon and return discount amount if applicable, else None. Supports GAME1000, JACKPOT2K, SCRATCH500."""
    if order_total < MIN_ORDER_AMOUNT:
        return None
    c = (code or "").strip().upper()
    if c == COUPON_CODE:
        return float(DISCOUNT_AMOUNT)
    if c == JACKPOT_CODE:
        return float(JACKPOT_DISCOUNT)
    if c == SCRATCH_CODE:
        return float(SCRATCH_DISCOUNT)
    return None
