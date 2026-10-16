from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import sync_jobs
from app.api.request_context import RequestContext, get_current_request_context


class SyncJobManagerSpy:
    def __init__(self):
        self.create_calls = []
        self.execute_calls = []
        self.status_calls = []
        self.list_calls = []
        self.schedule_calls = []
        self.list_schedule_calls = []
        self.get_schedule_calls = []
        self.update_schedule_calls = []
        self.delete_schedule_calls = []
        self.statistics_calls = []
        self.retry_calls = []

    def create_sync_job(self, **kwargs):
        self.create_calls.append(kwargs)
        return {
            "job_id": "job-1",
            "integration_id": kwargs["integration_id"],
            "sync_type": kwargs["sync_type"],
            "direction": kwargs["direction"].value,
            "status": "pending",
            "created_at": datetime.now(timezone.utc),
            "tenant_id": kwargs["tenant_id"],
        }

    def execute_sync_job(self, job_id, tenant_id=None):
        self.execute_calls.append((job_id, tenant_id))
        return {"job_id": job_id, "status": "success"}

    def get_job_status(self, job_id, tenant_id=None):
        self.status_calls.append((job_id, tenant_id))
        return {
            "job_id": job_id,
            "status": "success",
            "sync_type": "users",
            "direction": "import",
            "created_at": datetime.now(timezone.utc),
            "started_at": None,
            "completed_at": None,
            "result": {"count": 1},
            "error": None,
            "duration_seconds": None,
        }

    def list_jobs(self, integration_id=None, status=None, tenant_id=None, limit=100):
        self.list_calls.append((integration_id, status, tenant_id, limit))
        return [
            {
                "job_id": "job-1",
                "status": "success",
                "sync_type": "users",
                "direction": "import",
                "created_at": datetime.now(timezone.utc),
                "started_at": None,
                "completed_at": None,
                "result": None,
                "error": None,
                "duration_seconds": None,
            }
        ]

    def schedule_sync_job(self, **kwargs):
        self.schedule_calls.append(kwargs)
        return {
            "schedule_id": "schedule-1",
            "integration_id": kwargs["integration_id"],
            "schedule_type": kwargs["schedule_type"].value,
            "sync_type": kwargs["sync_type"],
            "direction": kwargs["direction"].value,
            "enabled": True,
            "last_run": None,
            "next_run": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "tenant_id": kwargs["tenant_id"],
        }

    def list_schedules(self, integration_id=None, tenant_id=None):
        self.list_schedule_calls.append((integration_id, tenant_id))
        return [
            {
                "schedule_id": "schedule-1",
                "integration_id": integration_id or "integration-1",
                "schedule_type": "daily",
                "sync_type": "users",
                "direction": "import",
                "enabled": True,
                "last_run": None,
                "next_run": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
                "tenant_id": tenant_id,
            }
        ]

    def get_schedule(self, schedule_id, tenant_id=None):
        self.get_schedule_calls.append((schedule_id, tenant_id))
        return {
            "schedule_id": schedule_id,
            "integration_id": "integration-1",
            "schedule_type": "daily",
            "sync_type": "users",
            "direction": "import",
            "enabled": True,
            "last_run": None,
            "next_run": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "tenant_id": tenant_id,
        }

    def update_schedule(self, schedule_id, updates, tenant_id=None):
        self.update_schedule_calls.append((schedule_id, updates, tenant_id))
        return {
            "schedule_id": schedule_id,
            "integration_id": "integration-1",
            "schedule_type": updates.get("schedule_type", "daily"),
            "sync_type": "users",
            "direction": "import",
            "enabled": updates.get("enabled", True),
            "last_run": None,
            "next_run": datetime.now(timezone.utc),
            "created_at": datetime.now(timezone.utc),
            "tenant_id": tenant_id,
        }

    def delete_schedule(self, schedule_id, tenant_id=None):
        self.delete_schedule_calls.append((schedule_id, tenant_id))
        return {"schedule_id": schedule_id, "status": "deleted"}

    def get_sync_statistics(self, integration_id=None, days=30, tenant_id=None):
        self.statistics_calls.append((integration_id, days, tenant_id))
        return {
            "period_days": days,
            "total_jobs": 1,
            "successful_jobs": 1,
            "failed_jobs": 0,
            "success_rate": 100.0,
            "average_duration_seconds": 1.0,
            "integration_id": integration_id,
            "tenant_id": tenant_id,
        }

    def retry_failed_job(self, job_id, tenant_id=None):
        self.retry_calls.append((job_id, tenant_id))
        return {"job_id": job_id, "status": "retrying"}


@pytest.fixture
def request_context():
    return RequestContext(
        tenant_id=uuid4(),
        user_id=str(uuid4()),
    )


