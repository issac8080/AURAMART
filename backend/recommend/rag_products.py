"""
RAG for product recommendations: vector index of products + optional user data,
keyword + semantic search, then LLM rerank to top 5 with preference boost.
"""
import json
import os
from pathlib import Path
from typing import List, Optional

from recommend.db import get_session
from recommend.models_db import Product

# Single embedding model ID and singleton so weights load once (no double load)
EMBEDDING_MODEL_ID = "all-MiniLM-L6-v2"

_CHROMA_CLIENT = None
_PRODUCT_COLLECTION = None
_EMBEDDING_MODEL = None
_EMBEDDING_POSITION_ID = "__shared_sentence_transformer__"  # stable id for embedding position / reuse


def _get_embedding_model():
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_ID)
        except Exception:
            _EMBEDDING_MODEL = False  # mark as failed
    return _EMBEDDING_MODEL if _EMBEDDING_MODEL else None


def init_embeddings() -> bool:
    """Initialize the shared SentenceTransformer once at startup. Call early to avoid first-request latency."""
    return _get_embedding_model() is not None


def _embed_fn(texts: List[str]) -> List[List[float]]:
    model = _get_embedding_model()
    if model is None:
        return [[0.0] * 384] * len(texts)  # dummy
    return model.encode(texts, convert_to_numpy=True).tolist()


class _SharedChromaEmbeddingFunction:
    """Chroma embedding function that uses the single shared SentenceTransformer (avoids loading weights twice)."""
    def __call__(self, input: List[str]) -> List[List[float]]:
        return _embed_fn(input)

    def name(self) -> str:
        """Chroma expects embedding_function.name() for config/serialization."""
        return "sentence_transformer"

    def default_space(self):
        """Chroma expects default_space() for collection config."""
        return "cosine"

    def supported_spaces(self) -> List[str]:
        """Chroma may check supported spaces."""
        return ["cosine", "l2", "ip"]


# One instance for all Chroma collections (products, FAQ) so embedding position id is shared
_SHARED_CHROMA_EMBEDDING_FN = _SharedChromaEmbeddingFunction()


def get_shared_embedding_function():
    """Return the shared embedding function for Chroma (single model load). Use for products and FAQ."""
    return _SHARED_CHROMA_EMBEDDING_FN


def _get_product_collection():
    global _CHROMA_CLIENT, _PRODUCT_COLLECTION
    if _PRODUCT_COLLECTION is not None:
        return _PRODUCT_COLLECTION
    # Ensure singleton model is loaded before Chroma uses it (single embedding position)
    _get_embedding_model()
    try:
        import chromadb
        from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE
        persist_dir = str(Path(__file__).resolve().parent.parent / "data" / "chroma_products")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _CHROMA_CLIENT = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )
        _PRODUCT_COLLECTION = _CHROMA_CLIENT.get_or_create_collection(
            name="products",
            embedding_function=_SHARED_CHROMA_EMBEDDING_FN,
            metadata={"hnsw:space": "cosine"},
        )
        return _PRODUCT_COLLECTION
    except Exception as e:
        print(f"Chroma init error: {e}")
        return None


# ChromaDB has a max batch size (~5461); use 5000 to stay under
CHROMA_MAX_BATCH = 5000


def build_product_index(limit: int = 10000) -> int:
    """
    Index products (and optionally user data) into Chroma.
    Adds in batches to stay under ChromaDB's max batch size.
    Returns number of documents indexed.
    """
    coll = _get_product_collection()
    if coll is None:
        return 0
    session = get_session()
    try:
        products = (
            session.query(Product)
            .limit(limit)
            .all()
        )
        if not products:
            return 0
        total = 0
        for start in range(0, len(products), CHROMA_MAX_BATCH):
            batch = products[start : start + CHROMA_MAX_BATCH]
            ids = []
            documents = []
            metadatas = []
            for p in batch:
                text = " ".join(filter(None, [
                    p.name,
                    p.category,
                    p.brand,
                    (p.description or "")[:300],
                    " ".join(p.tags or []),
                ]))
                ids.append(p.id)
                documents.append(text)
                metadatas.append({
                    "product_id": p.id,
                    "category": p.category or "",
                    "price": float(p.price),
                    "rating": float(p.rating),
                    "name": (p.name or "")[:200],
                })
            try:
                coll.delete(ids=ids)
            except Exception:
                pass
            coll.add(ids=ids, documents=documents, metadatas=metadatas)
            total += len(ids)
        return total
    finally:
        session.close()


def semantic_search_products(
    query: str,
    top_k: int = 15,
    keyword_filter: Optional[dict] = None,
) -> List[dict]:
    """
    Semantic search (cosine similarity) + optional keyword filter.
    Returns list of { product_id, score, metadata }.
    """
    coll = _get_product_collection()
    if coll is None:
        return []
    try:
        where = keyword_filter if keyword_filter else None
        results = coll.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["metadatas", "distances"],
        )
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        out = []
        for i, pid in enumerate(results["ids"][0]):
            dist = (results["distances"][0][i] if results.get("distances") else 0)
            score = 1.0 - dist if dist <= 2 else 0.0  # cosine distance -> similarity
            meta = (results["metadatas"][0][i] if results.get("metadatas") else {}) or {}
            out.append({
                "product_id": meta.get("product_id", pid),
                "score": float(score),
                "metadata": meta,
            })
        return out
    except Exception as e:
        print(f"Chroma query error: {e}")
        return []


