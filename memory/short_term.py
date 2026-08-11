"""
E.V. Short-term Memory — In-memory conversation buffer.
Keeps the most recent N messages for context window.
"""

import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ev.memory.short_term")


class Message:
    """A single conversation message."""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: Optional[datetime] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_call_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self.role = role  # "system", "user", "assistant", "tool"
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id
        self.name = name  # For tool responses

    def to_api_format(self) -> Dict[str, Any]:
        """Convert to OpenAI API message format."""
        msg = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.name:
            msg["name"] = self.name
        return msg

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
        }

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Message(role={self.role}, content={preview})"


class ShortTermMemory:
    """
    In-memory conversation buffer using a deque.
    Automatically evicts oldest messages when capacity is reached.
    """

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: deque[Message] = deque(maxlen=max_messages)
        self._system_message: Optional[Message] = None
        logger.info(f"Short-term memory initialized (max {max_messages} messages)")

    def set_system_message(self, content: str):
        """Set the system message (always at the beginning, never evicted)."""
        self._system_message = Message(role="system", content=content)
        logger.debug("System message set")

    def add_user_message(self, content: str) -> Message:
        """Add a user message."""
        msg = Message(role="user", content=content)
        self._messages.append(msg)
        logger.debug(f"Added user message: {content[:50]}")
        return msg

    def add_assistant_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        """Add an assistant message."""
        msg = Message(role="assistant", content=content, tool_calls=tool_calls)
        self._messages.append(msg)
        logger.debug(f"Added assistant message: {content[:50]}")
        return msg

    def add_tool_result(
        self,
        tool_call_id: str,
        content: str,
        name: str = "",
    ) -> Message:
        """Add a tool execution result."""
        msg = Message(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            name=name,
        )
        self._messages.append(msg)
        logger.debug(f"Added tool result for {name}: {content[:50]}")
        return msg

    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in API format (system + conversation)."""
        messages = []
        if self._system_message:
            messages.append(self._system_message.to_api_format())
        for msg in self._messages:
            messages.append(msg.to_api_format())
        return messages

    def get_last_n(self, n: int) -> List[Message]:
        """Get the last N messages."""
        messages = list(self._messages)
        return messages[-n:]

    def get_last_user_message(self) -> Optional[Message]:
        """Get the most recent user message."""
        for msg in reversed(self._messages):
            if msg.role == "user":
                return msg
        return None

    def clear(self):
        """Clear all messages (keeps system message)."""
        self._messages.clear()
        logger.info("Short-term memory cleared")

    def get_conversation_text(self) -> str:
        """Get full conversation as plain text (for summarization)."""
        lines = []
        for msg in self._messages:
            role = msg.role.upper()
            lines.append(f"[{role}]: {msg.content}")
        return "\n".join(lines)

    @property
    def count(self) -> int:
        return len(self._messages)

    @property
    def is_empty(self) -> bool:
        return len(self._messages) == 0

    def __len__(self):
        return len(self._messages)

    def __repr__(self):
        return f"ShortTermMemory({self.count}/{self.max_messages} messages)"
