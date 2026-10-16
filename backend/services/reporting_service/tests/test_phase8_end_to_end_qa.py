"""Phase 8.2 executable QA journey for reporting-service surfaces."""

from __future__ import annotations

import operator
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

if "apscheduler" not in sys.modules:
    aps = types.ModuleType("apscheduler")
    schedulers_mod = types.ModuleType("apscheduler.schedulers")
    asyncio_mod = types.ModuleType("apscheduler.schedulers.asyncio")
    triggers_mod = types.ModuleType("apscheduler.triggers")
    cron_mod = types.ModuleType("apscheduler.triggers.cron")
    date_mod = types.ModuleType("apscheduler.triggers.date")

    class _DummyScheduler:
        def __init__(self, *args, **kwargs):
            self._jobs = []

        def start(self):
            return None

        def add_job(self, *args, **kwargs):
            return None

        def get_jobs(self):
            return list(self._jobs)

        def remove_job(self, job_id):
            return None

        def shutdown(self):
            return None

    class _DummyTrigger:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    asyncio_mod.AsyncIOScheduler = _DummyScheduler
    cron_mod.CronTrigger = _DummyTrigger
    date_mod.DateTrigger = _DummyTrigger
    sys.modules["apscheduler"] = aps
    sys.modules["apscheduler.schedulers"] = schedulers_mod
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod
    sys.modules["apscheduler.triggers"] = triggers_mod
    sys.modules["apscheduler.triggers.cron"] = cron_mod
    sys.modules["apscheduler.triggers.date"] = date_mod

from app.api import reports as reports_api  # noqa: E402
from app.api import scheduled_reports as scheduled_reports_api  # noqa: E402


TENANT_ID = "tenant-a"


class _QueryResult:
    def __init__(self, values):
        self._values = list(values)

    def filter(self, *args, **kwargs):
        values = self._values
        for criterion in args:
            values = [value for value in values if _matches_criterion(value, criterion)]
        self._values = values
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._values[0] if self._values else None

    def all(self):
        return list(self._values)


class _FakeTenantDB:
    def __init__(self, values):
        self._values = list(values)
        self.added = []
        self.commit_count = 0

    def query(self, *args, **kwargs):
        return _QueryResult(self._values)

    def add(self, obj):
        self.added.append(obj)
        self._values.append(obj)

    def commit(self):
        self.commit_count += 1

    def refresh(self, obj):
        now = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
        obj.id = getattr(obj, "id", None) or "report-1"
        obj.created_at = getattr(obj, "created_at", None) or now
        obj.updated_at = getattr(obj, "updated_at", None) or now
        obj.generated_at = getattr(obj, "generated_at", None) or now


class _FakeReportService:
    def __init__(self):
        self.calls = []

    async def generate_report(self, db, report, template, tenant_id, realm_name, date_range, sections, report_parameters):
        self.calls.append(
            {
                "db": db,
                "report": report,
                "template": template,
                "tenant_id": tenant_id,
                "realm_name": realm_name,
                "date_range": date_range,
                "sections": sections,
                "report_parameters": report_parameters,
            }
        )
        report.report_metadata["compliance_snapshot"] = {
            "status": "captured",
            "snapshot_hash_sha256": "c" * 64,
            "evidence_summary": {"evidence_package_ids": report_parameters["evidence_package_ids"]},
        }


class _FakeComplianceWorkflowService:
    def __init__(self):
        self.calls = []

    async def create_recommendation_and_task(self, db, **kwargs):
        self.calls.append({"db": db, "kwargs": kwargs})
        return {"id": "rec-report-1"}


class _FakeScheduler:
    def __init__(self):
        self.scheduled = []

    def schedule_report(self, template, tenant_id, schedule):
        job_id = f"report_{template.id}_{tenant_id}"
        self.scheduled.append({"template_id": template.id, "tenant_id": tenant_id, "schedule": schedule, "job_id": job_id})
        return job_id


def _payload(*roles):
    return {"tenant_id": TENANT_ID, "user_id": "qa-user", "roles": list(roles)}


def _build_template(template_id: str, tenant_id: str | None, *, required_roles=None):
    now = datetime(2026, 4, 28, 12, 0, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        id=template_id,
        tenant_id=tenant_id,
        name="SOC 2 Evidence Summary",
        description="Evidence-backed SOC 2 report",
        type="soc2",
        sections=[],
        data_queries=[],
        schedule=None,
        required_roles=required_roles or ["compliance_manager"],
        created_at=now,
        updated_at=now,
    )


