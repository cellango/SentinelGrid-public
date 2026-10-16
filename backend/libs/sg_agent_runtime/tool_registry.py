"""Tool registry for the SentinelGrid agent runtime.

Wraps existing MCP tools and service clients into a uniform interface
that agents can invoke via the LLM tool-use loop.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from .models import ToolDefinition

logger = logging.getLogger(__name__)

# Type alias for async tool handlers: (params) -> result dict
ToolHandler = Callable[..., Coroutine[Any, Any, dict[str, Any]]]


class ToolRegistry:
    """Central registry of tools available to agents."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, tool_def: ToolDefinition, handler: ToolHandler) -> None:
        """Register a tool with its async handler function."""
        if tool_def.name in self._tools:
            logger.warning("Overwriting existing tool registration: %s", tool_def.name)
        self._tools[tool_def.name] = tool_def
        self._handlers[tool_def.name] = handler
        logger.debug("Registered tool: %s", tool_def.name)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> tuple[ToolDefinition, ToolHandler]:
        """Return (definition, handler) for *name*. Raises KeyError if missing."""
        if name not in self._tools:
            raise KeyError(f"Tool not registered: {name}")
        return self._tools[name], self._handlers[name]

    def list_tools(self, agent_tools: list[str] | None = None) -> list[ToolDefinition]:
        """List tools, optionally filtered to those in *agent_tools*."""
        if agent_tools is None:
            return list(self._tools.values())
        return [
            self._tools[name]
            for name in agent_tools
            if name in self._tools
        ]

    def names(self) -> set[str]:
        """Return the registered tool names."""
        return set(self._tools)

    # ------------------------------------------------------------------
    # LLM integration
    # ------------------------------------------------------------------

    def to_llm_tools(self, agent_tools: list[str] | None = None) -> list[dict[str, Any]]:
        """Convert registered tools to the Anthropic / OpenAI tool-use format.

        Returns a list compatible with both providers.  The outer structure
        uses the OpenAI ``{"type": "function", "function": {…}}`` envelope
        which the ``AgentLLMClient`` adapts per-provider as needed.
        """
        defs = self.list_tools(agent_tools)
        tools: list[dict[str, Any]] = []
        for td in defs:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": td.name,
                        "description": td.description,
                        "parameters": td.parameters or {"type": "object", "properties": {}},
                    },
                }
            )
        return tools
