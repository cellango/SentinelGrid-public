"""Tests for anomaly detection and automated response."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from uuid import uuid4
from fastapi import FastAPI
from app.api import anomalies
from app.api.request_context import RequestContext, get_current_request_context
from app.services.anomaly_detection import AnomalyDetectionService


@pytest.fixture
def caller():
    return RequestContext(uuid4(), str(uuid4()), ("TENANT_ADMIN",))


@pytest.fixture
def client(caller):
    app = FastAPI()
    app.include_router(anomalies.router)
    app.dependency_overrides[get_current_request_context] = lambda: caller
    with TestClient(app) as client:
        yield client


def test_list_anomalies(client, caller, monkeypatch):
    service = Mock()
    service.detect_anomalies = AsyncMock(return_value=[])
    service.store.list_anomalies.return_value = {"items": [], "total": 0}
    monkeypatch.setattr(anomalies, "AnomalyDetectionService", lambda: service)
    result = client.get("/api/v1/security/anomalies")
    assert result.status_code == 200 and result.json()["items"] == []
    assert service.detect_anomalies.call_args.kwargs["tenant_id"] == str(
        caller.tenant_id
    )
    assert service.store.list_anomalies.call_args.kwargs["tenant_id"] == str(
        caller.tenant_id
    )


def test_acknowledge_anomaly(client, caller, monkeypatch):
    store = Mock()
    store.acknowledge.return_value = True
    monkeypatch.setattr(anomalies, "AnomalyStore", lambda: store)
    result = client.post(
        "/api/v1/security/anomalies/synthetic-anomaly/acknowledge",
        json={"notes": "Synthetic"},
    )
    assert result.status_code == 200
    assert store.acknowledge.call_args.kwargs == {
        "tenant_id": str(caller.tenant_id),
        "anomaly_id": "synthetic-anomaly",
        "actor": caller.user_id,
    }


def test_trigger_anomaly_detection(client, caller, monkeypatch):
    service = Mock()
    service.detect_anomalies = AsyncMock(
        return_value=[
            {
                "anomaly_type": "impossible_travel",
                "severity": "critical",
                "risk_score": 99,
            }
        ]
    )
    monkeypatch.setattr(anomalies, "AnomalyDetectionService", lambda: service)
    result = client.post("/api/v1/security/anomalies/detect")
    assert result.status_code == 200
    assert result.json()["anomalies_detected"] == 1
    assert (
        result.json()["actions_taken"] == []
        and result.json()["response_status"] == "blocked"
    )
    assert service.detect_anomalies.call_args.kwargs["tenant_id"] == str(
        caller.tenant_id
    )


def test_impossible_travel_detection():
    """Detector flags geo jumps that exceed speed threshold."""
    service = AnomalyDetectionService(store=Mock())
    now = datetime.utcnow()
    events = [
        {
            "user_id": "u1",
            "timestamp": now - timedelta(hours=2),
            "success": True,
            "ip_address": "1.1.1.1",
            "user_agent": "ua",
            "device_id": None,
            "geo": {
                "lat": 40.7128,
                "lon": -74.0060,
                "city": "New York",
                "country": "US",
            },
        },
        {
            "user_id": "u1",
            "timestamp": now - timedelta(minutes=30),
            "success": True,
            "ip_address": "2.2.2.2",
            "user_agent": "ua",
            "device_id": None,
            "geo": {"lat": 51.5074, "lon": -0.1278, "city": "London", "country": "UK"},
        },
    ]
    anomalies = service._detect_impossible_travel(events)
    assert anomalies, "Expected impossible travel anomaly"
    assert anomalies[0]["anomaly_type"] == "impossible_travel"


def test_failed_login_burst_detection():
    """Detector flags failed login spikes in a short window."""
    service = AnomalyDetectionService(store=Mock())
    base = datetime.utcnow()
    failures = [
        {"timestamp": base - timedelta(minutes=4), "success": False},
        {"timestamp": base - timedelta(minutes=3), "success": False},
        {"timestamp": base - timedelta(minutes=2), "success": False},
        {"timestamp": base - timedelta(minutes=1), "success": False},
        {"timestamp": base - timedelta(seconds=30), "success": False},
    ]
    anomalies = service._detect_failed_auth_spike(failures, base - timedelta(hours=1))
    assert anomalies, "Expected failed login burst anomaly"
    assert anomalies[0]["anomaly_type"] == "failed_logins"
