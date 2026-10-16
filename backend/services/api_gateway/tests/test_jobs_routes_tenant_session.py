from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_jobs
from sg_core.db import get_tenant_session
from sg_core.security import get_current_tenant


class _Result:
    def __init__(self, *, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def first(self):
        return self._row

    def fetchall(self):
        return self._rows


class _Row:
    def __init__(self, job_id, tenant_id, job_type, status="queued"):
        self.id = job_id
        self.tenant_id = tenant_id
        self.job_type = job_type
        self.status = status
        self.attempts = 0
        self.error = None
        self.started_at = None
        self.finished_at = None
        self.created_at = None
        self.updated_at = None


class _FakeDB:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []
        self.committed = False

    def execute(self, statement, params=None):
        self.calls.append({"sql": str(statement), "params": params or {}})
        if self.responses:
            return self.responses.pop(0)
        return _Result()

    def commit(self):
        self.committed = True


@pytest.fixture
def jobs_client():
    app = FastAPI()
    app.include_router(routes_jobs.router, prefix="/jobs")
    tenant_id = str(uuid4())

    def _get_tenant():
        return tenant_id

    fake_db = _FakeDB()

    def _get_db():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = _get_tenant
    app.dependency_overrides[get_tenant_session] = _get_db

    with TestClient(app) as client:
        yield client, fake_db, tenant_id

    app.dependency_overrides.clear()


def test_enqueue_job_uses_authenticated_tenant_scope(jobs_client):
    client, fake_db, tenant_id = jobs_client
    job_id = str(uuid4())
    fake_db.responses = [_Result(row=_Row(job_id, tenant_id, "scan"))]

    response = client.post(
        "/jobs",
        json={
            "tenant_id": str(uuid4()),
            "job_type": "scan",
            "payload": {"target": "tenant-overridden"},
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == tenant_id
    assert fake_db.calls[0]["params"]["tenant_id"] == tenant_id
    assert fake_db.committed is True


def test_get_job_scopes_lookup_to_authenticated_tenant(jobs_client):
    client, fake_db, tenant_id = jobs_client
    job_id = str(uuid4())
    fake_db.responses = [_Result(row=_Row(job_id, tenant_id, "scan", status="running"))]

    response = client.get(f"/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["id"] == job_id
    assert fake_db.calls[0]["params"]["tenant_id"] == tenant_id


def test_list_jobs_scopes_query_to_authenticated_tenant(jobs_client):
    client, fake_db, tenant_id = jobs_client
    fake_db.responses = [
        _Result(
            rows=[
                _Row(str(uuid4()), tenant_id, "scan", status="queued"),
                _Row(str(uuid4()), tenant_id, "report", status="finished"),
            ]
        )
    ]

    response = client.get("/jobs?job_type=scan&status=queued&limit=25")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert fake_db.calls[0]["params"]["tenant_id"] == tenant_id
    assert fake_db.calls[0]["params"]["job_type"] == "scan"
    assert fake_db.calls[0]["params"]["status"] == "queued"
    assert fake_db.calls[0]["params"]["limit"] == 25
