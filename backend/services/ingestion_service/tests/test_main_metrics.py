from fastapi.testclient import TestClient

import app.main as ingestion_main
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


class DummyBatchProcessor:
    def queue_summary(self):
        return {
            "pending_events": 9,
            "tenants_with_pending_batches": 2,
            "active_batch_timers": 2,
            "max_batch_depth": 5,
        }

    def embedding_summary(self):
        return {
            "tenants_with_activity": 1,
            "attempted_total": 6,
            "success_total": 4,
            "failed_total": 2,
            "cap_used_total": 6,
            "cap_limit_per_tenant": 200,
        }


def test_health_exposes_aggregate_queue_and_embedding_summary(monkeypatch):
    reset_service_metrics("ingestion-service")
    monkeypatch.setattr(ingestion_main, "get_batch_processor", lambda: DummyBatchProcessor())

    client = TestClient(ingestion_main.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "ingestion-service",
        "version": ingestion_main.settings.VERSION,
        "queue": {
            "pending_events": 9,
            "tenants_with_pending_batches": 2,
            "active_batch_timers": 2,
            "max_batch_depth": 5,
        },
        "embeddings": {
            "tenants_with_activity": 1,
            "attempted_total": 6,
            "success_total": 4,
            "failed_total": 2,
            "cap_used_total": 6,
            "cap_limit_per_tenant": 200,
        },
    }
    assert "tenant-a" not in response.text


def test_metrics_endpoint_returns_runtime_snapshot():
    reset_service_metrics("ingestion-service")
    runtime_metrics = get_service_metrics("ingestion-service")
    runtime_metrics.increment_counter("ingestion_batches_received_total", outcome="success")
    runtime_metrics.set_gauge("ingestion_pending_events", 3)

    client = TestClient(ingestion_main.app)
    response = client.get("/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "ingestion-service"
    assert payload["counters"]["ingestion_batches_received_total"]["series"]["outcome=success"] == 1
    assert payload["gauges"]["ingestion_pending_events"]["__base__"] == 3


def test_metrics_prometheus_endpoint_returns_prometheus_text():
    reset_service_metrics("ingestion-service")
    runtime_metrics = get_service_metrics("ingestion-service")
    runtime_metrics.increment_counter("ingestion_batches_received_total", outcome="success")
    runtime_metrics.set_gauge("ingestion_pending_events", 3)

    client = TestClient(ingestion_main.app)
    response = client.get("/metrics/prometheus")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'ingestion_batches_received_total{outcome="success",service="ingestion-service"} 1.0' in response.text
    assert 'ingestion_pending_events{service="ingestion-service"} 3' in response.text
