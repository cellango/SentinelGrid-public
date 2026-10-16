from fastapi.testclient import TestClient

from app.main import app


def test_openai_compatible_chat_completion_accepts_content_payload(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_CHAT", "false")
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        headers={"X-Tenant-ID": "tenant-1"},
        json={
            "model": "sentinelgrid-default",
            "messages": [
                {"role": "system", "content": "You are concise."},
                {"role": "user", "content": "Summarize this alert."},
            ],
            "temperature": 0.1,
            "max_tokens": 64,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["object"] == "chat.completion"
    assert payload["choices"][0]["message"]["role"] == "assistant"
    assert payload["choices"][0]["message"]["content"]
    assert payload["usage"]["total_tokens"] >= payload["usage"]["completion_tokens"]
    assert payload["metadata"]["tenant_id"] == "tenant-1"
    assert payload["metadata"]["tool_call_support"] is False


def test_openai_compatible_chat_completion_reports_tool_call_support_false(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_CHAT", "false")
    monkeypatch.delenv("MODEL_GATEWAY_TOOL_CALL_SUPPORT", raising=False)
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "sentinelgrid-default",
            "messages": [{"role": "user", "content": "Use a tool."}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "search_logs",
                        "description": "Search logs",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "tool_choice": "auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["tools_requested"] is True
    assert payload["metadata"]["tool_call_support"] is False


def test_openai_compatible_chat_completion_reports_tool_call_support_true(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_CHAT", "false")
    monkeypatch.setenv("MODEL_GATEWAY_TOOL_CALL_SUPPORT", "true")
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        headers={"X-Tenant-ID": "tenant-1"},
        json={
            "model": "sentinelgrid-default",
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Search logs."}]}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "search_logs",
                        "description": "Search logs",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "tool_choice": "auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["tenant_id"] == "tenant-1"
    assert payload["metadata"]["tools_requested"] is True
    assert payload["metadata"]["tool_call_support"] is True
    assert payload["choices"][0]["message"]["content"] == "Search logs."
