from uuid import uuid4

from app.api import routes_chat
from sg_core.service_metrics import reset_service_metrics


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, recorder, payload):
        self.recorder = recorder
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.recorder.append(
            {
                "url": url,
                "json": json,
                "headers": headers or {},
            }
        )
        if isinstance(self.payload, FakeResponse):
            return self.payload
        return FakeResponse(self.payload)


def test_vuln_chat_forwards_authenticated_tenant_and_realm(
    client,
    monkeypatch,
    tenant_header_matrix,
):
    calls = []
    monkeypatch.setattr(
        routes_chat.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(calls, {"response": "ok", "sources": [{"id": "src-1"}]}),
    )

    response = client.post(
        "/api/v1/chat/vuln",
        json={"query": "show fix groups"},
        headers=tenant_header_matrix,
    )

    assert response.status_code == 200
    assert response.json() == {"response": "ok", "sources": [{"id": "src-1"}]}
    assert calls[0]["url"].endswith("/api/v1/chat/vuln")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["json"]["tenant_id"] == "tenant-123"
    assert calls[0]["json"]["query"] == "show fix groups"


def test_vuln_chat_rejects_foreign_payload_tenant_override(
    client,
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        routes_chat.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(calls, {"response": "ok"}),
    )

    response = client.post(
        "/api/v1/chat/vuln",
        json={"tenant_id": str(uuid4()), "query": "show fix groups"},
        headers={"x-tenant-id": "foreign-tenant"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert calls == []


def test_dashboard_chat_forwards_authenticated_tenant_and_internal_token(
    client,
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        routes_chat.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(
            calls,
            {
                "response": "summary",
                "conversation_id": "conv-123",
                "sources": [{"id": "src-1"}],
                "suggestions": ["next"],
                "module": "dashboard",
            },
        ),
    )
    monkeypatch.setattr(routes_chat.settings, "INTERNAL_SERVICE_TOKEN", "internal-test-token", raising=False)

    response = client.post(
        "/api/v1/chat/dashboard",
        json={"query": "summarize posture", "tenant_id": "tenant-123"},
        headers={"x-tenant-id": "foreign-tenant", "x-realm": "realm-123"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "summary",
        "conversation_id": "conv-123",
        "suggestions": ["next"],
        "sources": [{"id": "src-1"}],
        "module": "dashboard",
        "answer_type": "knowledge_base",
        "source_kind": "knowledge_base",
        "retrieval_categories": [],
        "actions": [],
    }
    assert calls[0]["url"].endswith("/internal/llm/chat")
    assert calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"
    assert calls[0]["headers"]["X-Realm"] == "realm-123"
    assert calls[0]["headers"]["Authorization"] == "Bearer internal-test-token"
    assert calls[0]["json"]["tenant_id"] == "tenant-123"
    assert calls[0]["json"]["query"] == "summarize posture"


def test_dashboard_chat_routes_compliance_agent_with_live_context(
    client,
    monkeypatch,
):
    calls = []

    class FakeComplianceAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return False

        async def request(self, method, url, headers=None, params=None):
            calls.append({"method": method, "url": url, "headers": headers or {}, "params": params or {}})
            if url.endswith("/api/v1/compliance/coverage"):
                return FakeResponse(
                    {
                        "tenant_id": "tenant-123",
                        "items": [
                            {
                                "framework_id": "soc2",
                                "framework_name": "SOC 2",
                                "status": "needs_evidence",
                                "control_count": 2,
                                "controls": [
                                    {
                                        "control_id": "CC6.1",
                                        "gaps": [{"title": "MFA evidence missing", "severity": "high"}],
                                    }
                                ],
                            }
                        ],
                    }
                )
            if url.endswith("/api/v1/compliance/evidence"):
                return FakeResponse({"items": [{"id": "ev-1", "title": "MFA export"}], "count": 1})
            if url.endswith("/api/v1/reports/"):
                return FakeResponse({"items": [{"id": "report-1", "name": "SOC 2"}], "count": 1})
            if url.endswith("/api/v1/compliance/agent/recommendations"):
                return FakeResponse(
                    {
                        "items": [
                            {
                                "id": "rec-1",
                                "title": "Collect MFA evidence",
                                "recommendation_type": "create_evidence_collection_task",
                            }
                        ],
                        "count": 1,
                    }
                )
            return FakeResponse({}, status_code=404)

        async def post(self, url, json=None, headers=None):
            calls.append({"method": "POST", "url": url, "json": json, "headers": headers or {}})
            if url.endswith("/api/v1/audit/ai-activity"):
                return FakeResponse({"ok": True}, status_code=201)
            return FakeResponse(
                {
                    "response": "live compliance summary",
                    "conversation_id": "conv-123",
                    "module": "compliance",
                    "answer_type": "proposed_agent_action",
                    "source_kind": "proposed_agent_action",
                    "retrieval_categories": ["reports", "controls", "evidence", "gaps"],
                    "actions": [{"label": "Collect MFA evidence", "action": "review"}],
                }
            )

    monkeypatch.setattr(routes_chat.httpx, "AsyncClient", FakeComplianceAsyncClient)
    monkeypatch.setattr(routes_chat.settings, "INTERNAL_SERVICE_TOKEN", "internal-test-token", raising=False)

    response = client.post(
        "/api/v1/chat/dashboard",
        json={
            "query": "/compliance status",
            "tenant_id": "tenant-123",
            "active_agent": "compliance_agent",
            "context": {"dashboard_data": {"active_agent": "compliance_agent"}},
        },
        headers={
            "x-tenant-id": "foreign-tenant",
            "x-realm": "realm-123",
            "authorization": "Bearer user-token",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["module"] == "compliance"
    assert payload["answer_type"] == "proposed_agent_action"
    assert payload["retrieval_categories"] == ["reports", "controls", "evidence", "gaps"]
    assert payload["actions"][0]["label"] == "Collect MFA evidence"

    model_call = calls[-1]
    assert model_call["url"].endswith("/internal/llm/chat")
    assert model_call["json"]["module"] == "compliance"
    assert model_call["json"]["active_agent"] == "compliance_agent"
    live_context = model_call["json"]["context"]["compliance_live_context"]
    assert live_context["coverage"]["high_priority_gap_count"] == 1
    assert live_context["evidence"]["count"] == 1
    assert live_context["reports"]["count"] == 1

    audit_call = next(call for call in calls if call["url"].endswith("/api/v1/audit/ai-activity"))
    assert audit_call["json"]["action"] == "compliance_chat_context_accessed"
    assert audit_call["json"]["metadata"]["accessed_categories"] == ["evidence", "reports"]


def test_dashboard_chat_rejects_foreign_payload_tenant_override(
    client,
    monkeypatch,
):
    calls = []
    monkeypatch.setattr(
        routes_chat.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(calls, {"response": "summary"}),
    )

    response = client.post(
        "/api/v1/chat/dashboard",
        json={"tenant_id": str(uuid4()), "query": "summarize posture"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant ID mismatch. You can only access your own tenant's data."
    assert calls == []


def test_vuln_chat_records_success_metrics(
    client,
    monkeypatch,
):
    reset_service_metrics("api-gateway")
    calls = []
    monkeypatch.setattr(
        routes_chat.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(calls, {"response": "ok"}),
    )

    response = client.post(
        "/api/v1/chat/vuln",
        json={"query": "show fix groups"},
        headers={"x-tenant-id": "tenant-123"},
    )
    metrics_response = client.get("/metrics")

    assert response.status_code == 200
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["gateway_proxy_requests_total"]["series"][
        "outcome=success,route=chat_vuln,upstream=model_gateway"
    ] == 1


def test_dashboard_chat_records_upstream_error_metrics(
    client,
    monkeypatch,
):
    reset_service_metrics("api-gateway")
    calls = []
    monkeypatch.setattr(
        routes_chat.httpx,
        "AsyncClient",
        lambda *a, **k: FakeAsyncClient(
            calls,
            FakeResponse({"detail": "model gateway unavailable"}, status_code=503),
        ),
    )

    response = client.post(
        "/api/v1/chat/dashboard",
        json={"query": "summarize posture"},
        headers={"x-tenant-id": "tenant-123"},
    )
    metrics_response = client.get("/metrics")

    assert response.status_code == 503
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["gateway_proxy_requests_total"]["series"][
        "outcome=upstream_error,route=chat_dashboard,upstream=model_gateway"
    ] == 1