def _matches_criterion(value, criterion):
    if isinstance(criterion, BooleanClauseList):
        clause_results = [_matches_criterion(value, clause) for clause in criterion.clauses]
        if criterion.operator is operator.or_:
            return any(clause_results)
        if criterion.operator is operator.and_:
            return all(clause_results)

    if isinstance(criterion, BinaryExpression):
        field_name = criterion.left.key
        actual = getattr(value, field_name, None)
        expected = getattr(criterion.right, "value", None)
        if criterion.operator is operator.eq:
            return actual == expected
        if criterion.operator.__name__ == "is_":
            return actual is expected

    raise AssertionError(f"Unsupported criterion: {criterion!r}")


def test_phase8_reporting_generates_evidence_backed_report_and_monthly_schedule():
    template = _build_template("tpl-soc2", TENANT_ID)
    other_template = _build_template("tpl-other", "tenant-b")
    fake_db = _FakeTenantDB([template, other_template])
    report_service = _FakeReportService()
    workflow = _FakeComplianceWorkflowService()
    scheduler = _FakeScheduler()

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")
    app.include_router(scheduled_reports_api.router, prefix="/api/v1/reports/scheduled")

    def tenant_session():
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = lambda: TENANT_ID
    app.dependency_overrides[reports_api.get_current_payload] = lambda: _payload("compliance_manager")
    app.dependency_overrides[reports_api.get_tenant_session] = tenant_session
    app.dependency_overrides[reports_api.resolve_accessible_template] = lambda: template
    app.dependency_overrides[reports_api.get_report_service] = lambda: report_service
    app.dependency_overrides[reports_api.get_compliance_agent_workflow_service] = lambda: workflow
    app.dependency_overrides[scheduled_reports_api.get_current_tenant] = lambda: TENANT_ID
    app.dependency_overrides[scheduled_reports_api.get_current_payload] = lambda: _payload("compliance_manager")
    app.dependency_overrides[scheduled_reports_api.get_tenant_session] = tenant_session

    original_get_scheduler = scheduled_reports_api.get_scheduler
    scheduled_reports_api.get_scheduler = lambda: scheduler

    try:
        client = TestClient(app, raise_server_exceptions=False)
        report_response = client.post(
            "/api/v1/reports/generate",
            headers={"Authorization": "Bearer qa-token"},
            json={
                "template_id": "tpl-soc2",
                "format": "pdf",
                "date_range": {"start": "2026-04-01T00:00:00Z", "end": "2026-06-30T23:59:59Z"},
                "framework_ids": ["soc2"],
                "control_ids": ["CC6.1"],
                "evidence_package_ids": ["pkg-soc2-q2"],
                "include_gaps": True,
                "include_expired_evidence": False,
            },
        )
        schedule_response = client.post(
            "/api/v1/reports/scheduled/",
            json={
                "template_id": "tpl-soc2",
                "schedule": {
                    "frequency": "monthly",
                    "day": "1",
                    "time": "09:00",
                    "recipients": ["compliance@example.com"],
                    "enabled": True,
                },
            },
        )
        foreign_schedule_response = client.post(
            "/api/v1/reports/scheduled/",
            json={
                "template_id": "tpl-other",
                "schedule": {"frequency": "monthly", "day": "1", "time": "09:00", "recipients": [], "enabled": True},
            },
        )
    finally:
        scheduled_reports_api.get_scheduler = original_get_scheduler
        app.dependency_overrides.clear()

    assert report_response.status_code == 201
    created_report = fake_db.added[0]
    assert created_report.tenant_id == TENANT_ID
    assert created_report.report_metadata["report_inputs"]["framework_ids"] == ["soc2"]
    assert created_report.report_metadata["report_inputs"]["evidence_package_ids"] == ["pkg-soc2-q2"]
    assert report_service.calls[0]["report_parameters"]["evidence_package_ids"] == ["pkg-soc2-q2"]
    assert created_report.report_metadata["compliance_snapshot"]["snapshot_hash_sha256"] == "c" * 64
    assert workflow.calls[0]["kwargs"]["trigger_type"] == "report_generation_requested"
    assert workflow.calls[0]["kwargs"]["metadata"]["report"]["report_inputs"]["evidence_package_ids"] == ["pkg-soc2-q2"]

    assert schedule_response.status_code == 200
    assert schedule_response.json()["job_id"] == f"report_tpl-soc2_{TENANT_ID}"
    assert scheduler.scheduled[0]["schedule"]["frequency"] == "monthly"
    assert scheduler.scheduled[0]["schedule"]["day"] == "1"

    assert foreign_schedule_response.status_code == 403
    assert foreign_schedule_response.json()["detail"] == "Template not accessible for this tenant"
