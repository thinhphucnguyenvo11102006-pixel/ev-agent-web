"""
E.V. ReAct Loop — Reasoning and Acting loop.
Implements the Thought → Action → Observation cycle.
"""

import json
import time
import logging
from typing import Any, Dict, List, Optional, Tuple

from brain.llm_client import LLMClient, LLMResponse
from tools.registry import ToolRegistry

import config

logger = logging.getLogger("ev.brain.react")


def _clean_repetitive_text(text: str) -> str:
    """Filter out repetitive lines/sentences produced by looping LLM responses."""
    if not text or len(text) < 100:
        return text
    lines = text.split('\n')
    seen = set()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) < 120:
            if stripped in seen:
                continue
            seen.add(stripped)
        cleaned.append(line)
    return '\n'.join(cleaned)


class ReActLoop:
    """
    ReAct (Reasoning and Acting) loop.
    
    Flow:
    1. LLM receives prompt → returns text OR tool_calls
    2. If tool_calls → execute tools → get observations
    3. Append observations → send back to LLM
    4. Repeat until LLM returns final text answer or max iterations reached
    """

    def __init__(self, llm_client: LLMClient, tool_registry: ToolRegistry):
        self.llm = llm_client
        self.tools = tool_registry
        self.max_iterations = config.MAX_REACT_ITERATIONS
        self._structured_memory = None

    def set_structured_memory(self, memory):
        """Set structured memory for tool usage logging."""
        self._structured_memory = memory

    async def run(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_thinking: Optional[callable] = None,
        on_tool_call: Optional[callable] = None,
        on_tool_result: Optional[callable] = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Run the ReAct loop.
        
        Args:
            messages: Current conversation messages
            tools: Tool schemas for function calling
            on_thinking: Callback when LLM starts thinking
            on_tool_call: Callback when a tool is being called
            on_tool_result: Callback when a tool returns result
            
        Returns:
            Tuple of (final_text_response, updated_messages)
        """
        current_messages = list(messages)
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1
            logger.info(f"ReAct iteration {iteration}/{self.max_iterations}")

            if on_thinking:
                await on_thinking(iteration)

            # Step 1: Ask LLM
            try:
                response = await self.llm.chat(
                    messages=current_messages,
                    tools=tools,
                    temperature=0.7,
                    max_tokens=2048,
                )
            except Exception as e:
                logger.error(f"LLM call failed in ReAct loop: {e}")
                return f"Xin lỗi, tôi gặp lỗi khi xử lý: {e}", current_messages

            # Step 2: Check if it's a final answer (no tool calls)
            if not response.has_tool_calls:
                logger.info(f"ReAct completed in {iteration} iteration(s)")
                return _clean_repetitive_text(response.content), current_messages

            # Step 3: Execute tool calls (parallelized if multiple)
            assistant_msg = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": response.tool_calls,
            }
            current_messages.append(assistant_msg)

            async def _exec_single_tool(tc):
                t_name = tc["function"]["name"]
                t_args = tc["function"]["arguments"]
                t_id = tc["id"]
                logger.info(f"Tool call: {t_name}({t_args[:100]})")

                if on_tool_call:
                    await on_tool_call(t_name, t_args)

                st = time.time()
                try:
                    res = await self.tools.dispatch(t_name, t_args)
                except Exception as ex:
                    res = f"Tool execution error: {ex}"
                    logger.error(f"Tool {t_name} failed: {ex}")

                dur_ms = int((time.time() - st) * 1000)

                if self._structured_memory:
                    try:
                        args_dict = json.loads(t_args) if t_args else {}
                    except json.JSONDecodeError:
                        args_dict = {"raw": t_args}
                    self._structured_memory.log_tool_usage(
                        tool_name=t_name,
                        arguments=args_dict,
                        result=res[:500],
                        success="Error" not in res,
                        duration_ms=dur_ms,
                    )

                if on_tool_result:
                    await on_tool_result(t_name, res)

                # Truncate nicely to save tokens (1200 chars limit)
                if len(res) > 1200:
                    res_formatted = res[:1200] + "\n\n[...Output truncated to save tokens...]"
                else:
                    res_formatted = res

                logger.info(f"Tool {t_name} completed in {dur_ms}ms")
                return {
                    "role": "tool",
                    "tool_call_id": t_id,
                    "content": res_formatted,
                }

            import asyncio
            tool_results = await asyncio.gather(*[_exec_single_tool(tc) for tc in response.tool_calls])
            current_messages.extend(tool_results)

        # Max iterations reached
        logger.warning(f"ReAct loop hit max iterations ({self.max_iterations})")
        
        # Ask LLM for a final summary
        current_messages.append({
            "role": "user",
            "content": "Hãy tổng hợp kết quả và trả lời ngắn gọn dựa trên thông tin đã thu thập.",
        })
        
        try:
            final_response = await self.llm.chat(
                messages=current_messages,
                tools=None,  # No tools for final summary
                temperature=0.7,
            )
            return final_response.content, current_messages
        except Exception as e:
            return f"Đã xử lý {iteration} bước nhưng gặp lỗi khi tổng hợp: {e}", current_messages