def keyword_match_products(query: str, limit: int, session) -> List[dict]:
    """SQL/keyword match: products where name, tags, category match query words."""
    words = [w.strip().lower() for w in query.split() if w.strip()]
    if not words:
        return []
    from sqlalchemy import or_
    cond = or_(
        *[Product.name.ilike(f"%{w}%") for w in words[:5]],
        *[Product.category.ilike(f"%{w}%") for w in words[:5]],
    )
    products = (
        session.query(Product)
        .filter(Product.in_stock == True, cond)
        .order_by(Product.rating.desc())
        .limit(limit)
        .all()
    )
    return [_product_row_to_dict(p) for p in products]


def _product_row_to_dict(p: Product) -> dict:
    return {
        "product_id": p.id,
        "name": p.name,
        "price": p.price,
        "category": p.category,
        "rating": p.rating,
        "metadata": {"product_id": p.id, "category": p.category, "price": p.price, "rating": p.rating, "name": p.name},
    }


def hybrid_search(
    query: str,
    top_k_semantic: int = 15,
    top_k_keyword: int = 10,
) -> List[dict]:
    """
    Merge semantic (Chroma) and keyword (DB) results; dedupe by product_id; return top 10–15.
    """
    session = get_session()
    try:
        sem = semantic_search_products(query, top_k=top_k_semantic)
        kw = keyword_match_products(query, limit=top_k_keyword, session=session)
        by_id = {}
        for i, r in enumerate(sem):
            pid = r.get("product_id") or r.get("metadata", {}).get("product_id")
            if pid and pid not in by_id:
                by_id[pid] = {**r, "rank": len(by_id), "source": "semantic"}
        for r in kw:
            pid = r.get("product_id")
            if pid and pid not in by_id:
                by_id[pid] = {**r, "score": 0.8, "rank": len(by_id), "source": "keyword"}
            elif pid and by_id.get(pid):
                by_id[pid]["score"] = max(by_id[pid].get("score", 0), 0.85)
        merged = sorted(by_id.values(), key=lambda x: (-x.get("score", 0), -x.get("metadata", {}).get("rating", 0)))
        return merged[: max(top_k_semantic, top_k_keyword)]
    finally:
        session.close()


def rerank_with_llm(
    query: str,
    candidates: List[dict],
    top_n: int = 5,
    user_preference: Optional[str] = None,
) -> List[dict]:
    """
    Inject query + candidates into LLM prompt; LLM returns best 5.
    If user_preference is stated and a product matches, boost that product.
    """
    if not candidates:
        return []
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        # Fallback: sort by score and rating
        boosted = list(candidates)[: top_n * 2]
        if user_preference and user_preference.strip():
            pref = user_preference.strip().lower()
            for c in boosted:
                meta = c.get("metadata") or {}
                name = (meta.get("name") or "").lower()
                cat = (meta.get("category") or "").lower()
                if pref in name or pref in cat:
                    c["score"] = c.get("score", 0) + 0.2
        boosted.sort(key=lambda x: (-x.get("score", 0), -x.get("metadata", {}).get("rating", 0)))
        return boosted[:top_n]
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        product_list = "\n".join(
            [
                f"- {c.get('product_id')}: {c.get('metadata', {}).get('name', '')} (₹{c.get('metadata', {}).get('price', 0)}, {c.get('metadata', {}).get('category', '')})"
                for c in candidates[:20]
            ]
        )
        prompt = f"""User query: {query}
Candidate products:
{product_list}

Return exactly the top {top_n} product IDs that best match the query, one per line. Only IDs, no explanation.
"""
        if user_preference:
            prompt += f"\nUser preference to prioritize: {user_preference}\n"
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        text = (resp.choices[0].message.content or "").strip()
        order_ids = [line.strip().split()[0] for line in text.splitlines() if line.strip()][:top_n]
        by_id = {c.get("product_id"): c for c in candidates if c.get("product_id")}
        out = []
        for pid in order_ids:
            if pid in by_id:
                out.append(by_id[pid])
        for c in candidates:
            if c.get("product_id") not in [x.get("product_id") for x in out]:
                out.append(c)
            if len(out) >= top_n:
                break
        return out[:top_n]
    except Exception as e:
        print(f"LLM rerank error: {e}")
        boosted = list(candidates)[:top_n * 2]
        if user_preference:
            pref = user_preference.strip().lower()
            for c in boosted:
                meta = c.get("metadata") or {}
                if pref in (meta.get("name") or "").lower() or pref in (meta.get("category") or "").lower():
                    c["score"] = c.get("score", 0) + 0.2
        boosted.sort(key=lambda x: (-x.get("score", 0), -x.get("metadata", {}).get("rating", 0)))
        return boosted[:top_n]


def recommend_products_rag(
    query: str,
    top_semantic: int = 15,
    top_rerank: int = 5,
    user_preference: Optional[str] = None,
) -> List[dict]:
    """
    Full pipeline: hybrid search (keyword + semantic) -> top 10–15 -> LLM rerank -> best 5,
    with preference boost if user stated a specific preference.
    """
    candidates = hybrid_search(query, top_k_semantic=top_semantic, top_k_keyword=10)
    return rerank_with_llm(query, candidates, top_n=top_rerank, user_preference=user_preference)


# Eager-init shared embedding model on first import so it is not loaded on every embed call
init_embeddings()
