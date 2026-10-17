import app.main as gateway_main

from sg_core.service_health import build_dependency_status
from sg_core.service_metrics import reset_service_metrics
from unittest.mock import patch
from fastapi import HTTPException


async def _healthy_probe(name: str, url: str, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="ok", url=url)


def test_metrics_capture_readiness_outcome(client, monkeypatch):
    reset_service_metrics("api-gateway")
    monkeypatch.setattr(gateway_main, "probe_http_dependency", _healthy_probe)

    ready_response = client.get("/ready")
    metrics_response = client.get("/metrics")

    assert ready_response.status_code == 200
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["readiness_checks_total"]["total"] == 1
    assert payload["counters"]["readiness_checks_total"]["series"]["outcome=ready"] == 1
    assert payload["gauges"]["service_ready"]["__base__"] == 1
    assert payload["last_readiness"]["ready"] is True


def test_metrics_capture_missing_authorization_failures(auth_client):
    reset_service_metrics("api-gateway")

    response = auth_client.get("/api/v1/alerts/")
    metrics_response = auth_client.get("/metrics")

    assert response.status_code == 401
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["auth_failures_total"]["series"]["reason=missing_authorization_token"] == 1


def test_metrics_prometheus_endpoint_exposes_runtime_series(auth_client):
    reset_service_metrics("api-gateway")

    response = auth_client.get("/api/v1/alerts/")
    metrics_response = auth_client.get("/metrics/prometheus")

    assert response.status_code == 401
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
    assert 'auth_failures_total{reason="missing_authorization_token",service="api-gateway"} 1.0' in metrics_response.text


def test_metrics_capture_token_validation_failures(auth_client):
    reset_service_metrics("api-gateway")

    with patch("sg_core.security.verify_iam_token", side_effect=HTTPException(401, "Invalid token")):
        response = auth_client.get(
            "/api/v1/alerts/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        metrics_response = auth_client.get("/metrics")

    assert response.status_code == 401
    assert metrics_response.status_code == 200
    payload = metrics_response.json()
    assert payload["counters"]["auth_failures_total"]["series"]["reason=invalid_token"] == 1
    assert payload["counters"]["token_validation_failures_total"]["series"]["reason=invalid_token"] == 1


def test_metrics_prometheus_endpoint_exposes_token_validation_failures(auth_client):
    reset_service_metrics("api-gateway")

    with patch("sg_core.security.verify_iam_token", side_effect=HTTPException(401, "Invalid token")):
        response = auth_client.get(
            "/api/v1/alerts/",
            headers={"Authorization": "Bearer invalid-token"},
        )
        metrics_response = auth_client.get("/metrics/prometheus")

    assert response.status_code == 401
    assert metrics_response.status_code == 200
    assert 'token_validation_failures_total{reason="invalid_token",service="api-gateway"} 1.0' in metrics_response.text
