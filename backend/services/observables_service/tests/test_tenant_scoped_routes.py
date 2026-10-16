from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_tenant_session
from app.main import app
from app.models import (
    AnalyzerJobResponse,
    BulkObservableCreate,
    EnrichmentStatus,
    Observable,
    ObservableAnalyzer,
    ObservableCreate,
)


def _observable(*, tenant_id, observable_id=None, observable_type="ip", value="1.2.3.4"):
    return Observable(
        id=observable_id or uuid4(),
        tenant_id=tenant_id,
        observable_type=observable_type,
        value=value,
        tlp_level=2,
        enrichment_status="completed",
        enrichment_data={"source": "pytest"},
        first_seen=datetime(2026, 3, 28, 12, 0, 0),
        last_seen=datetime(2026, 3, 28, 12, 5, 0),
        created_at=datetime(2026, 3, 28, 12, 0, 0),
    )


def _analyzer_job(*, observable_id):
    return ObservableAnalyzer(
        id=uuid4(),
        observable_id=observable_id,
        analyzer_id="VirusTotal_GetReport_3_0",
        cortex_job_id="cortex-123",
        status="completed",
        report={"score": 5},
        started_at=datetime(2026, 3, 28, 12, 0, 0),
        completed_at=datetime(2026, 3, 28, 12, 1, 0),
    )


@pytest.fixture
def observables_client():
    fake_db = Mock()

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, fake_db

    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {
        "x-tenant-id": str(uuid4()),
        "authorization": "Bearer internal-service-token-change-in-production",
    }


def test_create_observable_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observable = _observable(tenant_id=tenant_id)

    with patch("app.main.ObservableTracker") as tracker_class:
        tracker = tracker_class.return_value
        tracker.create_observable.return_value = observable

        response = client.post(
            "/observables",
            headers=auth_headers,
            json={"observable_type": "ip", "value": "1.2.3.4", "auto_enrich": False},
        )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id
    tracker_class.assert_called_once_with(fake_db)


def test_bulk_create_observables_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observables = [_observable(tenant_id=tenant_id, value="1.2.3.4"), _observable(tenant_id=tenant_id, value="example.com", observable_type="domain")]

    with patch("app.main.ObservableTracker") as tracker_class:
        tracker = tracker_class.return_value
        tracker.bulk_create_and_enrich = AsyncMock(return_value=observables)

        response = client.post(
            "/observables/bulk",
            headers=auth_headers,
            json={
                "observables": [
                    {"observable_type": "ip", "value": "1.2.3.4"},
                    {"observable_type": "domain", "value": "example.com"},
                ]
            },
        )

    assert response.status_code == 200
    assert len(response.json()) == 2
    tracker_class.assert_called_once_with(fake_db)


def test_get_observable_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observable = _observable(tenant_id=tenant_id)

    with patch("app.main.ObservableTracker") as tracker_class:
        tracker = tracker_class.return_value
        tracker.get_observable.return_value = observable

        response = client.get(f"/observables/{observable.id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(observable.id)
    tracker_class.assert_called_once_with(fake_db)


def test_search_observables_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observable = _observable(tenant_id=tenant_id)

    with patch("app.main.ObservableTracker") as tracker_class:
        tracker = tracker_class.return_value
        tracker.search_observables.return_value = [observable]

        response = client.post(
            "/observables/search",
            headers=auth_headers,
            json={"observable_type": "ip", "value": "1.2", "limit": 10, "offset": 0},
        )

    assert response.status_code == 200
    assert response.json()[0]["tenant_id"] == tenant_id
    tracker_class.assert_called_once_with(fake_db)


def test_enrich_observable_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observable = _observable(tenant_id=tenant_id)

    with patch("app.main.ObservableTracker") as tracker_class, patch("app.main.EnrichmentEngine") as engine_class:
        tracker = tracker_class.return_value
        tracker.get_observable.return_value = observable
        engine = engine_class.return_value
        engine.enrich_observable = AsyncMock(return_value=observable)

        response = client.post(
            f"/observables/{observable.id}/enrich",
            headers=auth_headers,
            json={"observable_id": str(observable.id), "analyzer_ids": ["VirusTotal_GetReport_3_0"]},
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(observable.id)
    tracker_class.assert_called_once_with(fake_db)
    engine_class.assert_called_once_with(fake_db)


def test_get_observable_analyzers_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observable = _observable(tenant_id=tenant_id)
    analyzer_job = _analyzer_job(observable_id=observable.id)

    fake_db.query.return_value.filter.return_value.all.return_value = [analyzer_job]

    with patch("app.main.ObservableTracker") as tracker_class:
        tracker = tracker_class.return_value
        tracker.get_observable.return_value = observable

        response = client.get(f"/observables/{observable.id}/analyzers", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()[0]["observable_id"] == str(observable.id)
    tracker_class.assert_called_once_with(fake_db)


def test_update_observable_uses_tenant_scoped_dependency(observables_client, auth_headers):
    client, fake_db = observables_client
    tenant_id = auth_headers["x-tenant-id"]
    observable = _observable(tenant_id=tenant_id)

    with patch("app.main.ObservableTracker") as tracker_class:
        tracker = tracker_class.return_value
        tracker.get_observable.return_value = observable

        response = client.patch(
            f"/observables/{observable.id}",
            headers=auth_headers,
            json={
                "tlp_level": 3,
                "enrichment_status": EnrichmentStatus.COMPLETED.value,
                "enrichment_data": {"source": "updated"},
            },
        )

    assert response.status_code == 200
    assert response.json()["tlp_level"] == 3
    assert response.json()["enrichment_data"] == {"source": "updated"}
    fake_db.commit.assert_called_once()
    fake_db.refresh.assert_called_once_with(observable)
    tracker_class.assert_called_once_with(fake_db)
