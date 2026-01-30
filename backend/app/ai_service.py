"""
AI layer: OpenAI-powered recommendation engine and chat assistant.
Uses prompt engineering for structured recommendations and natural chat.
"""
import json
import hashlib
from typing import List, Optional, Dict, Any
from app.config import OPENAI_API_KEY, USE_BUILTIN_CHAT
from app.data_store import (
    load_products,
    get_product,
    get_session_context,
    get_cached_recommendations,
    cache_recommendations,
)
from app.models import Product

# Optional OpenAI client (graceful if no key)
try:
    from openai import OpenAI
    _client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
except Exception:
    _client = None

# Only log once when OpenAI key is invalid (avoid terminal spam)
_openai_invalid_logged = False


def _product_summary(p: Product) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "price": p.price,
        "category": p.category,
        "rating": p.rating,
        "colors": p.colors,
        "tags": p.tags,
    }


def _build_user_summary(context: dict) -> str:
    profile = context.get("profile", {})
    budget = profile.get("max_budget") or (context.get("budget_signals") or [None])[-1]
    categories = profile.get("preferred_categories") or context.get("categories_viewed", [])
    queries = context.get("search_queries", [])
    viewed = context.get("viewed_product_ids", [])
    cart = context.get("cart_ids", [])
    parts = []
    if budget:
        parts.append(f"Budget signal: under ₹{budget}")
    if categories:
        parts.append(f"Categories of interest: {', '.join(categories[:5])}")
    if queries:
        parts.append(f"Recent searches: {', '.join(queries[:3])}")
    if viewed:
        parts.append(f"Recently viewed product IDs: {', '.join(viewed[:8])}")
    if cart:
        parts.append(f"Cart product IDs: {', '.join(cart)}")
    return "\n".join(parts) if parts else "New user, no history yet."


def get_recommendations(
    session_id: str,
    limit: int = 5,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    exclude_product_ids: Optional[List[str]] = None,
) -> List[dict]:
    """
    Hybrid recommendation: rule-based + AI ranking.
    Returns list of { product_id, reason, confidence }.
    """
    context = get_session_context(session_id)
    context_key = hashlib.md5(
        f"{limit}_{max_price}_{category}_{exclude_product_ids}".encode()
    ).hexdigest()
    cached = get_cached_recommendations(session_id, context_key)
    if cached is not None:
        return cached

    products = load_products()
    exclude = set(exclude_product_ids or [])
    # Filter by category and price
    candidates = [
        p for p in products
        if p.id not in exclude
        and (category is None or p.category == category)
        and (max_price is None or p.price <= max_price)
    ]
    if not candidates:
        candidates = [p for p in products if p.id not in exclude][:20]

    user_summary = _build_user_summary(context)
    product_list = "\n".join(
        [f"- {p.id}: {p.name}, ₹{p.price}, {p.category}, rating {p.rating}, tags: {', '.join(p.tags)}"
         for p in candidates[:50]]
    )
    prompt = f"""You are a shopping recommendation engine. Given the user context and product list, recommend exactly {limit} products.

User context:
{user_summary}

Available products (id, name, price, category, rating, tags):
{product_list}

Respond with a JSON array only, no other text. Each item: {{ "product_id": "<id>", "reason": "<short reason in 1 line>", "confidence": <0-1 number> }}.
Order by relevance. Prefer products that match budget, category affinity, and high ratings."""

    result: List[dict] = []
    if _client and OPENAI_API_KEY:
        try:
            resp = _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            text = (resp.choices[0].message.content or "").strip()
            # Extract JSON array (handle markdown code block)
            if "```" in text:
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text)
            if not isinstance(result, list):
                result = [result]
            valid_ids = {p.id for p in candidates}
            valid = []
            for r in result:
                if isinstance(r, dict) and r.get("product_id") and r["product_id"] in valid_ids:
                    valid.append({
                        "product_id": r["product_id"],
                        "reason": r.get("reason", "Recommended for you"),
                        "confidence": float(r.get("confidence", 0.8)),
                    })
                if len(valid) >= limit:
                    break
            result = valid
        except Exception:
            pass

    # Fallback: rule-based ranking by rating and price match
    if not result:
        by_rating = sorted(candidates, key=lambda p: (-p.rating, p.price))[:limit]
        budget = (context.get("budget_signals") or [None])[-1]
        for p in by_rating:
            reason = f"High rating ({p.rating})"
            if budget and p.price <= budget:
                reason = f"Within your budget, high rating"
            result.append({
                "product_id": p.id,
                "reason": reason,
                "confidence": 0.75,
            })

    # Attach full product for frontend (product cards)
    out = []
    for r in result:
        prod = get_product(r["product_id"])
        if prod:
            out.append({
                **r,
                "product": prod.model_dump(),
            })
    cache_recommendations(session_id, context_key, out)
    return out


