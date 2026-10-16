"""OpenAI-compatible chat completion endpoint for internal agent clients."""

from __future__ import annotations

import os
import time
import uuid
from typing import Any

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.model_service import ModelService

router = APIRouter(prefix="/v1", tags=["openai-compatible"])
model_service = ModelService()


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="default")
    messages: list[ChatMessage]
    temperature: float = Field(default=0.1)
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any | None = None
    max_tokens: int | None = Field(default=None, ge=1)


@router.post("/chat/completions")
def chat_completions(
    request: ChatCompletionRequest,
    tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
) -> dict[str, Any]:
    """Accept an OpenAI-style chat payload and return an OpenAI-style response.

    V1 supports content completions. Tool-call metadata is explicit so agent
    clients can fall back to providers that support function/tool calling.
    """
    prompt = _messages_to_prompt(request.messages)
    use_llm = os.getenv("ENABLE_LLM_CHAT", "false").lower() in {"1", "true", "yes"}
    tool_call_support = _tool_call_support_enabled()
    effective_tenant_id = tenant_id or "internal-agent-runtime"

    if use_llm:
        result = model_service.generate_with_adapter(
            tenant_id=effective_tenant_id,
            prompt=prompt,
            max_tokens=request.max_tokens or int(os.getenv("CHAT_MAX_TOKENS", "512")),
            temperature=request.temperature,
        )
        content = str(result.get("text") or "").strip() or "No response generated."
        completion_tokens = int(result.get("tokens") or _estimate_tokens(content))
        model_name = str(result.get("model_name") or request.model or settings.BASE_MODEL_NAME)
    else:
        content = _fallback_completion(request.messages, tool_call_support=tool_call_support)
        completion_tokens = _estimate_tokens(content)
        model_name = request.model or "fast-fallback"

    prompt_tokens = _estimate_tokens(prompt)
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "metadata": {
            "tenant_id": effective_tenant_id,
            "tool_call_support": tool_call_support,
            "tools_requested": bool(request.tools),
            "tool_choice": request.tool_choice,
        },
    }


def _tool_call_support_enabled() -> bool:
    return os.getenv("MODEL_GATEWAY_TOOL_CALL_SUPPORT", "false").lower() in {
        "1",
        "true",
        "yes",
        "on",
        "enabled",
    }


def _messages_to_prompt(messages: list[ChatMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        content = _message_content_to_text(message.content)
        if message.tool_calls:
            content = f"{content}\nTool calls requested: {message.tool_calls}".strip()
        if content:
            lines.append(f"{message.role}: {content}")
    return "\n".join(lines).strip()


def _message_content_to_text(content: str | list[dict[str, Any]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text" and block.get("text"):
            parts.append(str(block["text"]))
        elif block.get("content"):
            parts.append(str(block["content"]))
    return "\n".join(parts)


def _fallback_completion(
    messages: list[ChatMessage],
    *,
    tool_call_support: bool,
) -> str:
    last_user = next(
        (
            _message_content_to_text(message.content)
            for message in reversed(messages)
            if message.role == "user"
        ),
        "",
    ).strip()
    if not tool_call_support:
        return (
            "Model Gateway content completion is available, but tool calling is not "
            f"enabled for this provider. Last user request: {last_user[:500]}"
        ).strip()
    return last_user[:1000] or "No user message supplied."


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4) if text else 0
