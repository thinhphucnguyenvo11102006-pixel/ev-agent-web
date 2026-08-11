"""
E.V. Memory Manager — Unified interface for all memory systems.
Combines short-term, long-term (ChromaDB), and structured (SQLite) memory.
"""

import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import config
from memory.short_term import ShortTermMemory, Message
from memory.long_term import LongTermMemory
from memory.structured import StructuredMemory

logger = logging.getLogger("ev.memory.manager")


class MemoryManager:
    """
    Unified memory interface.
    
    - Short-term: recent conversation messages (in-memory deque)
    - Long-term: semantic memories (ChromaDB)
    - Structured: preferences, reminders, logs (SQLite)
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("session_%Y%m%d_%H%M%S")

        # Initialize memory systems
        self.short_term = ShortTermMemory(max_messages=config.MAX_SHORT_TERM_MESSAGES)
        self.long_term = LongTermMemory(persist_dir=config.CHROMA_DB_PATH)
        self.structured = StructuredMemory(db_path=config.SQLITE_DB_PATH)

        logger.info(f"Memory manager initialized (session: {self.session_id})")

    def add_user_message(self, content: str) -> Message:
        """Add a user message to short-term memory and log it."""
        msg = self.short_term.add_user_message(content)
        self.structured.log_message(self.session_id, "user", content)
        return msg

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Add an assistant message to short-term memory and log it."""
        msg = self.short_term.add_assistant_message(content, tool_calls)
        self.structured.log_message(self.session_id, "assistant", content, tool_calls)
        return msg

    def add_tool_result(self, tool_call_id: str, content: str, name: str = "") -> Message:
        """Add a tool result to short-term memory."""
        msg = self.short_term.add_tool_result(tool_call_id, content, name)
        return msg

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in API format for LLM context."""
        return self.short_term.get_messages()

    async def remember(self, text: str, category: str = "general",
                       metadata: Optional[Dict[str, Any]] = None):
        """
        Store information in long-term memory (async, non-blocking).
        Called after conversations to persist important information.
        """
        meta = metadata or {}
        meta["category"] = category
        meta["session_id"] = self.session_id

        # Store in ChromaDB (semantic)
        self.long_term.store(text, meta)

        # Also store as a fact in SQLite
        self.structured.add_fact(category, text, source=self.session_id)

    async def recall(self, query: str, top_k: int = None) -> List[Dict[str, Any]]:
        """
        Recall relevant memories for the given query.
        Combines semantic (ChromaDB) and keyword (SQLite FTS) results.
        """
        top_k = top_k or config.MEMORY_TOP_K
        results = []

        # Semantic recall from ChromaDB (offloaded to thread to avoid blocking asyncio event loop)
        semantic_results = await asyncio.to_thread(self.long_term.recall, query, top_k)
        for r in semantic_results:
            dist = float(r.get("distance", 1.0))
            rel = max(0.0, 1.0 - dist)
            results.append({
                "source": "semantic",
                "text": r["text"],
                "relevance": rel,
                "metadata": r.get("metadata", {}),
            })

        # Keyword search from SQLite
        keyword_results = self.structured.search_conversations(query, limit=top_k)
        for r in keyword_results:
            results.append({
                "source": "keyword",
                "text": r.get("content", ""),
                "relevance": 0.5,  # Lower default relevance for keyword matches
                "metadata": {"role": r.get("role", ""), "session_id": r.get("session_id", "")},
            })

        # Sort by relevance and deduplicate
        results.sort(key=lambda x: x["relevance"], reverse=True)

        # Deduplicate by text content
        seen = set()
        unique_results = []
        for r in results:
            text_key = r["text"][:100]
            if text_key not in seen:
                seen.add(text_key)
                unique_results.append(r)

        return unique_results[:top_k]

    def get_context_for_prompt(self, user_input: str) -> str:
        """
        Get relevant context string for the LLM prompt.
        Called by context_assembler.
        """
        # Get user preferences
        prefs = self.structured.get_all_preferences()
        
        # Get recent facts
        facts = self.structured.get_facts(limit=10)

        context_parts = []

        # Add user preferences if any
        if prefs:
            pref_lines = [f"- {k}: {v}" for k, v in prefs.items()]
            context_parts.append("### User Preferences\n" + "\n".join(pref_lines))

        # Add known facts
        if facts:
            fact_lines = [f"- [{f['category']}] {f['content']}" for f in facts]
            context_parts.append("### Known Facts\n" + "\n".join(fact_lines))

        return "\n\n".join(context_parts) if context_parts else ""

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return {
            "session_id": self.session_id,
            "short_term_messages": self.short_term.count,
            "long_term_memories": self.long_term.count(),
            "preferences": len(self.structured.get_all_preferences()),
        }

    def close(self):
        """Clean up resources."""
        self.structured.close()
        logger.info("Memory manager closed")