def chat(session_id: str, message: str, history: Optional[List[dict]] = None) -> dict:
    """
    Enhanced AI shopping assistant with FULL SYSTEM ACCESS - true agent capabilities.
    Returns { content, product_ids } for inline product cards.
    """
    from app.order_service import get_user_orders, get_user_profile
    from app.wallet_service import get_wallet_summary
    from app.data_store import get_categories
    
    context = get_session_context(session_id)
    products = load_products()
    
    # Get comprehensive user data
    cart_ids = context.get("cart_ids", [])
    cart_items = []
    cart_total = 0
    if cart_ids:
        cart_items = [get_product(pid) for pid in cart_ids]
        cart_items = [p for p in cart_items if p]
        cart_total = sum(p.price for p in cart_items)
    
    # Get orders
    orders_info = []
    try:
        orders = get_user_orders(session_id)
        for order in orders[:3]:
            orders_info.append({
                "id": order.id,
                "total": order.total,
                "status": order.status.value,
                "items_count": len(order.items)
            })
    except:
        pass
    
    # Get wallet
    wallet_info = {"balance": 0, "pending_points": 0, "total_earned": 0}
    try:
        wallet_summary = get_wallet_summary(session_id)
        wallet_info = {
            "balance": wallet_summary.get("balance", 0),
            "pending_points": wallet_summary.get("pending_points", 0),
            "total_earned": wallet_summary.get("total_earned", 0),
            "expiring_soon": wallet_summary.get("expiring_soon", 0)
        }
    except:
        pass
    
    # Get profile
    profile_name = "there"
    try:
        profile = get_user_profile(session_id)
        if profile and profile.name:
            profile_name = profile.name
    except:
        pass
    
    # Sample products across categories
    by_cat: Dict[str, List[Product]] = {}
    for p in products:
        by_cat.setdefault(p.category, []).append(p)
    sampled = []
    for cat_products in by_cat.values():
        sampled.extend(cat_products[:10])
    sampled = (sampled + products)[:100]
    product_list = "\n".join(
        [f"- {p.id}: {p.name}, ₹{p.price}, {p.category}, {p.rating}⭐"
         for p in sampled]
    )
    
    user_context = _build_user_summary(context)
    cart_summary = ""
    if cart_items:
        cart_summary = f"Cart ({len(cart_items)} items, ₹{cart_total}): " + ", ".join([f"{p.name} (₹{p.price})" for p in cart_items[:3]])
        if len(cart_items) > 3:
            cart_summary += f" +{len(cart_items)-3} more"
    
    categories = get_categories()

    system = f"""You are AuraShop's intelligent AI assistant with FULL SYSTEM ACCESS. You're a true agent!

🎯 YOUR CAPABILITIES:
1. SHOPPING: Search products, recommend, compare, suggest alternatives
2. ORDERS: Check status, track deliveries, help with cancellations  
3. WALLET: Check balance, explain AuraPoints (5% <₹1K, 7% ≥₹1K), show pending points
4. ACCOUNT: View profile, personalize recommendations

📊 CURRENT USER DATA:
Name: {profile_name}
Cart: {len(cart_items)} items, ₹{cart_total}
{cart_summary if cart_summary else "Cart is empty"}

Orders: {len(orders_info)} orders
{f"Latest: {orders_info[0]['id']} - {orders_info[0]['status']} (₹{orders_info[0]['total']})" if orders_info else "No orders yet"}

Wallet: ₹{wallet_info['balance']} available
{f"Pending: ₹{wallet_info['pending_points']} (after delivery)" if wallet_info['pending_points'] > 0 else ""}
{f"Total Earned: ₹{wallet_info['total_earned']}" if wallet_info['total_earned'] > 0 else ""}
{f"⚠️ ₹{wallet_info['expiring_soon']} expiring in 7 days!" if wallet_info.get('expiring_soon', 0) > 0 else ""}

Activity:
{user_context}

🏪 CATEGORIES: {', '.join(categories[:12])}

📦 PRODUCTS (use IDs when recommending):
{product_list}

💡 RESPONSE RULES:
- Friendly & conversational
- Use emojis sparingly (1-2 max)
- **ALWAYS mention product IDs (P00123)** for product cards
- Give 2-4 specific recommendations with prices
- Explain WHY (budget match, high-rated, trending)
- For wallet/orders, use ACTUAL user data above
- Ask clarifying questions: "Budget?", "Casual or formal?"
- Keep under 200 words
- Guide actions: "Add to cart?", "Want similar items?"

Remember: You have REAL user data. Use it for accurate, personalized help!"""

    user_block = f"""User message: {message}"""

    messages = [{"role": "system", "content": system}]
    if history:
        for h in history[-8:]:
            role = "user" if h.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": user_block})

    product_ids: List[str] = []
    content = f"Hi {profile_name}! ✨ I'm your AuraShop AI assistant. I can help you shop, check orders, manage your wallet, and more. What would you like to do?"

    # Try OpenAI first unless disabled; fallback to built-in intelligent assistant
    global _openai_invalid_logged

    if not USE_BUILTIN_CHAT and _client and OPENAI_API_KEY:
        try:
            resp = _client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )
            content = (resp.choices[0].message.content or content).strip()
            import re
            product_ids = list(dict.fromkeys(re.findall(r"P\d{3,5}", content)))
        except Exception as e:
            err_str = str(e).lower()
            is_invalid_key = "401" in err_str or "invalid_api_key" in err_str or "incorrect api key" in err_str
            if is_invalid_key and not _openai_invalid_logged:
                print("OpenAI API key invalid or expired; using built-in AI assistant. Set USE_BUILTIN_CHAT=1 in .env to hide this.")
                _openai_invalid_logged = True
            elif not is_invalid_key:
                print(f"OpenAI chat error: {e}")
            content, product_ids = _intelligent_fallback(message, profile_name, cart_items, cart_total, wallet_info, orders_info, products, by_cat, user_context)
    else:
        content, product_ids = _intelligent_fallback(message, profile_name, cart_items, cart_total, wallet_info, orders_info, products, by_cat, user_context)

    return {"content": content, "product_ids": product_ids[:6]}


