"""
E.V. Tool Registry — Central registry and dispatcher for all tools.
"""

import json
import time
import logging
from typing import Any, Callable, Dict, Optional
from pathlib import Path

logger = logging.getLogger("ev.tools.registry")


class Tool:
    """Represents a registered tool."""
    
    def __init__(self, name: str, handler: Callable, description: str = ""):
        self.name = name
        self.handler = handler
        self.description = description
        self.call_count = 0
        self.total_time_ms = 0

    async def execute(self, **kwargs) -> str:
        """Execute the tool and return result as string."""
        start = time.time()
        try:
            import inspect
            import asyncio

            # Filter kwargs to match function signature
            sig = inspect.signature(self.handler)
            has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if not has_kwargs:
                valid_keys = set(sig.parameters.keys())
                kwargs = {k: v for k, v in kwargs.items() if k in valid_keys}

            if asyncio.iscoroutinefunction(self.handler):
                result = await self.handler(**kwargs)
            else:
                result = self.handler(**kwargs)
            
            self.call_count += 1
            self.total_time_ms += int((time.time() - start) * 1000)
            
            return str(result) if result is not None else "Done."
        except Exception as e:
            logger.error(f"Tool {self.name} execution error: {e}")
            return f"Error: {str(e)}"


class ToolRegistry:
    """
    Central registry for all E.V. tools.
    Maps tool names to handlers and dispatches calls.
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._schemas: list = []
        logger.info("Tool registry initialized")

    def register(self, name: str, handler: Callable, description: str = ""):
        """Register a tool."""
        self._tools[name] = Tool(name, handler, description)
        logger.debug(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> list:
        """List all registered tool names."""
        return list(self._tools.keys())

    async def dispatch(self, tool_name: str, arguments: str) -> str:
        """
        Dispatch a tool call from the LLM.
        
        Args:
            tool_name: Name of the tool to call
            arguments: JSON string of arguments
            
        Returns:
            Tool execution result as string
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: Unknown tool '{tool_name}'. Available tools: {self.list_tools()}"

        try:
            kwargs = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError as e:
            return f"Error: Invalid arguments JSON: {e}"

        # Type normalization: LLMs (like Groq/Gemini) sometimes pass numbers/booleans as strings e.g. "num_results": "1"
        import inspect
        try:
            sig = inspect.signature(tool.handler)
            for param_name, param in sig.parameters.items():
                if param_name in kwargs:
                    val = kwargs[param_name]
                    target_type = param.annotation
                    if target_type == int and isinstance(val, str) and val.isdigit():
                        kwargs[param_name] = int(val)
                    elif target_type == float and isinstance(val, str):
                        try:
                            kwargs[param_name] = float(val)
                        except ValueError:
                            pass
                    elif target_type == bool and isinstance(val, str):
                        kwargs[param_name] = val.lower() in ("true", "1", "yes")
        except Exception as e:
            logger.debug(f"Type normalization error: {e}")

        logger.info(f"Dispatching tool: {tool_name}({json.dumps(kwargs, ensure_ascii=False)[:200]})")
        
        result = await tool.execute(**kwargs)
        logger.info(f"Tool {tool_name} result: {result[:200]}")
        
        return result

    def load_schemas(self, schema_path: Optional[str] = None) -> list:
        """Load tool schemas from JSON file."""
        if not schema_path:
            schema_path = str(
                Path(__file__).parent.parent / "brain" / "prompts" / "tool_schemas.json"
            )
        
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                self._schemas = json.load(f)
            logger.info(f"Loaded {len(self._schemas)} tool schemas")
            return self._schemas
        except Exception as e:
            logger.error(f"Failed to load tool schemas: {e}")
            return []

    def get_schemas(self) -> list:
        """Get tool schemas for LLM function calling."""
        if not self._schemas:
            self.load_schemas()
        return self._schemas

    def get_tool_info_list(self) -> list:
        """Get detailed tool list (name, description) for UI autocomplete."""
        info = []
        for s in self.get_schemas():
            fn = s.get("function", {})
            info.append({
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
            })
        return info


    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all tools."""
        return {
            name: {
                "calls": tool.call_count,
                "total_time_ms": tool.total_time_ms,
                "avg_time_ms": tool.total_time_ms // max(tool.call_count, 1),
            }
            for name, tool in self._tools.items()
        }
