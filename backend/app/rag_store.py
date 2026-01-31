"""
RAG vector store: product and FAQ embeddings for semantic search.
Uses ChromaDB. If ChromaDB is not installed or fails, all functions return empty/safe
results so the rest of the app keeps working (keyword fallback in ai_service).
"""
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from app.data_store import load_products, get_product
from app.models import Product

# Lazy init - avoid import errors if chromadb not installed
_chroma_client = None
_products_collection = None
_faq_collection = None
_products_indexed = False
_faq_indexed = False
_rag_available = None

def _rag_available_check() -> bool:
    global _rag_available
    if _rag_available is not None:
        return _rag_available
    try:
        import chromadb  # noqa: F401
        _rag_available = True
    except Exception:
        _rag_available = False
    return _rag_available


def _get_client():
    global _chroma_client
    if _chroma_client is None and _rag_available_check():
        try:
            import chromadb
            from chromadb.config import Settings
            PERSIST_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma_db"
            PERSIST_DIR.mkdir(parents=True, exist_ok=True)
            _chroma_client = chromadb.PersistentClient(
                path=str(PERSIST_DIR),
                settings=Settings(anonymized_telemetry=False),
            )
        except Exception:
            pass
    return _chroma_client


def _product_to_document(p: Product) -> str:
    parts = [p.name, p.description or "", p.category]
    if p.tags:
        parts.append(" ".join(str(t) for t in p.tags))
    if p.colors:
        parts.append(" ".join(str(c) for c in p.colors))
    return " ".join(parts).strip()


def _ensure_products_index() -> bool:
    global _products_collection, _products_indexed
    if _products_indexed and _products_collection is not None:
        return True
    client = _get_client()
    if client is None:
        _products_indexed = True
        return False
    try:
        name = "aurashop_products"
        _products_collection = client.get_or_create_collection(name=name, metadata={"description": "products"})
    except Exception:
        _products_indexed = True
        return False
    products = load_products()
    if not _products_indexed and products:
        try:
            count = _products_collection.count()
            if count == 0:
                ids = []
                documents = []
                metadatas = []
                for p in products:
                    ids.append(p.id)
                    documents.append(_product_to_document(p))
                    metadatas.append({
                        "product_id": p.id,
                        "name": (p.name or "")[:200],
                        "category": p.category,
                        "price": float(p.price),
                        "rating": float(p.rating),
                    })
                _products_collection.add(ids=ids, documents=documents, metadatas=metadatas)
        except Exception:
            pass
        _products_indexed = True
    return _products_collection is not None


def _ensure_faq_index() -> bool:
    global _faq_collection, _faq_indexed
    if _faq_indexed and _faq_collection is not None:
        return True
    FAQ_PATH = Path(__file__).resolve().parent.parent / "data" / "faq.json"
    if not FAQ_PATH.exists():
        _faq_indexed = True
        return False
    client = _get_client()
    if client is None:
        _faq_indexed = True
        return False
    try:
        name = "aurashop_faq"
        _faq_collection = client.get_or_create_collection(name=name, metadata={"description": "faq"})
    except Exception:
        _faq_indexed = True
        return False
    try:
        count = _faq_collection.count()
        if count == 0:
            with open(FAQ_PATH, "r", encoding="utf-8") as f:
                faq_list = json.load(f)
            if not isinstance(faq_list, list):
                faq_list = []
            ids_faq = []
            documents_faq = []
            metadatas_faq = []
            for i, item in enumerate(faq_list):
                q = item.get("q") or item.get("question") or ""
                a = item.get("a") or item.get("answer") or ""
                doc = f"{q} {a}"
                ids_faq.append(f"faq_{i}")
                documents_faq.append(doc)
                metadatas_faq.append({"question": q[:300], "answer": a[:500]})
            if ids_faq:
                _faq_collection.add(ids=ids_faq, documents=documents_faq, metadatas=metadatas_faq)
    except Exception:
        pass
    _faq_indexed = True
    return _faq_collection is not None


def search_products_semantic(query: str, top_k: int = 15) -> List[Dict[str, Any]]:
    """Semantic search over products. Returns list of { product_id, distance, metadata }. Empty on error."""
    if not _rag_available_check():
        return []
    try:
        _ensure_products_index()
        if _products_collection is None:
            return []
        results = _products_collection.query(
            query_texts=[query],
            n_results=min(top_k, 50),
            include=["metadatas", "distances"],
        )
        if not results or not results.get("ids") or not results["ids"][0]:
            return []
        out = []
        for i, pid in enumerate(results["ids"][0]):
            meta = (results["metadatas"][0] or [{}])[i] if results.get("metadatas") else {}
            dist = (results["distances"][0] or [0])[i] if results.get("distances") else 0
            out.append({"product_id": pid, "distance": float(dist), "metadata": meta})
        return out
    except Exception:
        return []


def search_products_keyword(query: str, products: Optional[List[Product]] = None, top_k: int = 15) -> List[str]:
    """Keyword match on name, category, tags. Returns list of product_ids."""
    if products is None:
        products = load_products()
    words = re.findall(r"\w+", query.lower())
    if not words:
        return [p.id for p in products[:top_k]]
    scored = []
    for p in products:
        text = f"{p.name} {p.category} {' '.join(p.tags)}".lower()
        score = sum(1 for w in words if w in text)
        if score > 0:
            scored.append((p.id, score))
    scored.sort(key=lambda x: -x[1])
    return [pid for pid, _ in scored[:top_k]]


def search_products_hybrid(query: str, top_k: int = 15) -> List[Dict[str, Any]]:
    """Merge semantic + keyword results, dedupe, return up to top_k."""
    semantic = search_products_semantic(query, top_k=top_k)
    keyword_ids = search_products_keyword(query, top_k=top_k)
    seen = set()
    out = []
    for s in semantic:
        pid = s.get("product_id") or s.get("id")
        if pid and pid not in seen:
            seen.add(pid)
            out.append({"product_id": pid, "distance": s.get("distance", 0), "metadata": s.get("metadata", {})})
    for kid in keyword_ids:
        if kid not in seen and len(out) < top_k:
            seen.add(kid)
            out.append({"product_id": kid, "distance": 999, "metadata": {}})
    return out[:top_k]


def search_faq(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Semantic search over FAQ. Returns list of { question, answer, distance }. Empty on error."""
    if not _rag_available_check():
        return []
    try:
        _ensure_faq_index()
        if _faq_collection is None:
            return []
        results = _faq_collection.query(
            query_texts=[query],
            n_results=min(top_k, 10),
            include=["metadatas", "distances"],
        )
        if not results or not results.get("ids") or not results["ids"][0]:
            return []
        out = []
        for i, _ in enumerate(results["ids"][0]):
            meta = (results["metadatas"][0] or [{}])[i] if results.get("metadatas") else {}
            dist = (results["distances"][0] or [0])[i] if results.get("distances") else 0
            out.append({
                "question": meta.get("question", ""),
                "answer": meta.get("answer", ""),
                "distance": float(dist),
            })
        return out
    except Exception:
        return []