def _intelligent_fallback(message: str, profile_name: str, cart_items: List, cart_total: float, wallet_info: dict, orders_info: List, products: List[Product], by_cat: Dict, user_context: str) -> tuple:
    """
    Intelligent rule-based AI agent when OpenAI is unavailable.
    Handles: search, recommendations, cart, orders, wallet, comparisons.
    """
    import re
    msg_lower = message.lower()
    product_ids = []
    
    # SEARCH/PRODUCT QUERIES - Extract budget and category
    budget_match = re.search(r'under\s+₹?(\d+)|below\s+₹?(\d+)|<\s*₹?(\d+)|budget\s+of\s+₹?(\d+)|price\s+around\s+₹?(\d+)', msg_lower)
    budget = None
    if budget_match:
        # Find the first non-None group
        for group in budget_match.groups():
            if group:
                budget = int(group)
                break
    
    # AGENT ACTIONS - EXTRACT INTENT
    is_buying = any(word in msg_lower for word in ['buy', 'purchase', 'order', 'checkout', 'pay'])
    is_searching = any(word in msg_lower for word in ['search', 'find', 'show', 'look for', 'get me'])
    is_adding = any(word in msg_lower for word in ['add to cart', 'put in cart', 'add this'])
    
    # Find matching category
    matching_category = None
    for cat in by_cat.keys():
        if cat.lower() in msg_lower:
            matching_category = cat
            break
    
    # Search keywords
    search_terms = []
    for word in ['phone', 'shirt', 'shoes', 'laptop', 'watch', 'bag', 'dress', 'jeans', 'electronics', 'fashion', 'camera', 'tv', 'headphone']:
        if word in msg_lower:
            search_terms.append(word)

    # ACTION: BUYING / CHECKOUT
    if is_buying and not is_searching:
        if cart_items:
            content = f"Hi {profile_name}! 🚀 I can help you complete your purchase right now.\n\n"
            content += f"Items in your cart: {len(cart_items)}\n"
            content += f"Total Amount: **₹{cart_total}**\n"
            content += f"Estimated AuraPoints: ₹{(cart_total * (0.07 if cart_total >= 1000 else 0.05)):.0f}\n\n"
            content += "Shall I take you to the secure checkout page to finalize your order?"
            content += "\n\n[Click here to go to Checkout](/checkout)"
            return content, [p.id for p in cart_items[:4]]
        else:
            content = f"Hi {profile_name}! Your cart is empty, so there's nothing to buy yet. 🛍️\n\nWhat are you looking for? I can find the best products for you!"
            return content, []

    # ACTION: ADDING TO CART
    if is_adding and not is_searching:
        # Try to find which product to add
        target_product = None
        for p in products:
            if p.name.lower() in msg_lower or p.id.lower() in msg_lower:
                target_product = p
                break
        
        if target_product:
            content = f"Hi {profile_name}! I've found **{target_product.name}** (₹{target_product.price}). ✨\n\n"
            content += "I'm an AI agent and I've prepared this item for your cart. You can click the 'Add to Cart' button on the product card below to confirm!"
            return content, [target_product.id]
        else:
            content = f"Hi {profile_name}! Which item would you like to add to your cart? Please mention the name or ID, or browse our trending products below!"
            return content, [p.id for p in sorted(products, key=lambda x: -x.rating)[:4]]
    
    # WALLET QUERIES
    if any(word in msg_lower for word in ['wallet', 'balance', 'money', 'aurapoints', 'points', 'rewards', 'topup', 'add money']):
        content = f"Hi {profile_name}! 💰 I'm your Aura Wallet agent. Here's your status:\n\n"
        content += f"💎 **Available Balance: ₹{wallet_info['balance']}**\n"
        if wallet_info['pending_points'] > 0:
            content += f"⏳ Pending AuraPoints: ₹{wallet_info['pending_points']} (activates after delivery)\n"
        if wallet_info['total_earned'] > 0:
            content += f"🎉 Total Rewards Earned: ₹{wallet_info['total_earned']}\n"
        
        content += f"\n**Agent Recommendation:** "
        if wallet_info['balance'] < 500:
            content += "Your balance is low. Want me to help you add money via Razorpay?"
        else:
            content += "You have a good balance! Want to use it for a purchase?"
            
        content += "\n\n[Go to Wallet Page](/wallet)"
        return content, []

    # ORDER QUERIES
    if any(word in msg_lower for word in ['order', 'delivery', 'track', 'status', 'shipped']):
        if orders_info:
            latest = orders_info[0]
            content = f"Hi {profile_name}! 📦 Your Orders:\n\n"
            content += f"Latest Order: **{latest['id']}**\n"
            content += f"Status: {latest['status'].replace('_', ' ').title()}\n"
            content += f"Total: ₹{latest['total']}\n"
            content += f"Items: {latest['items_count']}\n\n"
            if len(orders_info) > 1:
                content += f"You have {len(orders_info)} total orders. "
            content += "Need help with anything else?"
            return content, []
        else:
            content = f"Hi {profile_name}! You don't have any orders yet. 🛍️\n\nWant me to help you find something to buy? I can search products, compare options, or show you trending items!"
            return content, []
    
    # CART QUERIES
    if any(word in msg_lower for word in ['cart', 'basket', 'added']):
        if cart_items:
            content = f"Hi {profile_name}! 🛒 Your Cart ({len(cart_items)} items):\n\n"
            for i, item in enumerate(cart_items[:5], 1):
                content += f"{i}. {item.name} - ₹{item.price}\n"
                product_ids.append(item.id)
            if len(cart_items) > 5:
                content += f"\n+{len(cart_items)-5} more items\n"
            content += f"\n**Total: ₹{cart_total}**\n\n"
            if cart_total >= 1000:
                points = cart_total * 0.07
                content += f"🎉 You'll earn ₹{points:.0f} AuraPoints (7%) on this order!\n"
            else:
                points = cart_total * 0.05
                content += f"💎 You'll earn ₹{points:.0f} AuraPoints (5%) on this order!\n"
            content += "\nReady to checkout?"
            return content, product_ids[:6]
        else:
            content = f"Hi {profile_name}! Your cart is empty. 🛍️\n\nLet me help you find something! What are you looking for? (e.g., 'phones under 30000', 'casual shirts', 'trending products')"
            return content, []
    
    # SEARCH/PRODUCT QUERIES - Extract budget and category
    budget_match = re.search(r'under\s+₹?(\d+)|below\s+₹?(\d+)|<\s*₹?(\d+)', msg_lower)
    budget = None
    if budget_match:
        budget = int(budget_match.group(1) or budget_match.group(2) or budget_match.group(3))
    
    # Find matching category
    matching_category = None
    for cat in by_cat.keys():
        if cat.lower() in msg_lower:
            matching_category = cat
            break
    
    # Search keywords
    search_terms = []
    for word in ['phone', 'shirt', 'shoes', 'laptop', 'watch', 'bag', 'dress', 'jeans', 'electronics', 'fashion']:
        if word in msg_lower:
            search_terms.append(word)
    
    # TRENDING/BEST QUERIES
    if any(word in msg_lower for word in ['trending', 'popular', 'best', 'top', 'recommend', 'suggest', 'find', 'search', 'show', 'look for', 'get me']):
        # Get top-rated products
        sorted_products = sorted(products, key=lambda p: (-p.rating, -p.price))[:30]
        if budget:
            sorted_products = [p for p in sorted_products if p.price <= budget]
        if matching_category:
            sorted_products = [p for p in sorted_products if p.category == matching_category]
        
        recommendations = sorted_products[:4]
        if recommendations:
            content = f"Hi {profile_name}! ✨ I've found some great options for you"
            if budget:
                content += f" under ₹{budget}"
            if matching_category:
                content += f" in {matching_category}"
            content += ":\n\n"
            
            for i, p in enumerate(recommendations, 1):
                content += f"{i}. **{p.id}** - {p.name}\n   ₹{p.price} | {p.rating}⭐ | {p.category}\n\n"
                product_ids.append(p.id)
            
            content += "I'm your shopping agent! You can click any card to view details, add to cart, or ask me to 'checkout' when you're ready!"
            return content, product_ids
    
    # CATEGORY/SEARCH QUERIES
    if matching_category or search_terms or budget:
        results = products
        
        if matching_category:
            results = by_cat.get(matching_category, [])
        elif search_terms:
            # Search by keywords
            results = [p for p in products if any(term in p.name.lower() or term in p.category.lower() for term in search_terms)]
        
        if budget:
            results = [p for p in results if p.price <= budget]
        
        # Sort by rating
        results = sorted(results, key=lambda p: (-p.rating, p.price))[:4]
        
        if results:
            content = f"Hi {profile_name}! 🔍 Found {len(results)} great options"
            if budget:
                content += f" under ₹{budget}"
            if matching_category:
                content += f" in {matching_category}"
            content += ":\n\n"
            
            for i, p in enumerate(results, 1):
                content += f"{i}. **{p.id}** - {p.name}\n   ₹{p.price} | {p.rating}⭐\n\n"
                product_ids.append(p.id)
            
            content += "Click any product card to view details or add to cart!"
            return content, product_ids
        else:
            content = f"Hi {profile_name}! I couldn't find exact matches"
            if budget:
                content += f" under ₹{budget}"
            content += ". Try:\n• Different budget\n• Browse categories\n• Ask for 'trending products'"
            return content, []
    
    # GREETING/HELP
    if any(word in msg_lower for word in ['hi', 'hello', 'hey', 'help', 'what can you do']):
        content = f"Hi {profile_name}! ✨ I'm your AuraShop AI assistant. I can help you:\n\n"
        content += "🛍️ **Shopping:**\n"
        content += "• 'Show phones under 30000'\n"
        content += "• 'Find casual shirts'\n"
        content += "• 'Trending products'\n\n"
        content += "📦 **Orders:** 'Where is my order?'\n"
        content += "💰 **Wallet:** 'Check my balance'\n"
        content += "🛒 **Cart:** 'What's in my cart?'\n\n"
        if cart_items:
            content += f"You have {len(cart_items)} items in cart (₹{cart_total}). "
        content += "What would you like to do?"
        return content, []
    
    # DEFAULT - Show trending
    trending = sorted(products, key=lambda p: (-p.rating, -p.price))[:4]
    content = f"Hi {profile_name}! 🎯 Here are some trending products:\n\n"
    for i, p in enumerate(trending, 1):
        content += f"{i}. **{p.id}** - {p.name}\n   ₹{p.price} | {p.rating}⭐\n\n"
        product_ids.append(p.id)
    content += "Try asking: 'phones under 30000', 'check my wallet', or 'where is my order?'"
    return content, product_ids
