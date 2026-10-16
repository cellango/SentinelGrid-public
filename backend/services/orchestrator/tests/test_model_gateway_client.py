import pytest

from app.services import model_gateway_client as model_gateway_client_module
from app.services.model_gateway_client import ModelGatewayClient


class _RaisingAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        raise model_gateway_client_module.httpx.RequestError("boom")


@pytest.mark.asyncio
async def test_generate_snapshot_analysis_returns_explicit_unavailable_state(monkeypatch):
    monkeypatch.setattr(model_gateway_client_module.httpx, "AsyncClient", _RaisingAsyncClient)
    client = ModelGatewayClient()

    result = await client.generate_snapshot_analysis(
        "tenant-123",
        {"summary": {"alerts_count": 5}},
    )

    assert result["posture"] == "Unknown"
    assert result["risk_level"] == "Unknown"
    assert result["analysis_available"] is False
    assert "unavailable" in result["summary"].lower()
    assert result["recommendations"] == []


def test_parse_ai_response_rejects_unstructured_snapshot_text():
    client = ModelGatewayClient()

    result = client._parse_ai_response(  # noqa: SLF001 - targeted regression for fallback semantics
        {"response": "Everything looks fine overall"},
        {"summary": {"alerts_count": 0}},
    )

    assert result["posture"] == "Unknown"
    assert result["analysis_available"] is False
    assert "unstructured response" in result["summary"].lower()


@pytest.mark.asyncio
async def test_analyze_phishing_email_returns_pending_manual_review_on_error(monkeypatch):
    monkeypatch.setattr(model_gateway_client_module.httpx, "AsyncClient", _RaisingAsyncClient)
    client = ModelGatewayClient()

    result = await client.analyze_phishing_email(
        "tenant-123",
        {
            "from_address": "alerts@example.com",
            "subject": "Verify your account",
            "text_body": "Click here now",
        },
    )

    assert result["classification"] == "pending"
    assert result["confidence"] == 0.0
    assert result["analysis_available"] is False
    assert "manual review" in result["reasoning"].lower()
    assert result["mitre_mapping"] == {}
    assert result["nist_mapping"] == {}
