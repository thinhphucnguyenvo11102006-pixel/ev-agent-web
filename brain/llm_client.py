"""
E.V. LLM Client — DeepSeek API integration via OpenAI-compatible SDK.
Supports function calling, streaming, and automatic retries.
"""

import json
import logging
import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError

import config

logger = logging.getLogger("ev.brain.llm")


class LLMResponse:
    """Represents a response from the LLM."""
    
    def __init__(
        self,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        finish_reason: str = "stop",
        model: str = "",
        usage: Optional[Dict[str, int]] = None,
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.finish_reason = finish_reason
        self.model = model
        self.usage = usage or {}

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    def __repr__(self):
        if self.has_tool_calls:
            tools = [tc.get("function", {}).get("name", "?") for tc in self.tool_calls]
            return f"LLMResponse(tools={tools})"
        return f"LLMResponse(content={self.content[:80]}...)"


class LLMClient:
    """
    DeepSeek API client using OpenAI-compatible SDK.
    
    Features:
    - Function calling (tool use)
    - Streaming responses
    - Automatic retries with backoff
    - Token usage tracking
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        name: str = "deepseek",
    ):
        self.name = name
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.model = model or config.DEEPSEEK_MODEL
        self.base_url = base_url or config.DEEPSEEK_BASE_URL

        if not self.api_key:
            logger.warning(f"No API key set for {self.name}. LLM calls will fail.")

        extra_headers = {}
        if self.base_url and "openrouter.ai" in self.base_url:
            extra_headers = {
                "HTTP-Referer": "https://github.com/ev-agent",
                "X-Title": "E.V. Agent",
            }

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers=extra_headers if extra_headers else None,
            timeout=15.0,
        )

        # Usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        retry_count: int = 3,
    ) -> LLMResponse:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts (role, content)
            tools: Optional tool definitions for function calling
            temperature: Creativity (0.0 - 2.0)
            max_tokens: Max tokens in response
            retry_count: Number of retries on failure
            
        Returns:
            LLMResponse with content and/or tool_calls
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        last_error = None
        for attempt in range(retry_count):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                self.total_requests += 1

                choice = response.choices[0]
                message = choice.message

                # Track usage
                if response.usage:
                    self.total_prompt_tokens += response.usage.prompt_tokens
                    self.total_completion_tokens += response.usage.completion_tokens

                # Parse tool calls
                tool_calls = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        args_str = tc.function.arguments
                        # Fix strict schema issues where LLM passes stringified numbers or booleans
                        try:
                            args_obj = json.loads(args_str)
                            if isinstance(args_obj, dict):
                                for k, v in list(args_obj.items()):
                                    if isinstance(v, str):
                                        if v.isdigit():
                                            args_obj[k] = int(v)
                                        elif v.lower() == "true":
                                            args_obj[k] = True
                                        elif v.lower() == "false":
                                            args_obj[k] = False
                                args_str = json.dumps(args_obj)
                        except Exception:
                            pass

                        tool_calls.append({
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": args_str,
                            },
                        })

                return LLMResponse(
                    content=message.content or "",
                    tool_calls=tool_calls,
                    finish_reason=choice.finish_reason or "stop",
                    model=response.model,
                    usage={
                        "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                        "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    },
                )

            except RateLimitError as e:
                last_error = e
                logger.warning(f"Rate limit / Quota hit on {self.name}, falling back immediately: {e}")
                break

            except APITimeoutError as e:
                last_error = e
                logger.warning(f"API timeout on {self.name} (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt >= 1:
                    break
                await asyncio.sleep(1)

            except APIError as e:
                last_error = e
                # Don't retry on 402 Insufficient Balance or 413 Request Too Large
                if hasattr(e, 'status_code') and e.status_code in (402, 413, 429):
                    logger.error(f"API status {e.status_code} for {self.name}, skipping retries.")
                    break
                logger.error(f"API error (attempt {attempt + 1}/{retry_count}): {e}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(1)

            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error: {e}")
                break

        raise ConnectionError(
            f"LLM request failed after {retry_count} attempts: {last_error}"
        )

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion response, yielding text chunks.
        
        Note: When tools are present and the model wants to call a tool,
        streaming will collect the full response and yield nothing (use chat() instead).
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self.client.chat.completions.create(**kwargs)
            
            collected_tool_calls = {}
            
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                # Handle text content
                if delta.content:
                    yield delta.content

                # Handle tool calls (collect fragments)
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in collected_tool_calls:
                            collected_tool_calls[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.id:
                            collected_tool_calls[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                collected_tool_calls[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                collected_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            self.total_requests += 1

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise

    def get_usage_stats(self) -> Dict[str, int]:
        """Get cumulative token usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }


def create_openrouter_client() -> Optional[LLMClient]:
    """Create an OpenRouter LLM client if API key is available."""
    if not config.OPENROUTER_API_KEY:
        return None
    return LLMClient(
        api_key=config.OPENROUTER_API_KEY,
        model=config.OPENROUTER_MODEL,
        base_url=config.OPENROUTER_BASE_URL,
        name="openrouter",
    )


def create_deepseek_client() -> LLMClient:
    """Create a DeepSeek LLM client with default config."""
    return LLMClient(
        api_key=config.DEEPSEEK_API_KEY,
        model=config.DEEPSEEK_MODEL,
        base_url=config.DEEPSEEK_BASE_URL,
        name="deepseek",
    )


def create_groq_client() -> Optional[LLMClient]:
    """Create a Groq LLM client if API key is available."""
    if not config.GROQ_API_KEY:
        return None
    return LLMClient(
        api_key=config.GROQ_API_KEY,
        model=config.GROQ_MODEL,
        base_url=config.GROQ_BASE_URL,
        name="groq",
    )


def create_gemini_client() -> Optional[LLMClient]:
    """Create a Gemini LLM client if API key is available."""
    if not config.GEMINI_API_KEY:
        return None
    return LLMClient(
        api_key=config.GEMINI_API_KEY,
        model=config.GEMINI_MODEL,
        base_url=config.GEMINI_BASE_URL,
        name="gemini",
    )
