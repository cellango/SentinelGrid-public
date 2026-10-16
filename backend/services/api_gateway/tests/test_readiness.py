import app.main as gateway_main

from sg_core.service_health import build_dependency_status


async def _healthy_probe(name: str, url: str, *, critical: bool, **kwargs):
    return build_dependency_status(name, status="healthy", critical=critical, detail="ok", url=url)


def test_ready_returns_200_when_critical_dependencies_are_healthy(client, monkeypatch):
    monkeypatch.setattr(gateway_main, "probe_http_dependency", _healthy_probe)

    response = client.get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready"] is True
    assert payload["status"] == "healthy"
    assert payload["dependencies"]["iam_agent"]["status"] == "healthy"
    assert payload["dependencies"]["orchestrator"]["status"] == "healthy"


def test_ready_returns_503_when_a_critical_dependency_is_unhealthy(client, monkeypatch):
    async def _probe(name: str, url: str, *, critical: bool, **kwargs):
        status = "unhealthy" if name == "orchestrator" else "healthy"
        detail = "timeout" if status == "unhealthy" else "ok"
        return build_dependency_status(name, status=status, critical=critical, detail=detail, url=url)

    monkeypatch.setattr(gateway_main, "probe_http_dependency", _probe)

    response = client.get("/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["ready"] is False
    assert payload["status"] == "unhealthy"
    assert payload["dependencies"]["orchestrator"]["status"] == "unhealthy"
