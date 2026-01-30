"""
LLM chatbot: route user message to order (agentic_order), recommend (RAG products), or FAQ (RAG FAQ).
Intent is decoded by LLM instead of keyword matching.
"""
import os
import re
from typing import Optional

from recommend.agentic_order import process_order_from_message, process_order
from recommend.rag_products import recommend_products_rag
from recommend.rag_faq import answer_faq_with_llm


INTENT_ORDER = "order"
INTENT_RECOMMEND = "recommend"
INTENT_FAQ = "faq"
INTENT_OTHER = "other"


def _classify_intent_keyword_fallback(message: str) -> str:
    """Fallback when LLM is unavailable or returns invalid intent."""
    msg = (message or "").strip().lower()
    order_keywords = ["order", "buy", "purchase", "add to cart", "get me", "send me", "place order", "checkout"]
    faq_keywords = ["return", "policy", "refund", "delivery", "ship", "track", "wallet", "aurapoints", "cancel", "how do i", "how to", "what is", "faq", "help"]
    if any(k in msg for k in order_keywords):
        return INTENT_ORDER
    if any(k in msg for k in faq_keywords):
        return INTENT_FAQ
    return INTENT_RECOMMEND


def classify_intent(message: str) -> str:
    """
    Classify user message: order vs recommend vs FAQ using LLM.
    Falls back to keyword matching if OPENAI_API_KEY is missing or LLM fails.
    """
    msg = (message or "").strip()
    if not msg:
        return INTENT_RECOMMEND
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        return _classify_intent_keyword_fallback(message)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        prompt = """You are an intent classifier for a shopping assistant chatbot. Classify the user message into exactly one intent.

Intents:
- order: user wants to buy, purchase, or place an order for specific product(s) (e.g. "order 2x P00001", "buy me that shirt", "get me a phone").
- recommend: user wants product suggestions, recommendations, or to browse (e.g. "best phones under 20k", "suggest casual shoes", "what do you have for gifts").
- faq: user is asking about policies, help, or how things work (e.g. "return policy", "how do I track", "what is AuraPoints").

User message: "{message}"

Reply with exactly one word: order, recommend, or faq. No other text.""".format(message=msg[:500])
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=10,
        )
        text = (resp.choices[0].message.content or "").strip().lower()
        if text in (INTENT_ORDER, INTENT_RECOMMEND, INTENT_FAQ):
            return text
        if "order" in text:
            return INTENT_ORDER
        if "faq" in text:
            return INTENT_FAQ
        return INTENT_RECOMMEND
    except Exception:
        return _classify_intent_keyword_fallback(message)


def extract_preference(message: str) -> Optional[str]:
    """Extract user preference from message for product boost (e.g. 'under 2000', 'red')."""
    msg = (message or "").strip().lower()
    # Budget: under X, below X, budget X
    m = re.search(r"(?:under|below|within|budget)\s*(?:rs\.?|₹|inr)?\s*(\d+)", msg)
    if m:
        return f"under ₹{m.group(1)}"
    # Color
    colors = ["red", "blue", "black", "white", "green", "grey", "navy", "brown"]
    for c in colors:
        if c in msg:
            return c
    return None


def chat(user_id: str, message: str) -> dict:
    """
    Main entry: route to order / recommend / FAQ and return { content, product_ids, order_id, success }.
    """
    intent = classify_intent(message)
    content = ""
    product_ids = []
    order_id = None
    success = True

    if intent == INTENT_ORDER:
        result = process_order_from_message(user_id=user_id, message=message)
        success = result.get("success", False)
        content = result.get("message", "")
        order_id = result.get("order_id")
        return {"content": content, "product_ids": product_ids, "order_id": order_id, "success": success}

    if intent == INTENT_RECOMMEND:
        preference = extract_preference(message)
        recs = recommend_products_rag(
            query=message,
            top_semantic=15,
            top_rerank=5,
            user_preference=preference,
        )
        if not recs:
            content = "I couldn't find matching products. Try describing what you're looking for (e.g. 'phones under 20k', 'casual shoes')."
        else:
            product_ids = [r.get("product_id") or r.get("metadata", {}).get("product_id") for r in recs if r.get("product_id") or r.get("metadata", {}).get("product_id")]
            product_ids = list(dict.fromkeys(product_ids))[:5]
            lines = [f"- {r.get('metadata', {}).get('name', r.get('product_id', ''))} (₹{r.get('metadata', {}).get('price', 0)}, {r.get('metadata', {}).get('category', '')})" for r in recs[:5]]
            content = "Here are my top picks:\n" + "\n".join(lines)
        return {"content": content, "product_ids": product_ids, "order_id": None, "success": True}

    if intent == INTENT_FAQ:
        content = answer_faq_with_llm(message, top_k=3)
        return {"content": content, "product_ids": [], "order_id": None, "success": True}

    # Fallback: try recommend
    preference = extract_preference(message)
    recs = recommend_products_rag(message, top_semantic=10, top_rerank=5, user_preference=preference)
    if recs:
        product_ids = [r.get("product_id") or (r.get("metadata") or {}).get("product_id") for r in recs if (r.get("product_id") or (r.get("metadata") or {}).get("product_id"))]
        product_ids = list(dict.fromkeys(product_ids))[:5]
        lines = [f"- {r.get('metadata', {}).get('name', r.get('product_id', ''))} (₹{r.get('metadata', {}).get('price', 0)})" for r in recs[:5]]
        content = "Here are some products you might like:\n" + "\n".join(lines)
    else:
        content = "How can I help? You can ask me to order a product (e.g. 'Order P00001'), recommend products (e.g. 'Best phones under 20k'), or ask a FAQ (e.g. 'What is your return policy?')."
    return {"content": content, "product_ids": product_ids, "order_id": None, "success": True}
