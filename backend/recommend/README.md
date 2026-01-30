# Recommend module

Recommendation engine (6 types), chatbot with RAG, and agentic order processing. Tested via CLI only (no API endpoints).

## Setup

1. **MySQL (XAMPP)**  
   Start MySQL, create database `auramart`, set in `.env`:
   ```
   MYSQL_URI=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/auramart
   ```
   If `MYSQL_URI` is unset or pymysql is not installed, the module falls back to SQLite at `backend/data/recommend.db`.

2. **Dependencies**  
   From `backend`: `pip install -r requirements.txt` (adds pymysql, sqlalchemy, chromadb, sentence-transformers, langgraph, langchain-core, langchain-openai).

3. **Load data (from backend)**  
   ```bash
   python -m scripts.load_products_to_mysql   # products from data/products.json
   python -m scripts.load_orders_to_mysql     # orders + users from data/orders.json
   python -m scripts.seed_recommendation_users --users 100   # synthetic users, orders, events, festivals, FAQ
   python -m scripts.build_rag_index          # Chroma indices for products + FAQ
   ```

## Interactive menu (recommended)

From `backend` run:

```bash
python -m scripts.run_recommend_menu
```

You get a menu to choose:

1. **Recommendations** – Pick user ID, type (category, search_no_buy, already_bought, out_of_stock_notify, festival, habits), limit; optionally subscribe to out-of-stock product.
2. **Chatbot** – Single message or interactive chat (order / recommend / FAQ).
3. **Habits** – List “Wanna reorder that?” and optionally confirm a product to reorder.
4. **Data setup** – Load products, load orders, seed users/events/festivals/FAQ, build RAG index (or run all).
0. **Exit**

Use the interactive menu for all flows; there are no separate CLI command scripts.

## Module layout

- `db.py` – SQLAlchemy engine/session (MySQL or SQLite).
- `models_db.py` – ORM: users, products, orders, order_items, events, stock_notify, festivals, faq.
- `recommendation_engine.py` – 6 recommendation types (category, search_no_buy, already_bought, out_of_stock_notify, festival, habits).
- `habits.py` – Detect repeated purchases; "Wanna reorder that?".
- `festivals.py` – Festival-based suggestions.
- `agentic_order.py` – LangGraph agentic workflow: parse_intent → extract_order_items (LLM) → resolve_products (RAG/DB) → create_order → format_response. Exposes `process_order_from_message(user_id, message)` for natural-language orders and `process_order(user_id, product_quantities)` for direct (product_id, qty) calls (e.g. habit reorder).
- `rag_products.py` – Product RAG: keyword + semantic search, LLM rerank, preference boost.
- `rag_faq.py` – FAQ RAG: semantic search + LLM answer.
- `chatbot.py` – Intent routing (order / recommend / FAQ) and response.
