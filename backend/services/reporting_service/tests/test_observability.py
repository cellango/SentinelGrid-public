"""Focused observability coverage for reporting-service compliance report metrics."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))


def _install_apscheduler_stub() -> None:
    if "apscheduler" in sys.modules:
        return

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


_install_apscheduler_stub()

from app.core.config import settings

os.makedirs(settings.REPORT_STORAGE_PATH, exist_ok=True)

from app.main import app
from app.models.report import ReportFormat, ReportStatus
from app.services.observability import record_report_generation
from app.services.report_generator import ReportGeneratorService
from sg_core.service_metrics import get_service_metrics, reset_service_metrics


class _FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class _FakePDFGenerator:
    def __init__(self, *, fail: bool = False):
        self.fail = fail

    def generate(self, report_id, template_name, sections, tenant_id, date_range=None):
        if self.fail:
            raise RuntimeError("renderer unavailable")
        return {
            "file_path": f"/tmp/{report_id}.pdf",
            "file_size_bytes": 128,
            "download_url": f"https://reports.example/{report_id}.pdf",
        }


async def _noop_async(*args, **kwargs):
    return None


def _build_report_template_pair():
    report = SimpleNamespace(
        id="report-1",
        name="Executive Summary",
        format=ReportFormat.PDF,
        status=ReportStatus.PENDING,
        generated_by="user-123",
        sections=[],
        report_metadata={},
    )
    template = SimpleNamespace(
        id="tpl-1",
        name="Executive Summary",
        type="executive",
        sections=[],
    )
    return report, template


def test_reporting_metrics_endpoints_render_runtime_snapshot_and_prometheus():
    reset_service_metrics("reporting-service")
    record_report_generation(outcome="failed", report_format="pdf", template_type="compliance")

    client = TestClient(app, raise_server_exceptions=False)
    snapshot_response = client.get("/metrics")
    prometheus_response = client.get("/metrics/prometheus")

    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["service"] == "reporting-service"
    assert snapshot["counters"]["compliance_report_generation_total"]["series"][
        "outcome=failed,report_format=pdf,template_type=compliance"
    ] == 1
    assert snapshot["counters"]["compliance_report_generation_failures_total"]["series"][
        "report_format=pdf,template_type=compliance"
    ] == 1

    assert prometheus_response.status_code == 200
    assert prometheus_response.headers["content-type"].startswith("text/plain")
    assert (
        'compliance_report_generation_total{outcome="failed",report_format="pdf",'
        'service="reporting-service",template_type="compliance"} 1.0'
    ) in prometheus_response.text
    assert (
        'compliance_report_generation_failures_total{report_format="pdf",'
        'service="reporting-service",template_type="compliance"} 1.0'
    ) in prometheus_response.text


@pytest.mark.asyncio
async def test_report_generator_records_success_metric():
    reset_service_metrics("reporting-service")
    service = ReportGeneratorService()
    service.pdf_generator = _FakePDFGenerator()
    service.audit_client.log_event = _noop_async
    service.vector_client.index_report = _noop_async
    report, template = _build_report_template_pair()

    await service.generate_report(_FakeDB(), report, template, "tenant-a", realm_name="demo")

    metrics = get_service_metrics("reporting-service").snapshot()
    assert metrics["counters"]["compliance_report_generation_total"]["series"][
        "outcome=success,report_format=pdf,template_type=executive"
    ] == 1
    assert "compliance_report_generation_failures_total" not in metrics["counters"]


@pytest.mark.asyncio
async def test_report_generator_records_failure_metric():
    reset_service_metrics("reporting-service")
    service = ReportGeneratorService()
    service.pdf_generator = _FakePDFGenerator(fail=True)
    service.audit_client.log_event = _noop_async
    service.vector_client.index_report = _noop_async
    report, template = _build_report_template_pair()

    with pytest.raises(RuntimeError):
        await service.generate_report(_FakeDB(), report, template, "tenant-a", realm_name="demo")

    metrics = get_service_metrics("reporting-service").snapshot()
    assert metrics["counters"]["compliance_report_generation_total"]["series"][
        "outcome=failed,report_format=pdf,template_type=executive"
    ] == 1
    assert metrics["counters"]["compliance_report_generation_failures_total"]["series"][
        "report_format=pdf,template_type=executive"
    ] == 1
