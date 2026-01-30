"""
Build RAG indices: products (Chroma) and FAQ (Chroma).
Run after loading products and FAQ into MySQL: python -m scripts.build_rag_index
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from recommend.rag_products import build_product_index
from recommend.rag_faq import build_faq_index


def main():
    print("Building product index...")
    n_products = build_product_index(limit=15000)
    print(f"  Indexed {n_products} products.")
    print("Building FAQ index...")
    n_faq = build_faq_index()
    print(f"  Indexed {n_faq} FAQ entries.")
    print("Done. You can run cli_chatbot and cli_recommend now.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
