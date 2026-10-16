"""LLM client wrapper for the SentinelGrid agent runtime.

Supports three backends (tried in order):
1. Internal model gateway (MODEL_GATEWAY_URL)
2. Anthropic API (ANTHROPIC_API_KEY)
3. OpenAI API (OPENAI_API_KEY)

All responses are normalised to a standard dict format regardless of provider.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Normalised response schema returned by ``chat()``:
# {
#     "content": str | None,
#     "tool_calls": [{"id": str, "name": str, "arguments": dict}],
#     "tokens": {"input": int, "output": int},
# }


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}


class AgentLLMClient:
    """Async LLM client with tool-use support."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        gateway_tool_call_support: bool | None = None,
    ) -> None:
        self._gateway_url = base_url or os.environ.get(
            "MODEL_GATEWAY_URL", "http://model_gateway:8000"
        )
        self._anthropic_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._openai_key = os.environ.get("OPENAI_API_KEY")
        self._model = model  # If None, each provider uses its own default
        self._gateway_tool_call_support = (
            gateway_tool_call_support
            if gateway_tool_call_support is not None
            else _env_flag("MODEL_GATEWAY_TOOL_CALL_SUPPORT", default=False)
        )
        self._client = httpx.AsyncClient(timeout=120.0)

    async def close(self) -> None:
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Send a chat completion request with optional tool use.

        Returns a normalised dict::

            {
                "content": str | None,
                "tool_calls": [{"id": str, "name": str, "arguments": dict}],
                "tokens": {"input": int, "output": int},
            }
        """
        last_gateway_error: Exception | None = None
        if tools and not self._gateway_tool_call_support:
            last_gateway_error = self._gateway_tool_call_disabled_error(tools)
            logger.debug(
                "Skipping Model Gateway for tool-using request because tool calling is disabled"
            )
        else:
            # Try model gateway first
            try:
                return await self._chat_gateway(messages, tools, temperature)
            except Exception as exc:
                last_gateway_error = exc
                logger.debug("Model gateway unavailable (%s), falling back", exc)

        # Anthropic fallback
        if self._anthropic_key:
            try:
                return await self._chat_anthropic(messages, tools, temperature)
            except Exception as exc:
                logger.debug("Anthropic API failed (%s), falling back", exc)

        # OpenAI fallback
        if self._openai_key:
            return await self._chat_openai(messages, tools, temperature)

        detail = (
            f" Last Model Gateway error: {last_gateway_error}"
            if last_gateway_error is not None
            else ""
        )
        message = (
            "No tool-capable LLM backend available. Set MODEL_GATEWAY_TOOL_CALL_SUPPORT=true "
            "when the active Model Gateway provider supports tool calling, or set "
            "ANTHROPIC_API_KEY or OPENAI_API_KEY."
            if tools
            else "No LLM backend available. Set MODEL_GATEWAY_URL, ANTHROPIC_API_KEY, or OPENAI_API_KEY."
        )
        raise RuntimeError(message + detail)

    # ------------------------------------------------------------------
    # Model gateway (OpenAI-compatible /v1/chat/completions)
    # ------------------------------------------------------------------

    async def _chat_gateway(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model or "default",
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        resp = await self._client.post(
            f"{self._gateway_url}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        metadata = data.get("metadata") or {}
        if tools and metadata.get("tool_call_support") is False:
            raise self._gateway_tool_call_disabled_error(tools)
        return self._parse_openai_response(data)

    # ------------------------------------------------------------------
    # Anthropic Messages API
    # ------------------------------------------------------------------

    async def _chat_anthropic(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float,
    ) -> dict[str, Any]:
        # Extract system prompt from messages
        system_text = ""
        user_messages: list[dict] = []
        for msg in messages:
            if msg.get("role") == "system":
                system_text = msg["content"]
            else:
                user_messages.append(msg)

        payload: dict[str, Any] = {
            "model": self._model or "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": self._convert_messages_to_anthropic(user_messages),
        }
        if system_text:
            payload["system"] = system_text
        if tools:
            payload["tools"] = self._convert_tools_to_anthropic(tools)

        resp = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={
                "x-api-key": self._anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_anthropic_response(data)

    # ------------------------------------------------------------------
    # OpenAI API
    # ------------------------------------------------------------------

    async def _chat_openai(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        temperature: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self._model or "gpt-4o",
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools

        resp = await self._client.post(
            "https://api.openai.com/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {self._openai_key}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return self._parse_openai_response(data)

    # ------------------------------------------------------------------
    # Response parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _tool_name(tool: dict[str, Any]) -> str:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if isinstance(fn, dict) and fn.get("name"):
            return str(fn["name"])
        return str(tool.get("name", "unknown")) if isinstance(tool, dict) else "unknown"

    @classmethod
    def _gateway_tool_call_disabled_error(cls, tools: list[dict[str, Any]]) -> RuntimeError:
        return RuntimeError(
            json.dumps(
                {
                    "backend": "model_gateway",
                    "endpoint": "/v1/chat/completions",
                    "tool_call_support": False,
                    "tools_requested": [cls._tool_name(tool) for tool in tools],
                    "message": "Model Gateway content completions are reachable, but tool calling is not enabled.",
                }
            )
        )

    @staticmethod
    def _parse_openai_response(data: dict) -> dict[str, Any]:
        choice = data["choices"][0]
        msg = choice["message"]
        tool_calls: list[dict] = []
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                args = tc["function"].get("arguments", "{}")
                tool_calls.append(
                    {
                        "id": tc["id"],
                        "name": tc["function"]["name"],
                        "arguments": json.loads(args) if isinstance(args, str) else args,
                    }
                )
        usage = data.get("usage", {})
        return {
            "content": msg.get("content"),
            "tool_calls": tool_calls,
            "tokens": {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            },
        }

    @staticmethod
    def _parse_anthropic_response(data: dict) -> dict[str, Any]:
        content_text: str | None = None
        tool_calls: list[dict] = []

        for block in data.get("content", []):
            if block["type"] == "text":
                content_text = block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append(
                    {
                        "id": block["id"],
                        "name": block["name"],
                        "arguments": block.get("input", {}),
                    }
                )

        usage = data.get("usage", {})
        return {
            "content": content_text,
            "tool_calls": tool_calls,
            "tokens": {
                "input": usage.get("input_tokens", 0),
                "output": usage.get("output_tokens", 0),
            },
        }

    # ------------------------------------------------------------------
    # Format converters
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_tools_to_anthropic(tools: list[dict]) -> list[dict]:
        """Convert OpenAI-style tool defs to Anthropic format."""
        anthropic_tools: list[dict] = []
        for tool in tools:
            fn = tool.get("function", tool)
            anthropic_tools.append(
                {
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return anthropic_tools

    @staticmethod
    def _convert_messages_to_anthropic(messages: list[dict]) -> list[dict]:
        """Convert OpenAI-style messages to Anthropic Messages format.

        Handles tool_calls (assistant) and tool results transparently.
        """
        converted: list[dict] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant" and msg.get("tool_calls"):
                # Anthropic expects content blocks for tool use
                blocks: list[dict] = []
                if msg.get("content"):
                    blocks.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"] if "function" in tc else tc["name"],
                            "input": (
                                json.loads(tc["function"]["arguments"])
                                if "function" in tc and isinstance(tc["function"]["arguments"], str)
                                else tc.get("arguments", tc.get("function", {}).get("arguments", {}))
                            ),
                        }
                    )
                converted.append({"role": "assistant", "content": blocks})
            elif role == "tool":
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg.get("tool_call_id", ""),
                                "content": msg.get("content", ""),
                            }
                        ],
                    }
                )
            else:
                converted.append({"role": role, "content": msg.get("content", "")})
        return converted
