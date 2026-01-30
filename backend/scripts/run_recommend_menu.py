"""
Interactive menu to run recommendation, chatbot, habits, and data setup.
Run from backend: python -m scripts.run_recommend_menu
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))


def input_default(prompt, default=""):
    s = input(prompt).strip()
    return s if s else default


def menu_recommendations():
    from recommend.recommendation_engine import get_recommendations, out_of_stock_subscribe
    user_id = input_default("User ID (default U1): ", "U1")
    print("\nRecommendation types:")
    print("  1. category       - Same category as you're buying/browsing")
    print("  2. search_no_buy  - You searched but didn't buy")
    print("  3. already_bought - Cross-sell from order history")
    print("  4. out_of_stock_notify - Out-of-stock items + notify when back")
    print("  5. festival       - Suggestions for current/upcoming festival")
    print("  6. habits         - Wanna reorder that?")
    choice = input_default("Choose 1-6 (default 1): ", "1")
    type_map = {"1": "category", "2": "search_no_buy", "3": "already_bought",
                "4": "out_of_stock_notify", "5": "festival", "6": "habits"}
    rec_type = type_map.get(choice, "category")
    limit = input_default("Limit (default 5): ", "5")
    try:
        limit = int(limit)
    except ValueError:
        limit = 5
    if rec_type == "out_of_stock_notify":
        sub = input("Subscribe to a product ID when back in stock? (product_id or Enter to skip): ").strip()
        if sub:
            result = out_of_stock_subscribe(user_id, sub)
            print("Subscribe result:", result)
            return
    recs = get_recommendations(user_id=user_id, rec_type=rec_type, limit=limit)
    if not recs:
        print("No recommendations.")
        return
    print(f"\nRecommendations ({rec_type}, limit={limit}):")
    for i, r in enumerate(recs, 1):
        if rec_type == "habits":
            print(f"  {i}. {r.get('name', '')} (ID: {r.get('product_id')}, ₹{r.get('price')}, ordered {r.get('order_count')}x) - Wanna reorder?")
        elif rec_type == "out_of_stock_notify":
            print(f"  {i}. {r.get('name')} (ID: {r.get('product_id')}) - Restock: {r.get('probable_restock_at')}, subscribed: {r.get('subscribed')}")
        else:
            print(f"  {i}. {r.get('name', r.get('id', ''))} (ID: {r.get('id', r.get('product_id'))}, ₹{r.get('price')}, {r.get('category', '')})")


def menu_chatbot():
    from recommend.chatbot import chat
    user_id = input_default("User ID (default U1): ", "U1")
    print("\n  1. Single message")
    print("  2. Interactive chat (multiple messages)")
    mode = input_default("Choose 1 or 2 (default 1): ", "1")
    if mode == "2":
        print("\nChatbot (user=%s). Type 'quit' or 'exit' to stop.\n" % user_id)
        while True:
            try:
                msg = input("You: ").strip()
            except EOFError:
                break
            if not msg or msg.lower() in ("quit", "exit", "q"):
                break
            result = chat(user_id=user_id, message=msg)
            print("Bot:", result.get("content", ""))
            if result.get("product_ids"):
                print("  Product IDs:", result["product_ids"])
            if result.get("order_id"):
                print("  Order ID:", result["order_id"])
    else:
        msg = input("Your message: ").strip()
        if not msg:
            print("No message entered.")
            return
        result = chat(user_id=user_id, message=msg)
        print("\nBot:", result.get("content", ""))
        if result.get("product_ids"):
            print("Product IDs:", result["product_ids"])
        if result.get("order_id"):
            print("Order ID:", result["order_id"])


def menu_habits():
    from recommend.habits import get_habit_products
    from recommend.agentic_order import process_order
    user_id = input_default("User ID (default U1): ", "U1")
    habits = get_habit_products(user_id, min_orders=2)
    if not habits:
        print("No habit products (no repeated purchases) for user %s." % user_id)
        return
    print("\nWanna reorder that?")
    for i, h in enumerate(habits, 1):
        print(f"  {i}. {h.get('name')} (ID: {h.get('product_id')}, ₹{h.get('price')}, ordered {h.get('order_count')}x)")
    pid = input("\nEnter product ID to reorder (or Enter to skip): ").strip()
    if pid:
        result = process_order(user_id=user_id, product_quantities=[(pid, 1)])
        print("Order result:", result.get("message", result))
        if result.get("success"):
            print("Order ID:", result.get("order_id"))
    else:
        print("Skipped.")


def _run_script(script_name, argv_extra=None):
    """Run another script in scripts/ by importing its main()."""
    import importlib.util
    script_path = backend_dir / "scripts" / script_name
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return
    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
    mod = importlib.util.module_from_spec(spec)
    old_argv = sys.argv
    try:
        sys.argv = [script_name] + (argv_extra or [])
        spec.loader.exec_module(mod)
        if hasattr(mod, "main"):
            mod.main()
    finally:
        sys.argv = old_argv


def menu_data_setup():
    print("\nData setup:")
    print("  1. Load products (from data/products.json)")
    print("  2. Load orders (from data/orders.json)")
    print("  3. Seed recommendation users + events + festivals + FAQ")
    print("  4. Build RAG index (products + FAQ)")
    print("  5. Run all (1, 2, 3, 4)")
    choice = input_default("Choose 1-5: ", "5")
    if choice == "1":
        _run_script("load_products_to_mysql.py")
    elif choice == "2":
        _run_script("load_orders_to_mysql.py")
    elif choice == "3":
        n = input_default("Number of synthetic users (default 100): ", "100")
        try:
            n = int(n)
        except ValueError:
            n = 100
        _run_script("seed_recommendation_users.py", ["--users", str(n)])
    elif choice == "4":
        _run_script("build_rag_index.py")
    elif choice == "5":
        print("Loading products...")
        _run_script("load_products_to_mysql.py")
        print("Loading orders...")
        _run_script("load_orders_to_mysql.py")
        print("Seeding users/events/festivals/FAQ...")
        _run_script("seed_recommendation_users.py", ["--users", "100"])
        print("Building RAG index...")
        _run_script("build_rag_index.py")
        print("All done.")
    else:
        print("Invalid choice.")


def main():
    while True:
        print("\n" + "=" * 50)
        print("  Recommend & Chatbot Menu")
        print("=" * 50)
        print("  1. Recommendations (category, search_no_buy, festival, habits, etc.)")
        print("  2. Chatbot (order / recommend products / FAQ)")
        print("  3. Habits - Wanna reorder that?")
        print("  4. Data setup (load products, orders, seed users, build RAG index)")
        print("  0. Exit")
        print("=" * 50)
        choice = input("Choose option (0-4): ").strip()
        if choice == "0":
            print("Bye.")
            break
        if choice == "1":
            menu_recommendations()
        elif choice == "2":
            menu_chatbot()
        elif choice == "3":
            menu_habits()
        elif choice == "4":
            menu_data_setup()
        else:
            print("Invalid option. Enter 0-4.")
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    sys.exit(main() or 0)
