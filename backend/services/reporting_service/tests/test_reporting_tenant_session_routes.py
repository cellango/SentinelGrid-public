"""Focused tenant-session coverage for reporting-service routes."""

import operator
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
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
            self._jobs = [job for job in self._jobs if getattr(job, "id", None) != job_id]

        def shutdown(self):
            return None

    class _DummyTrigger:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __str__(self):
            return "dummy-trigger"

    asyncio_mod.AsyncIOScheduler = _DummyScheduler
    cron_mod.CronTrigger = _DummyTrigger
    date_mod.DateTrigger = _DummyTrigger

    aps.schedulers = schedulers_mod
    aps.triggers = triggers_mod
    sys.modules["apscheduler"] = aps
    sys.modules["apscheduler.schedulers"] = schedulers_mod
    sys.modules["apscheduler.schedulers.asyncio"] = asyncio_mod
    sys.modules["apscheduler.triggers"] = triggers_mod
    sys.modules["apscheduler.triggers.cron"] = cron_mod
    sys.modules["apscheduler.triggers.date"] = date_mod

from app.api import reports as reports_api
from app.api import scheduled_reports as scheduled_reports_api
from app.api import shares as shares_api
from app.api import templates as templates_api
from app.models.report import Report, ReportFormat, ReportStatus
from app.models.template import ReportGenerateRequest


@pytest.fixture(autouse=True)
def _disable_route_audit(monkeypatch):
    async def noop_log_event(self, payload):
        return None

    monkeypatch.setattr("app.services.report_access.AuditClient.log_event", noop_log_event)


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

    def limit(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def first(self):
        return self._values[0] if self._values else None

    def all(self):
        return list(self._values)


class _FakeTenantDB:
    def __init__(self, *, first_value=None, all_values=None):
        if all_values is not None:
            self._values = list(all_values)
        elif first_value is not None:
            self._values = [first_value]
        else:
            self._values = []
        self.added = []
        self.deleted = []
        self.commit_count = 0

    def query(self, *args, **kwargs):
        return _QueryResult(self._values)

    def add(self, obj):
        self.added.append(obj)
        self._values.append(obj)

    def commit(self):
        self.commit_count += 1

    def refresh(self, obj):
        now = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
        obj.id = getattr(obj, "id", None) or "report-1"
        obj.created_at = getattr(obj, "created_at", None) or now
        obj.updated_at = getattr(obj, "updated_at", None) or now
        obj.generated_at = getattr(obj, "generated_at", None) or now

    def delete(self, obj):
        self.deleted.append(obj)


class _FakeReportService:
    async def generate_report(self, *args, **kwargs):
        return None


class _FakeComplianceWorkflowService:
    def __init__(self):
        self.calls = []

    async def create_recommendation_and_task(self, db, **kwargs):
        self.calls.append({"db": db, "kwargs": kwargs})
        return {"id": "rec-1"}


class _FakeQuestionnaireService:
    async def build_questionnaire_assist(self, tenant_id, questions):
        return {
            "answers": [
                {
                    "answer": f"answer-for-{tenant_id}",
                    "confidence": "high",
                    "recommended_artifacts": [{"template_key": "soc2_summary"}],
                    "follow_up": ["next-step"],
                }
            ]
        }


class _FakeScheduler:
    def __init__(self):
        self.scheduled = []
        self.unscheduled = []
        self.jobs = []

    def schedule_report(self, template, tenant_id, schedule):
        job_id = f"report_{template.id}_{tenant_id}"
        self.scheduled.append((template.id, tenant_id, schedule))
        self.jobs = [
            job
            for job in self.jobs
            if job["job_id"] != job_id
        ]
        self.jobs.append({"job_id": job_id, "next_run": "2026-04-01T09:00:00Z"})
        return job_id

    def list_scheduled_reports(self, tenant_id):
        return [
            job for job in self.jobs
            if job["job_id"].endswith(f"_{tenant_id}")
        ]

    def unschedule_report(self, job_id):
        self.unscheduled.append(job_id)
        self.jobs = [job for job in self.jobs if job["job_id"] != job_id]


def _unexpected_dependency():
    raise AssertionError("Unexpected plain DB dependency used")
    yield  # pragma: no cover


def _payload(*roles):
    return {"tenant_id": "tenant-a", "user_id": "user-123", "roles": list(roles or ("tenant_admin",))}


def _build_report(report_id="report-1") -> Report:
    now = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    report = Report(
        tenant_id="tenant-a",
        template_id="tpl-1",
        name="Executive Summary",
        format=ReportFormat.PDF,
        status=ReportStatus.COMPLETED,
        report_metadata={"template_key": "soc2_summary", "report_type": "soc2"},
    )
    report.id = report_id
    report.created_at = now
    report.updated_at = now
    report.generated_at = now
    report.download_url = "https://reports.example/report-1.pdf"
    report.sections = ["Overview"]
    return report


def _build_template(
    template_id,
    tenant_id=None,
    *,
    name="Executive Summary",
    template_type="executive",
    required_roles=None,
):
    now = datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc)
    return SimpleNamespace(
        id=template_id,
        tenant_id=tenant_id,
        name=name,
        description="template",
        type=template_type,
        sections=[],
        data_queries=[],
        schedule=None,
        required_roles=required_roles or [],
        created_at=now,
        updated_at=now,
    )


