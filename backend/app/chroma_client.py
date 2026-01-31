"""
ChromaDB client for policy vector search (simplified version for AuraShop integration).
"""
import logging
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaClient:
    """Simple ChromaDB client for policy retrieval."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        try:
            self.client = chromadb.Client(Settings(
                anonymized_telemetry=False,
                allow_reset=True
            ))
            self.collection_name = "return_policies"
            self.collection = None
            logger.info("[ChromaClient] Initialized successfully")
        except Exception as e:
            logger.error(f"[ChromaClient] Failed to initialize: {e}")
            self.client = None
            self.collection = None
    
    def get_cosine_similarity_scores(
        self,
        query_text: str,
        product_category: str,
        n_results: int = 10
    ) -> List[tuple]:
        """
        Get policy matches with cosine similarity scores.
        
        Returns:
            List of (policy_id, similarity_score) tuples
        """
        if not self.client or not self.collection:
            logger.warning("[ChromaClient] No collection available, returning empty results")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where={"category": product_category} if product_category else None
            )
            
            if not results or not results.get("ids") or not results["ids"][0]:
                return []
            
            # Combine IDs with distances (convert distance to similarity)
            ids = results["ids"][0]
            distances = results.get("distances", [[]])[0]
            
            # Convert distance to similarity (1 - distance for cosine)
            similarities = [1 - d for d in distances]
            
            return list(zip(ids, similarities))
            
        except Exception as e:
            logger.error(f"[ChromaClient] Error querying policies: {e}")
            return []
    
    def query_policies(
        self,
        query_text: str,
        product_category: str,
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Query policies and return detailed results.
        
        Returns:
            List of policy details with text, metadata, etc.
        """
        if not self.client or not self.collection:
            logger.warning("[ChromaClient] No collection available, returning empty results")
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where={"category": product_category} if product_category else None
            )
            
            if not results or not results.get("documents") or not results["documents"][0]:
                return []
            
            # Build policy details
            documents = results["documents"][0]
            metadatas = results.get("metadatas", [[]])[0]
            ids = results.get("ids", [[]])[0]
            
            policy_details = []
            for i, doc in enumerate(documents):
                metadata = metadatas[i] if i < len(metadatas) else {}
                policy_id = ids[i] if i < len(ids) else f"policy_{i}"
                
                policy_details.append({
                    "id": policy_id,
                    "text": doc,
                    "title": metadata.get("title", "Return Policy"),
                    "category": metadata.get("category", product_category),
                    "metadata": metadata
                })
            
            return policy_details
            
        except Exception as e:
            logger.error(f"[ChromaClient] Error querying policy details: {e}")
            return []
    
    def initialize_collection(self):
        """Initialize or get the policies collection."""
        if not self.client:
            return
        
        try:
            # Try to get existing collection
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"[ChromaClient] Loaded existing collection: {self.collection_name}")
        except Exception:
            # Create new collection if it doesn't exist
            try:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Return policy documents for RAG"}
                )
                logger.info(f"[ChromaClient] Created new collection: {self.collection_name}")
                
                # Add some default policies
                self._add_default_policies()
            except Exception as e:
                logger.error(f"[ChromaClient] Failed to create collection: {e}")
    
    def _add_default_policies(self):
        """Add some default return policies."""
        if not self.collection:
            return
        
        default_policies = [
            {
                "id": "policy_electronics_1",
                "text": "Electronics with physical damage such as cracked screens or broken parts are eligible for return within 30 days of purchase if the damage occurred during shipping or was present at delivery.",
                "metadata": {"category": "Electronics", "title": "Physical Damage Policy"}
            },
            {
                "id": "policy_electronics_2",
                "text": "Functional defects in electronics (device not powering on, software issues, hardware malfunctions) are covered under warranty for 90 days from purchase date.",
                "metadata": {"category": "Electronics", "title": "Functional Defect Policy"}
            },
            {
                "id": "policy_general_1",
                "text": "All products can be returned within 30 days if they are unused, in original packaging, and in resalable condition. Customer-caused damage is not eligible for return.",
                "metadata": {"category": "General", "title": "Standard Return Policy"}
            },
        ]
        
        try:
            self.collection.add(
                ids=[p["id"] for p in default_policies],
                documents=[p["text"] for p in default_policies],
                metadatas=[p["metadata"] for p in default_policies]
            )
            logger.info(f"[ChromaClient] Added {len(default_policies)} default policies")
        except Exception as e:
            logger.error(f"[ChromaClient] Failed to add default policies: {e}")


# Global instance - lazy initialization
chroma_client = None

def get_chroma_client():
    """Get or create the global ChromaDB client."""
    global chroma_client
    if chroma_client is None:
        chroma_client = ChromaClient()
        chroma_client.initialize_collection()
    return chroma_client
