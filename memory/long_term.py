"""
E.V. Long-term Memory — ChromaDB vector store for semantic memory.
Stores conversation summaries, facts, and user preferences.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ev.memory.long_term")


class LongTermMemory:
    """
    ChromaDB-backed semantic memory.
    Stores and retrieves information based on meaning similarity.
    """

    def __init__(self, persist_dir: str = "./data/chroma_db", collection_name: str = "ev_memory"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self._collection = None
        self._client = None
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization of ChromaDB."""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialized = True
            logger.info(f"ChromaDB initialized at {self.persist_dir} (collection: {self.collection_name})")
            logger.info(f"Existing documents: {self._collection.count()}")
        except ImportError:
            logger.warning("ChromaDB not installed. Long-term memory disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")

    def store(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ):
        """Store a text with optional metadata."""
        self._ensure_initialized()
        if not self._collection:
            return

        if not doc_id:
            doc_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        meta = metadata or {}
        meta["timestamp"] = datetime.now().isoformat()

        try:
            self._collection.upsert(
                documents=[text],
                metadatas=[meta],
                ids=[doc_id],
            )
            logger.debug(f"Stored memory: {text[:50]}... (id={doc_id})")
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")

    def recall(
        self,
        query: str,
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recall memories similar to the query.
        
        Returns list of dicts with 'text', 'metadata', 'distance'.
        """
        self._ensure_initialized()
        if not self._collection:
            return []

        try:
            kwargs = {
                "query_texts": [query],
                "n_results": top_k,
            }
            if where:
                kwargs["where"] = where

            results = self._collection.query(**kwargs)

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    memories.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                        "id": results["ids"][0][i] if results["ids"] else "",
                    })

            logger.debug(f"Recalled {len(memories)} memories for: {query[:50]}")
            return memories

        except Exception as e:
            logger.error(f"Failed to recall memories: {e}")
            return []

    def delete(self, doc_id: str):
        """Delete a specific memory."""
        self._ensure_initialized()
        if not self._collection:
            return
        try:
            self._collection.delete(ids=[doc_id])
            logger.debug(f"Deleted memory: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")

    def count(self) -> int:
        """Get total number of stored memories."""
        self._ensure_initialized()
        if not self._collection:
            return 0
        return self._collection.count()

    def clear_all(self):
        """Delete all memories."""
        self._ensure_initialized()
        if self._client:
            try:
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("All long-term memories cleared")
            except Exception as e:
                logger.error(f"Failed to clear memories: {e}")