def _matches_criterion(value, criterion):
    if isinstance(criterion, BooleanClauseList):
        op = criterion.operator
        clause_results = [_matches_criterion(value, clause) for clause in criterion.clauses]
        if op is operator.or_:
            return any(clause_results)
        if op is operator.and_:
            return all(clause_results)
        raise AssertionError(f"Unsupported boolean operator: {op}")

    if isinstance(criterion, BinaryExpression):
        field_name = criterion.left.key
        actual = getattr(value, field_name)
        expected = getattr(criterion.right, "value", None)

        if criterion.operator is operator.eq:
            return actual == expected
        if criterion.operator.__name__ == "is_":
            return actual is expected

        raise AssertionError(f"Unsupported binary operator: {criterion.operator}")

    raise AssertionError(f"Unsupported criterion type: {type(criterion)!r}")


def test_generate_report_uses_tenant_session():
    calls = {"tenant_session": 0}
    fake_db = _FakeTenantDB()
    fake_workflow = _FakeComplianceWorkflowService()
    template = SimpleNamespace(
        id="tpl-1",
        tenant_id=None,
        name="Executive Summary",
        type="executive",
    )

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant():
        return "tenant-a"

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = override_tenant
    app.dependency_overrides[reports_api.get_current_payload] = lambda: _payload("tenant_admin")
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session
    app.dependency_overrides[reports_api.resolve_accessible_template] = lambda: template
    app.dependency_overrides[reports_api.get_report_service] = lambda: _FakeReportService()
    app.dependency_overrides[reports_api.get_compliance_agent_workflow_service] = lambda: fake_workflow

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/reports/generate",
            headers={"Authorization": "Bearer user-token"},
            json={
                "template_id": "tpl-1",
                "format": "pdf",
                "framework_ids": ["soc2"],
                "control_ids": ["CC6.1"],
                "evidence_package_ids": ["pkg-1"],
                "include_gaps": True,
                "include_expired_evidence": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert calls["tenant_session"] == 1
    assert len(fake_db.added) == 1
    assert fake_db.added[0].tenant_id == "tenant-a"
    assert fake_db.added[0].report_metadata["report_inputs"]["framework_ids"] == ["soc2"]
    assert fake_db.added[0].report_metadata["report_inputs"]["control_ids"] == ["CC6.1"]
    assert fake_db.added[0].report_metadata["report_inputs"]["evidence_package_ids"] == ["pkg-1"]
    assert fake_db.added[0].report_metadata["compliance_snapshot"]["status"] == "pending"
    assert response.json()["template_id"] == "tpl-1"
    assert len(fake_workflow.calls) == 1
    workflow_call = fake_workflow.calls[0]["kwargs"]
    assert workflow_call["tenant_id"] == "tenant-a"
    assert workflow_call["created_by"] == "user-123"
    assert workflow_call["authorization"] == "Bearer user-token"
    assert workflow_call["trigger_type"] == "report_generation_requested"
    assert workflow_call["recommendation_type"] == "read_only_summary"
    assert workflow_call["report_id"] == "report-1"
    assert workflow_call["metadata"]["report"]["report_inputs"]["framework_ids"] == ["soc2"]


def test_generate_report_rejects_unsupported_output_format():
    fake_db = _FakeTenantDB()
    template = SimpleNamespace(
        id="tpl-1",
        tenant_id=None,
        name="Compliance Status Report",
        type="compliance",
    )

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = lambda: "tenant-a"
    app.dependency_overrides[reports_api.get_current_payload] = lambda: _payload("tenant_admin")
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session
    app.dependency_overrides[reports_api.resolve_accessible_template] = lambda: template
    app.dependency_overrides[reports_api.get_report_service] = lambda: _FakeReportService()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/reports/generate",
            json={"template_id": "tpl-1", "format": "json"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported report format. Supported formats: pdf, csv"
    assert fake_db.added == []


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("compliance_viewer", 403),
        ("compliance_manager", 201),
        ("admin", 201),
    ],
)
def test_report_generation_enforces_template_role_matrix(role, expected_status):
    fake_db = _FakeTenantDB()
    template = SimpleNamespace(
        id="tpl-1",
        tenant_id=None,
        name="Compliance Status Report",
        type="compliance",
        required_roles=["compliance_manager"],
    )

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = lambda: "tenant-a"
    app.dependency_overrides[reports_api.get_current_payload] = lambda: _payload(role)
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session
    app.dependency_overrides[reports_api.resolve_accessible_template] = lambda: template
    app.dependency_overrides[reports_api.get_report_service] = lambda: _FakeReportService()
    app.dependency_overrides[reports_api.get_compliance_agent_workflow_service] = lambda: _FakeComplianceWorkflowService()

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/reports/generate",
            json={"template_id": "tpl-1", "format": "pdf"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    if expected_status == 201:
        assert fake_db.added[-1].tenant_id == "tenant-a"
        assert fake_db.added[-1].generated_by == "user-123"
    else:
        assert fake_db.added == []
        assert response.json()["detail"] == "Required report template role not found"


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("compliance_viewer", 403),
        ("report_exporter", 200),
        ("admin", 200),
    ],
)
def test_report_download_enforces_export_role_matrix(role, expected_status):
    report = _build_report()
    template = _build_template("tpl-1", None, required_roles=["report_exporter"])
    fake_db = _FakeTenantDB(all_values=[report, template])

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = lambda: "tenant-a"
    app.dependency_overrides[reports_api.get_current_payload] = lambda: _payload(role)
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/reports/report-1/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["download_url"] == "https://reports.example/report-1.pdf"
    else:
        assert response.json()["detail"] == "Required report template role not found"


