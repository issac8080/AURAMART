"""
Load products from backend/data/products.json into MySQL (recommend.products).
Run from backend: python -m scripts.load_products_to_mysql
"""
import json
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from recommend.db import get_engine, get_session, init_db
from recommend.models_db import Product, Base


def main():
    init_db()
    products_path = backend_dir / "data" / "products.json"
    if not products_path.exists():
        print(f"ERROR: {products_path} not found")
        return 1
    print(f"Loading products from {products_path}...")
    with open(products_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        print("ERROR: products.json should be a JSON array")
        return 1
    session = get_session()
    try:
        existing = {r.id for r in session.query(Product.id).all()}
        batch_size = 500
        inserted = 0
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            for p in batch:
                pid = p.get("id")
                if not pid or pid in existing:
                    continue
                session.add(
                    Product(
                        id=pid,
                        name=(p.get("name") or "")[:512],
                        description=((p.get("description") or "")[:10000]) or None,
                        price=float(p.get("price", 0)),
                        currency=p.get("currency", "INR"),
                        category=(p.get("category") or "")[:128] or None,
                        subcategory=(p.get("subcategory") or "")[:128] if p.get("subcategory") else None,
                        brand=(p.get("brand") or "")[:128] if p.get("brand") else None,
                        rating=float(p.get("rating", 0)),
                        review_count=int(p.get("review_count", 0)),
                        colors=p.get("colors") or [],
                        sizes=p.get("sizes") or [],
                        image_url=(p.get("image_url") or "")[:1024] or None,
                        tags=p.get("tags") or [],
                        in_stock=p.get("in_stock", True),
                        stock_count=p.get("stock_count"),
                    )
                )
                existing.add(pid)
                inserted += 1
            session.commit()
            print(f"  Committed batch, total inserted so far: {inserted}")
        print(f"Done. Inserted {inserted} products.")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
