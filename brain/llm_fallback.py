"""
E.V. LLM Fallback — Multi-provider fallback chain.
Tries DeepSeek → Groq → Gemini, auto-switching on failure.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional

from brain.llm_client import (
    LLMClient,
    LLMResponse,
    create_openrouter_client,
    create_deepseek_client,
    create_groq_client,
    create_gemini_client,
)

logger = logging.getLogger("ev.brain.fallback")


class LLMFallbackChain:
    """
    Multi-LLM fallback chain.
    Tries providers in order, auto-switching on failure/timeout.
    """

    def __init__(self):
        self.clients: List[LLMClient] = []
        self.active_index = 0
        self._setup_clients()

    def _setup_clients(self):
        """Initialize available LLM clients (OpenRouter → Groq → Gemini → DeepSeek)."""
        # Primary / High-capacity: OpenRouter
        try:
            openrouter = create_openrouter_client()
            if openrouter:
                self.clients.append(openrouter)
                logger.info(f"✓ OpenRouter client ready ({openrouter.model})")
        except Exception as e:
            logger.warning(f"✗ OpenRouter client failed: {e}")

        # Fallback 1: Groq (ultra-fast, sub-second response)
        try:
            groq = create_groq_client()
            if groq:
                self.clients.append(groq)
                logger.info(f"✓ Groq client ready ({groq.model})")
        except Exception as e:
            logger.warning(f"✗ Groq client failed: {e}")

        # Fallback 2: Gemini
        try:
            gemini = create_gemini_client()
            if gemini:
                self.clients.append(gemini)
                logger.info(f"✓ Gemini client ready ({gemini.model})")
        except Exception as e:
            logger.warning(f"✗ Gemini client failed: {e}")

        # Fallback 3: DeepSeek
        try:
            deepseek = create_deepseek_client()
            if deepseek and deepseek.api_key:
                self.clients.append(deepseek)
                logger.info(f"✓ DeepSeek client ready ({deepseek.model})")
        except Exception as e:
            logger.warning(f"✗ DeepSeek client failed: {e}")

        if not self.clients:
            raise RuntimeError("No LLM clients available. Please set at least one API key.")

        logger.info(f"Fallback chain: {' → '.join(c.name for c in self.clients)}")

    @property
    def active_client(self) -> LLMClient:
        """Get the currently active client."""
        return self.clients[self.active_index]

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Send chat request with automatic fallback.
        Tries each provider in sequence until one succeeds.
        """
        errors = []

        for i, client in enumerate(self.clients):
            try:
                logger.debug(f"Trying {client.name}...")
                response = await client.chat(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    retry_count=2 if i < len(self.clients) - 1 else 3,
                )
                
                # If we fell back and succeeded, log it
                if i != self.active_index:
                    logger.info(f"Fell back from {self.active_client.name} to {client.name}")
                    self.active_index = i

                return response

            except Exception as e:
                errors.append(f"{client.name}: {e}")
                logger.warning(f"{client.name} failed: {e}")
                continue

        # All providers failed
        error_summary = " | ".join(errors)
        raise ConnectionError(f"All LLM providers failed: {error_summary}")

    async def chat_stream(self, messages, tools=None, temperature=0.7, max_tokens=2048):
        """Stream chat with automatic fallback across providers."""
        for i in range(len(self.clients)):
            idx = (self.active_index + i) % len(self.clients)
            client = self.clients[idx]
            try:
                logger.debug(f"Streaming with {client.name}...")
                async for chunk in client.chat_stream(
                    messages=messages,
                    tools=tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
                self.active_index = idx
                return
            except Exception as e:
                logger.warning(f"Streaming failed on {client.name}: {e}")
                continue

        # Fallback to non-streaming chat across providers
        response = await self.chat(messages, tools, temperature, max_tokens)
        if response.content:
            yield response.content


    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers."""
        return {
            "active": self.active_client.name,
            "providers": [
                {
                    "name": c.name,
                    "model": c.model,
                    "active": i == self.active_index,
                    "usage": c.get_usage_stats(),
                }
                for i, c in enumerate(self.clients)
            ],
        }
