from __future__ import annotations

import json

import pytest

from sg_agent_runtime import llm_client


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse):
        self.response = response
        self.posts: list[dict] = []

    async def post(self, url: str, *, json: dict, **kwargs):
        self.posts.append({"url": url, "json": json, **kwargs})
        return self.response

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_agent_llm_client_parses_model_gateway_content_response(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_GATEWAY_TOOL_CALL_SUPPORT", raising=False)
    fake = _FakeAsyncClient(
        _FakeResponse(
            {
                "choices": [{"message": {"role": "assistant", "content": "content response"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 3},
                "metadata": {"tool_call_support": False},
            }
        )
    )
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", lambda *args, **kwargs: fake)
    client = llm_client.AgentLLMClient(base_url="http://model-gateway")

    result = await client.chat([{"role": "user", "content": "hello"}])

    assert fake.posts[0]["url"] == "http://model-gateway/v1/chat/completions"
    assert result["content"] == "content response"
    assert result["tool_calls"] == []
    assert result["tokens"] == {"input": 4, "output": 3}


@pytest.mark.asyncio
async def test_agent_llm_client_parses_model_gateway_tool_call_response(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("MODEL_GATEWAY_TOOL_CALL_SUPPORT", "true")
    fake = _FakeAsyncClient(
        _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "search_logs",
                                        "arguments": json.dumps({"query": "mfa"}),
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 2},
                "metadata": {"tool_call_support": True},
            }
        )
    )
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", lambda *args, **kwargs: fake)
    client = llm_client.AgentLLMClient(base_url="http://model-gateway")

    result = await client.chat(
        [{"role": "user", "content": "search"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_logs",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    assert result["tool_calls"] == [
        {"id": "call-1", "name": "search_logs", "arguments": {"query": "mfa"}}
    ]
    assert fake.posts[0]["json"]["tools"][0]["function"]["name"] == "search_logs"


@pytest.mark.asyncio
async def test_agent_llm_client_skips_gateway_for_tools_when_tool_calls_disabled(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_GATEWAY_TOOL_CALL_SUPPORT", raising=False)
    fake = _FakeAsyncClient(
        _FakeResponse(
            {
                "choices": [{"message": {"role": "assistant", "content": "should not be used"}}],
                "metadata": {"tool_call_support": False},
            }
        )
    )
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", lambda *args, **kwargs: fake)
    client = llm_client.AgentLLMClient(base_url="http://model-gateway")

    with pytest.raises(RuntimeError, match="tool calling is not enabled"):
        await client.chat(
            [{"role": "user", "content": "search"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "search_logs",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        )

    assert fake.posts == []


@pytest.mark.asyncio
async def test_agent_llm_client_rejects_gateway_without_tool_call_support(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    fake = _FakeAsyncClient(
        _FakeResponse(
            {
                "choices": [{"message": {"role": "assistant", "content": "fallback content"}}],
                "metadata": {"tool_call_support": False},
            }
        )
    )
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", lambda *args, **kwargs: fake)
    client = llm_client.AgentLLMClient(base_url="http://model-gateway")

    with pytest.raises(RuntimeError, match="tool calling is not enabled"):
        await client._chat_gateway(
            [{"role": "user", "content": "search"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "search_logs",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            temperature=0.1,
        )
