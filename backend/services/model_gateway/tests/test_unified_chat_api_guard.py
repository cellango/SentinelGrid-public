import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.api import unified_chat


@pytest.fixture(autouse=True)
def disable_llm(monkeypatch):
    monkeypatch.setenv("ENABLE_LLM_CHAT", "false")


def _stub_token(monkeypatch, tenant_id="tenant-1", realm="demo"):
    def _fake_verify(token: str):
        return {"tenant_id": tenant_id, "realm": realm, "realm_name": realm}
    monkeypatch.setattr(unified_chat, "verify_token", _fake_verify)


def _stub_services(monkeypatch):
    monkeypatch.setattr(unified_chat.chat_service, "process_chat_query", lambda **kwargs: {
        "prompt": kwargs.get("query"),
        "sources": [],
        "module": "general",
        "confidence": 1.0,
    })
    monkeypatch.setattr(unified_chat.model_service, "generate_with_adapter", lambda **kwargs: {
        "text": "ok",
        "model_name": "test-model",
        "adapter_used": False,
        "adapter_version": None,
        "tokens": 0,
    })
    async def _noop(payload):
        return None
    monkeypatch.setattr(unified_chat.audit_client, "log_ai_event", _noop)


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_rejects_missing_token(client):
    resp = client.post("/internal/llm/chat", json={"query": "hi", "tenant_id": "t1"})
    assert resp.status_code in (401, 403)


def test_chat_rejects_tenant_mismatch(client, monkeypatch):
    _stub_token(monkeypatch, tenant_id="t1", realm="demo")
    _stub_services(monkeypatch)
    resp = client.post(
        "/internal/llm/chat",
        headers={"Authorization": "Bearer dummy"},
        json={"query": "hi", "tenant_id": "other"},
    )
    assert resp.status_code == 403
    assert "Tenant mismatch" in resp.text


def test_chat_rejects_missing_realm(client, monkeypatch):
    _stub_token(monkeypatch, tenant_id="t1", realm=None)
    _stub_services(monkeypatch)
    resp = client.post(
        "/internal/llm/chat",
        headers={"Authorization": "Bearer dummy"},
        json={"query": "hi", "tenant_id": "t1"},
    )
    assert resp.status_code == 400
    assert "realm is required" in resp.text


def test_chat_allows_valid_token_and_tenant(client, monkeypatch):
    _stub_token(monkeypatch, tenant_id="t1", realm="demo")
    _stub_services(monkeypatch)
    monkeypatch.setenv("ENABLE_LLM_CHAT", "true")
    resp = client.post(
        "/internal/llm/chat",
        headers={"Authorization": "Bearer dummy"},
        json={"query": "hi", "tenant_id": "t1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tenant_id"] == "t1"
    assert data["response"] == "ok"
