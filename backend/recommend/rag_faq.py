"""
RAG for FAQ: index FAQ rows (question, answer), semantic search, inject into LLM prompt for answer.
"""
import os
from pathlib import Path
from typing import List, Optional

from recommend.db import get_session
from recommend.models_db import FAQ

_CHROMA_FAQ_CLIENT = None
_FAQ_COLLECTION = None


def _get_faq_collection():
    global _CHROMA_FAQ_CLIENT, _FAQ_COLLECTION
    if _FAQ_COLLECTION is not None:
        return _FAQ_COLLECTION
    try:
        import chromadb
        from chromadb.config import Settings, DEFAULT_TENANT, DEFAULT_DATABASE
        from recommend.rag_products import get_shared_embedding_function
        persist_dir = str(Path(__file__).resolve().parent.parent / "data" / "chroma_faq")
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        _CHROMA_FAQ_CLIENT = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
            tenant=DEFAULT_TENANT,
            database=DEFAULT_DATABASE,
        )
        _FAQ_COLLECTION = _CHROMA_FAQ_CLIENT.get_or_create_collection(
            name="faq",
            embedding_function=get_shared_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        return _FAQ_COLLECTION
    except Exception as e:
        print(f"Chroma FAQ init error: {e}")
        return None


def build_faq_index() -> int:
    """Index FAQ table into Chroma. Returns number of documents indexed."""
    coll = _get_faq_collection()
    if coll is None:
        return 0
    session = get_session()
    try:
        faqs = session.query(FAQ).all()
        ids = []
        documents = []
        metadatas = []
        for f in faqs:
            doc = f"{f.question} {f.answer}"[:2000]
            ids.append(f"faq_{f.id}")
            documents.append(doc)
            metadatas.append({"faq_id": f.id, "question": (f.question or "")[:500], "answer": (f.answer or "")[:1000], "category": f.category or ""})
        if not ids:
            return 0
        try:
            coll.delete(ids=ids)
        except Exception:
            pass
        coll.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(ids)
    finally:
        session.close()


def faq_search(query: str, top_k: int = 5) -> List[dict]:
    """Semantic search over FAQ. Returns list of { faq_id, question, answer, score }. """
    coll = _get_faq_collection()
    if coll is None:
        return []
    try:
        results = coll.query(
            query_texts=[query],
            n_results=top_k,
            include=["metadatas", "distances"],
        )
        if not results or not results["ids"] or not results["ids"][0]:
            return []
        out = []
        for i, fid in enumerate(results["ids"][0]):
            dist = results["distances"][0][i] if results.get("distances") else 0
            score = 1.0 - dist if dist <= 2 else 0.0
            meta = (results["metadatas"][0][i] if results.get("metadatas") else {}) or {}
            out.append({
                "faq_id": meta.get("faq_id"),
                "question": meta.get("question", ""),
                "answer": meta.get("answer", ""),
                "category": meta.get("category", ""),
                "score": float(score),
            })
        return out
    except Exception as e:
        print(f"FAQ query error: {e}")
        return []


def answer_faq_with_llm(query: str, top_k: int = 3) -> str:
    """
    Retrieve top FAQ chunks, inject into LLM prompt, return answer.
    """
    hits = faq_search(query, top_k=top_k)
    if not hits:
        return "I couldn't find a relevant FAQ. Please contact support or rephrase your question."
    openai_key = os.getenv("OPENAI_API_KEY")
    context = "\n\n".join([f"Q: {h['question']}\nA: {h['answer']}" for h in hits])
    if not openai_key:
        return hits[0].get("answer", "") or "No answer found."
    try:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)
        prompt = f"""Use the following FAQ context to answer the user question. Be concise and accurate. If the context doesn't contain the answer, say so.

Context:
{context}

User question: {query}

Answer:"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return (resp.choices[0].message.content or hits[0].get("answer", "")).strip()
    except Exception as e:
        print(f"FAQ LLM error: {e}")
        return hits[0].get("answer", "") or "I couldn't generate an answer. Please try again."