def test_query_reports_uses_tenant_session():
    calls = {"tenant_session": 0}
    fake_db = _FakeTenantDB(all_values=[_build_report()])

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant():
        return "tenant-a"

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = override_tenant
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session
    app.dependency_overrides[reports_api.get_questionnaire_assist_service] = (
        lambda: _FakeQuestionnaireService()
    )

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/reports/query",
            json={"query": "How ready are we for SOC 2?"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls["tenant_session"] == 1
    body = response.json()
    assert body["answer"] == "answer-for-tenant-a"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["report_id"] == "report-1"


def test_report_lookup_routes_use_tenant_session():
    calls = {"tenant_session": 0}
    fake_db = _FakeTenantDB(first_value=_build_report(), all_values=[_build_report()])

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant():
        return "tenant-a"

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = override_tenant
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        list_response = client.get("/api/v1/reports/")
        get_response = client.get("/api/v1/reports/report-1")
        delete_response = client.delete("/api/v1/reports/report-1")
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert delete_response.status_code == 204
    assert calls["tenant_session"] == 3
    assert len(fake_db.deleted) == 1


def test_report_download_route_uses_tenant_session_and_audits_access():
    calls = {"tenant_session": 0}
    report = _build_report()
    template = _build_template("tpl-1", None)
    fake_db = _FakeTenantDB(all_values=[report, template])

    app = FastAPI()
    app.include_router(reports_api.router, prefix="/api/v1/reports")

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[reports_api.get_current_tenant] = lambda: "tenant-a"
    app.dependency_overrides[reports_api.get_current_payload] = lambda: _payload("tenant_admin")
    app.dependency_overrides[reports_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/reports/report-1/download")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert calls["tenant_session"] == 1
    body = response.json()
    assert body["report_id"] == "report-1"
    assert body["download_url"] == "https://reports.example/report-1.pdf"


def test_resolve_accessible_template_rejects_cross_tenant_template():
    plain_db = _FakeTenantDB(
        first_value=SimpleNamespace(id="tpl-1", tenant_id="tenant-b", name="Other Tenant")
    )

    with pytest.raises(HTTPException) as excinfo:
        reports_api.resolve_accessible_template(
            request=ReportGenerateRequest(template_id="tpl-1"),
            tenant_id="tenant-a",
            db=plain_db,
        )

    assert excinfo.value.status_code == 403
    assert excinfo.value.detail == "Template not accessible for this tenant"


def test_template_routes_use_tenant_session_and_keep_shared_templates_visible():
    calls = {"tenant_session": 0}
    shared_template = _build_template("tpl-system", None, name="System SOC2", template_type="soc2")
    tenant_template = _build_template("tpl-tenant", "tenant-a", name="Tenant SOC2", template_type="soc2")
    other_template = _build_template("tpl-other", "tenant-b", name="Other SOC2", template_type="soc2")
    fake_db = _FakeTenantDB(all_values=[shared_template, tenant_template, other_template])

    app = FastAPI()
    app.include_router(templates_api.router, prefix="/api/v1/reports/templates")

    def override_tenant():
        return "tenant-a"

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[templates_api.get_current_tenant] = override_tenant
    app.dependency_overrides[templates_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        list_response = client.get("/api/v1/reports/templates/?type_filter=soc2")
        get_response = client.get("/api/v1/reports/templates/tpl-system")
        create_response = client.post(
            "/api/v1/reports/templates/",
            json={
                "name": "Custom Tenant Report",
                "description": "custom",
                "type": "custom",
                "sections": [],
                "data_queries": [],
                "required_roles": [],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert list_response.status_code == 200
    assert get_response.status_code == 200
    assert create_response.status_code == 201
    assert calls["tenant_session"] == 3
    listed_ids = {item["id"] for item in list_response.json()}
    assert listed_ids == {"tpl-system", "tpl-tenant"}
    assert create_response.json()["tenant_id"] == "tenant-a"
    assert fake_db.added[0].tenant_id == "tenant-a"


def test_scheduled_report_routes_use_tenant_session_and_copy_system_templates():
    calls = {"tenant_session": 0}
    scheduler = _FakeScheduler()
    shared_template = _build_template("tpl-system", None, name="System SOC2", template_type="soc2")
    tenant_template = _build_template("tpl-tenant", "tenant-a", name="Tenant SOC2", template_type="soc2")
    other_template = _build_template("tpl-other", "tenant-b", name="Other SOC2", template_type="soc2")
    fake_db = _FakeTenantDB(all_values=[shared_template, tenant_template, other_template])

    app = FastAPI()
    app.include_router(scheduled_reports_api.router, prefix="/api/v1/reports/scheduled")

    def override_tenant():
        return "tenant-a"

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[scheduled_reports_api.get_current_tenant] = override_tenant
    app.dependency_overrides[scheduled_reports_api.get_current_payload] = lambda: _payload("tenant_admin")
    app.dependency_overrides[scheduled_reports_api.get_tenant_session] = override_tenant_session

    original_get_scheduler = scheduled_reports_api.get_scheduler
    scheduled_reports_api.get_scheduler = lambda: scheduler

    try:
        client = TestClient(app, raise_server_exceptions=False)
        list_templates_response = client.get("/api/v1/reports/scheduled/templates?type_filter=soc2")
        create_from_system_response = client.post(
            "/api/v1/reports/scheduled/",
            json={
                "template_id": "tpl-system",
                "schedule": {
                    "frequency": "weekly",
                    "day": "monday",
                    "time": "09:00",
                    "recipients": ["a@example.com"],
                    "enabled": True,
                },
            },
        )
        create_response = client.post(
            "/api/v1/reports/scheduled/",
            json={
                "template_id": "tpl-tenant",
                "schedule": {
                    "frequency": "weekly",
                    "day": "monday",
                    "time": "09:00",
                    "recipients": ["a@example.com"],
                    "enabled": True,
                },
            },
        )
        list_jobs_response = client.get("/api/v1/reports/scheduled/")
        update_response = client.put(
            "/api/v1/reports/scheduled/report_tpl-tenant_tenant-a",
            json={
                "frequency": "monthly",
                "day": "1",
                "time": "10:00",
                "recipients": ["a@example.com"],
                "enabled": True,
            },
        )
        delete_response = client.delete("/api/v1/reports/scheduled/report_tpl-tenant_tenant-a")
    finally:
        scheduled_reports_api.get_scheduler = original_get_scheduler
        app.dependency_overrides.clear()

    assert list_templates_response.status_code == 200
    assert create_from_system_response.status_code == 200
    assert create_response.status_code == 200
    assert list_jobs_response.status_code == 200
    assert update_response.status_code == 200
    assert delete_response.status_code == 200
    assert calls["tenant_session"] == 6

    listed_ids = {item["id"] for item in list_templates_response.json()}
    assert listed_ids == {"tpl-system", "tpl-tenant"}
    assert create_from_system_response.json()["source_template_id"] == "tpl-system"
    assert create_from_system_response.json()["template_id"] == "report-1"
    assert create_response.json()["job_id"] == "report_tpl-tenant_tenant-a"
    listed_job_template_ids = {item.get("template_id") for item in list_jobs_response.json()["items"]}
    assert {"report-1", "tpl-tenant"}.issubset(listed_job_template_ids)
    assert scheduler.unscheduled == [
        "report_tpl-tenant_tenant-a",
        "report_tpl-tenant_tenant-a",
    ]
    assert tenant_template.schedule is None


def test_share_management_routes_use_tenant_session(monkeypatch):
    calls = {"tenant_session": 0}
    report = _build_report()

    created_share = SimpleNamespace(
        id="share-1",
        tenant_id="tenant-a",
        report_id="report-1",
        share_token="token-1",
        expires_at=datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc),
        password_hash=None,
        access_count=0,
        last_accessed_at=None,
        created_at=datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    fake_db = _FakeTenantDB(all_values=[report, created_share])

    monkeypatch.setattr(
        shares_api.ShareService,
        "create_share",
        lambda self, db, report_id, tenant_id, expires_in_days, password, created_by=None: created_share,
    )
    monkeypatch.setattr(
        shares_api.ShareService,
        "list_shares",
        lambda self, db, report_id, tenant_id: [created_share],
    )
    monkeypatch.setattr(
        shares_api.ShareService,
        "delete_share",
        lambda self, db, share_id, tenant_id: None,
    )

    app = FastAPI()
    app.include_router(shares_api.router, prefix="/api/v1")

    def override_tenant():
        return "tenant-a"

    def override_tenant_session():
        calls["tenant_session"] += 1
        yield fake_db

    app.dependency_overrides[shares_api.get_current_tenant] = override_tenant
    app.dependency_overrides[shares_api.get_current_payload] = lambda: _payload("tenant_admin")
    app.dependency_overrides[shares_api.get_db] = _unexpected_dependency
    app.dependency_overrides[shares_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        create_response = client.post(
            "/api/v1/reports/report-1/share",
            json={"expires_in_days": 7},
        )
        list_response = client.get("/api/v1/reports/report-1/shares")
        delete_response = client.delete("/api/v1/shares/share-1")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    assert list_response.status_code == 200
    assert delete_response.status_code == 204
    assert calls["tenant_session"] == 3
    assert create_response.json()["share_token"] == "token-1"
    assert create_response.json()["share_url"].endswith("/shared/token-1")
    assert list_response.json()[0]["id"] == "share-1"


def test_share_management_routes_reject_cross_tenant_records():
    foreign_report = _build_report()
    foreign_report.tenant_id = "tenant-b"
    foreign_share = SimpleNamespace(
        id="share-1",
        tenant_id="tenant-b",
        report_id="report-1",
        share_token="token-1",
        expires_at=datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc),
        password_hash=None,
        access_count=0,
        last_accessed_at=None,
        created_at=datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    fake_db = _FakeTenantDB(all_values=[foreign_report, foreign_share])

    app = FastAPI()
    app.include_router(shares_api.router, prefix="/api/v1")

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[shares_api.get_current_tenant] = lambda: "tenant-a"
    app.dependency_overrides[shares_api.get_current_payload] = lambda: _payload("tenant_admin")
    app.dependency_overrides[shares_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        create_response = client.post(
            "/api/v1/reports/report-1/share",
            json={"expires_in_days": 7},
        )
        list_response = client.get("/api/v1/reports/report-1/shares")
        delete_response = client.delete("/api/v1/shares/share-1")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 404
    assert list_response.status_code == 404
    assert delete_response.status_code == 404


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("compliance_viewer", 403),
        ("report_exporter", 200),
        ("admin", 200),
    ],
)
def test_share_creation_enforces_export_role_matrix(monkeypatch, role, expected_status):
    report = _build_report()
    restricted_template = _build_template(
        "tpl-1",
        None,
        required_roles=["report_exporter"],
    )
    created_share = SimpleNamespace(
        id="share-1",
        tenant_id="tenant-a",
        report_id="report-1",
        share_token="token-1",
        expires_at=datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc),
        password_hash=None,
        access_count=0,
        last_accessed_at=None,
        created_at=datetime(2026, 3, 28, 12, 0, 0, tzinfo=timezone.utc),
    )
    fake_db = _FakeTenantDB(all_values=[report, restricted_template])
    captured = {}

    def fake_create_share(self, db, report_id, tenant_id, expires_in_days, password, created_by=None):
        captured["create_share"] = {
            "db": db,
            "report_id": report_id,
            "tenant_id": tenant_id,
            "expires_in_days": expires_in_days,
            "password": password,
            "created_by": created_by,
        }
        return created_share

    monkeypatch.setattr(shares_api.ShareService, "create_share", fake_create_share)

    app = FastAPI()
    app.include_router(shares_api.router, prefix="/api/v1")

    def override_tenant_session():
        yield fake_db

    app.dependency_overrides[shares_api.get_current_tenant] = lambda: "tenant-a"
    app.dependency_overrides[shares_api.get_current_payload] = lambda: _payload(role)
    app.dependency_overrides[shares_api.get_tenant_session] = override_tenant_session

    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/reports/report-1/share",
            json={"expires_in_days": 7},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json()["share_token"] == "token-1"
        assert captured["create_share"]["tenant_id"] == "tenant-a"
        assert captured["create_share"]["created_by"] == "user-123"
    else:
        assert response.json()["detail"] == "Required report template role not found"
        assert "create_share" not in captured