@pytest.fixture
def sync_jobs_test_app(request_context):
    app = FastAPI()
    app.include_router(sync_jobs.router)
    app.dependency_overrides[get_current_request_context] = lambda: request_context
    return app


@pytest.fixture
def sync_jobs_client(sync_jobs_test_app):
    return TestClient(sync_jobs_test_app)


def _override_dependency(app, dependency, value):
    app.dependency_overrides[dependency] = lambda: value


def test_create_sync_job_rejects_foreign_body_tenant(sync_jobs_test_app, sync_jobs_client):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.post(
        "/internal/iam/sync-jobs/",
        headers={"authorization": "Bearer test-token"},
        json={
            "integration_id": "integration-1",
            "sync_type": "users",
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.create_calls == []


def test_create_sync_job_defaults_to_authenticated_tenant(
    sync_jobs_test_app,
    sync_jobs_client,
    request_context,
):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.post(
        "/internal/iam/sync-jobs/",
        headers={"authorization": "Bearer test-token"},
        json={"integration_id": "integration-1", "sync_type": "users"},
    )

    assert response.status_code == 200
    assert manager.create_calls[0]["tenant_id"] == str(request_context.tenant_id)
    assert response.json()["tenant_id"] == str(request_context.tenant_id)


def test_list_jobs_rejects_foreign_query_tenant(sync_jobs_test_app, sync_jobs_client):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.get(
        f"/internal/iam/sync-jobs/?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.list_calls == []


def test_list_jobs_defaults_to_authenticated_tenant(
    sync_jobs_test_app,
    sync_jobs_client,
    request_context,
):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.get(
        "/internal/iam/sync-jobs/",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert manager.list_calls[0][2] == str(request_context.tenant_id)


def test_schedule_sync_job_rejects_foreign_body_tenant(sync_jobs_test_app, sync_jobs_client):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.post(
        "/internal/iam/sync-jobs/schedules",
        headers={"authorization": "Bearer test-token"},
        json={
            "integration_id": "integration-1",
            "schedule_type": "daily",
            "sync_type": "users",
            "tenant_id": str(uuid4()),
        },
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.schedule_calls == []


def test_list_schedules_rejects_foreign_query_tenant(sync_jobs_test_app, sync_jobs_client):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.get(
        f"/internal/iam/sync-jobs/schedules?tenant_id={uuid4()}",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Access denied: Tenant mismatch"}
    assert manager.list_schedule_calls == []


def test_job_status_execute_retry_use_authenticated_tenant(
    sync_jobs_test_app,
    sync_jobs_client,
    request_context,
):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    status_response = sync_jobs_client.get(
        "/internal/iam/sync-jobs/job-1",
        headers={"authorization": "Bearer test-token"},
    )
    execute_response = sync_jobs_client.post(
        "/internal/iam/sync-jobs/job-1/execute",
        headers={"authorization": "Bearer test-token"},
    )
    retry_response = sync_jobs_client.post(
        "/internal/iam/sync-jobs/job-1/retry",
        headers={"authorization": "Bearer test-token"},
    )

    assert status_response.status_code == 200
    assert execute_response.status_code == 200
    assert retry_response.status_code == 200
    assert manager.status_calls[0][1] == str(request_context.tenant_id)
    assert manager.execute_calls[0][1] == str(request_context.tenant_id)
    assert manager.retry_calls[0][1] == str(request_context.tenant_id)


def test_schedule_get_update_delete_use_authenticated_tenant(
    sync_jobs_test_app,
    sync_jobs_client,
    request_context,
):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    get_response = sync_jobs_client.get(
        "/internal/iam/sync-jobs/schedules/schedule-1",
        headers={"authorization": "Bearer test-token"},
    )
    update_response = sync_jobs_client.put(
        "/internal/iam/sync-jobs/schedules/schedule-1",
        headers={"authorization": "Bearer test-token"},
        json={"enabled": False},
    )
    delete_response = sync_jobs_client.delete(
        "/internal/iam/sync-jobs/schedules/schedule-1",
        headers={"authorization": "Bearer test-token"},
    )

    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert manager.get_schedule_calls[0][1] == str(request_context.tenant_id)
    assert manager.update_schedule_calls[0][2] == str(request_context.tenant_id)
    assert manager.delete_schedule_calls[0][1] == str(request_context.tenant_id)


def test_sync_statistics_use_authenticated_tenant(
    sync_jobs_test_app,
    sync_jobs_client,
    request_context,
):
    manager = SyncJobManagerSpy()
    _override_dependency(sync_jobs_test_app, sync_jobs.get_sync_job_manager, manager)

    response = sync_jobs_client.get(
        "/internal/iam/sync-jobs/statistics?days=7",
        headers={"authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert manager.statistics_calls[0] == (None, 7, str(request_context.tenant_id))
