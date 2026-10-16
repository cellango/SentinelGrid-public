from fastapi.testclient import TestClient

import app.main as iam_main
from sg_core.service_health import build_dependency_status
from sg_core.service_metrics import reset_service_metrics


class _NoopSeeder:
    async def seed_all(self):
        return None


async def _noop_stop_scheduler():
    return None


def _client(monkeypatch):
    monkeypatch.setattr(iam_main, "KeycloakSeeder", lambda: _NoopSeeder())
    monkeypatch.setattr(iam_main, "start_scheduler", lambda: None)
    monkeypatch.setattr(iam_main, "stop_scheduler", _noop_stop_scheduler)
    iam_main.seeding_result = None
    reset_service_metrics("iam-agent")
    return TestClient(iam_main.app)


def test_ready_returns_200_when_database_and_keycloak_are_healthy(monkeypatch):
    async def _healthy_db():
        return build_dependency_status("database", status="healthy", critical=True, detail="query_ok")

    async def _healthy_keycloak():
        return build_dependency_status("keycloak_admin", status="healthy", critical=True, detail="ok")

    monkeypatch.setattr(iam_main, "_probe_database_dependency", _healthy_db)
    monkeypatch.setattr(iam_main, "_probe_keycloak_dependency", _healthy_keycloak)

    with _client(monkeypatch) as client:
        response = client.get("/ready")
        metrics_response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["database"]["status"] == "healthy"
    assert payload["dependencies"]["keycloak_admin"]["status"] == "healthy"
    assert metrics_response.json()["counters"]["readiness_checks_total"]["series"]["outcome=ready"] == 1


def test_ready_returns_503_when_keycloak_admin_is_unhealthy(monkeypatch):
    async def _healthy_db():
        return build_dependency_status("database", status="healthy", critical=True, detail="query_ok")

    async def _broken_keycloak():
        return build_dependency_status("keycloak_admin", status="unhealthy", critical=True, detail="auth_failed")

    monkeypatch.setattr(iam_main, "_probe_database_dependency", _healthy_db)
    monkeypatch.setattr(iam_main, "_probe_keycloak_dependency", _broken_keycloak)

    with _client(monkeypatch) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["ready"] is False
    assert payload["status"] == "unhealthy"
    assert payload["dependencies"]["keycloak_admin"]["status"] == "unhealthy"


def test_metrics_prometheus_endpoint_returns_prometheus_text(monkeypatch):
    async def _healthy_db():
        return build_dependency_status("database", status="healthy", critical=True, detail="query_ok")

    async def _healthy_keycloak():
        return build_dependency_status("keycloak_admin", status="healthy", critical=True, detail="ok")

    monkeypatch.setattr(iam_main, "_probe_database_dependency", _healthy_db)
    monkeypatch.setattr(iam_main, "_probe_keycloak_dependency", _healthy_keycloak)

    with _client(monkeypatch) as client:
        ready_response = client.get("/ready")
        metrics_response = client.get("/metrics/prometheus")

    assert ready_response.status_code == 200
    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain")
    assert 'readiness_checks_total{outcome="ready",service="iam-agent"} 1.0' in metrics_response.text
