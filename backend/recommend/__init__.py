"""
Recommendation and chatbot (RAG) module.
Uses MySQL for relational data and Chroma for vector search.
"""
from recommend.db import get_engine, get_session, init_db

__all__ = ["get_engine", "get_session", "init_db"]
