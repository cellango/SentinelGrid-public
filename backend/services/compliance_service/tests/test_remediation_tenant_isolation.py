from pathlib import Path
import os
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.main import app
from app.api import remediation as remediation_api
from app.core.database import get_current_tenant, get_tenant_session


TENANT_ID = "00000000-0000-0000-0000-000000000111"


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDB:
    def __init__(self):
        self.result = None

    def query(self, *args, **kwargs):
        return FakeQuery(self.result)


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def call_log(monkeypatch):
    log = {}

    class DummyEnhancer:
        def __init__(self, db):
            log["enhancer_db"] = db

        async def enhance_iam_finding(self, finding_id, tenant_id):
            log["enhance_iam"] = (str(finding_id), str(tenant_id))
            return {
                "finding_id": str(finding_id),
                "nist_control_id": "AC-2",
                "remediation_plan": {"steps": []},
                "remediation_status": "planned",
            }

        async def enhance_posture_finding(self, finding_id, tenant_id):
            log["enhance_posture"] = (str(finding_id), str(tenant_id))
            return {
                "finding_id": str(finding_id),
                "nist_control_id": "CM-6",
                "remediation_plan": {"steps": []},
                "remediation_status": "planned",
            }

    class DummyPlanner:
        def __init__(self, db):
            log["planner_db"] = db

        def create_remediation_plan(self, finding_id, finding_type, tenant_id, custom_steps=None):
            log["plan"] = (str(finding_id), finding_type, str(tenant_id), custom_steps)
            return {"steps": custom_steps or [], "finding_type": finding_type}

    class DummyOrchestrator:
        def __init__(self, db):
            log["orchestrator_db"] = db

        async def execute_remediation(self, finding_id, finding_type, tenant_id, playbook_id=None, auto_approve=False):
            log["execute"] = (
                str(finding_id),
                finding_type,
                str(tenant_id),
                str(playbook_id) if playbook_id else None,
                auto_approve,
            )
            return {
                "remediation_id": str(uuid4()),
                "execution_id": str(uuid4()),
                "status": "in_progress",
                "finding_id": str(finding_id),
                "finding_type": finding_type,
            }

    monkeypatch.setattr(remediation_api, "FindingEnhancer", DummyEnhancer)
    monkeypatch.setattr(remediation_api, "RemediationPlanner", DummyPlanner)
    monkeypatch.setattr(remediation_api, "RemediationOrchestrator", DummyOrchestrator)
    return log


@pytest.fixture
def client(fake_db):
    def override_get_current_tenant():
        return TENANT_ID

    def override_get_tenant_session():
        yield fake_db

    app.dependency_overrides[get_current_tenant] = override_get_current_tenant
    app.dependency_overrides[get_tenant_session] = override_get_tenant_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_enhance_finding_uses_authenticated_tenant(client, call_log):
    finding_id = "00000000-0000-0000-0000-000000000001"

    response = client.post(
        f"/api/v1/compliance/findings/{finding_id}/enhance",
        json={"finding_type": "iam_finding"},
    )

    assert response.status_code == 200
    assert call_log["enhance_iam"] == (finding_id, TENANT_ID)


def test_create_remediation_plan_uses_authenticated_tenant(client, call_log):
    finding_id = "00000000-0000-0000-0000-000000000002"

    response = client.post(
        f"/api/v1/compliance/findings/{finding_id}/remediation-plan",
        json={"finding_type": "posture_finding", "custom_steps": [{"step": 1}]},
    )

    assert response.status_code == 200
    assert call_log["plan"] == (finding_id, "posture_finding", TENANT_ID, [{"step": 1}])


def test_execute_remediation_uses_authenticated_tenant(client, call_log):
    finding_id = "00000000-0000-0000-0000-000000000003"
    playbook_id = "00000000-0000-0000-0000-000000000099"

    response = client.post(
        f"/api/v1/compliance/findings/{finding_id}/remediate",
        params={"finding_type": "iam_finding"},
        json={"playbook_id": playbook_id, "auto_approve": True},
    )

    assert response.status_code == 200
    assert call_log["execute"] == (finding_id, "iam_finding", TENANT_ID, playbook_id, True)


def test_get_remediation_status_uses_authenticated_tenant(client, fake_db):
    finding_id = "00000000-0000-0000-0000-000000000004"
    remediation_id = "00000000-0000-0000-0000-000000000055"
    execution_id = "00000000-0000-0000-0000-000000000066"
    fake_db.result = SimpleNamespace(
        id=remediation_id,
        status="in_progress",
        playbook_execution_id=execution_id,
        created_at="2026-03-28T00:00:00Z",
    )

    response = client.get(
        f"/api/v1/compliance/findings/{finding_id}/remediation-status",
        params={"finding_type": "iam_finding"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "finding_id": finding_id,
        "remediation_id": remediation_id,
        "status": "in_progress",
        "execution_id": execution_id,
        "created_at": "2026-03-28T00:00:00Z",
    }
