from __future__ import annotations

import pytest
from pathlib import Path
import sys

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.services.compliance_report_data import ComplianceReportDataProvider
from app.services.report_generator import ReportGeneratorService
from app.models.report import ReportFormat


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeAsyncClient:
    calls = []

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.get("timeout")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    async def get(self, url, headers=None, params=None):
        self.calls.append({"url": url, "headers": headers or {}, "params": params or {}})
        if url.endswith("/api/v1/compliance/framework-selections"):
            return FakeResponse(
                {
                    "items": [
                        {
                            "framework_id": "soc2",
                            "framework_name": "SOC 2",
                            "status": "active",
                        }
                    ]
                }
            )
        if url.endswith("/api/v1/compliance/frameworks/soc2/coverage"):
            return FakeResponse(
                {
                    "framework_id": "soc2",
                    "controls": [
                        {
                            "control_id": "CC6.1",
                            "title": "Logical access",
                            "status": "needs_evidence",
                            "gaps": [{"reason": "Pending review"}],
                        }
                    ],
                }
            )
        if url.endswith("/api/v1/compliance/controls/CC6.1/status"):
            return FakeResponse({"control_id": "CC6.1", "items": [{"status": "needs_evidence"}]})
        if url.endswith("/api/v1/compliance/evidence/packages/pkg-1"):
            return FakeResponse(
                {
                    "id": "pkg-1",
                    "package_name": "SOC 2 Q2 Evidence",
                    "items": [
                        {
                            "id": "ev-1",
                            "review_status": "accepted",
                            "valid_until": "2026-07-01T00:00:00Z",
                        },
                        {
                            "id": "ev-2",
                            "review_status": "ready_for_review",
                            "valid_until": "2026-07-01T00:00:00Z",
                        },
                    ],
                }
            )
        if url.endswith("/api/v1/compliance/evidence"):
            return FakeResponse({"items": [], "count": 0})
        return FakeResponse({})


class FakeDB:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1


class FakePDFGenerator:
    def __init__(self):
        self.sections = []

    def generate(self, report_id, template_name, sections, tenant_id, date_range=None):
        self.sections = sections
        return {
            "file_path": f"/tmp/{report_id}.pdf",
            "file_size_bytes": 100,
            "download_url": f"https://reports.example/{report_id}.pdf",
        }


class FakeProvider:
    async def build_snapshot(self, **kwargs):
        return {
            "snapshot_hash_sha256": "abc123",
            "source": "compliance_report_data_provider",
            "evidence_summary": {
                "evidence_package_ids": ["pkg-1"],
                "evidence_package_count": 1,
                "evidence_item_count": 2,
                "accepted_evidence_item_count": 1,
            },
            "coverage_snapshots": [
                {
                    "framework_id": "soc2",
                    "framework_name": "SOC 2",
                    "status": "needs_evidence",
                    "controls": [
                        {
                            "control_id": "CC6.1",
                            "title": "Logical access",
                            "status": "needs_evidence",
                            "gaps": [{"reason": "Pending review"}],
                        }
                    ],
                }
            ],
            "evidence_packages": [
                {
                    "id": "pkg-1",
                    "package_name": "SOC 2 Q2 Evidence",
                    "items": [
                        {
                            "id": "ev-1",
                            "title": "MFA export",
                            "evidence_type": "configuration",
                            "review_status": "accepted",
                            "valid_until": "2026-07-01T00:00:00Z",
                            "control_links": [
                                {
                                    "control_ref": "CC6.1",
                                    "control_name": "Logical access",
                                    "framework_code": "soc2",
                                    "framework_name": "SOC 2",
                                }
                            ],
                        }
                    ],
                }
            ],
        }


@pytest.mark.asyncio
async def test_compliance_report_data_provider_builds_traceable_snapshot(monkeypatch):
    FakeAsyncClient.calls = []
    monkeypatch.setattr("app.services.compliance_report_data.httpx.AsyncClient", FakeAsyncClient)
    provider = ComplianceReportDataProvider("http://compliance_service:8000", "internal-token")

    snapshot = await provider.build_snapshot(
        tenant_id="tenant-123",
        date_range={"start": "2026-04-01", "end": "2026-06-30"},
        report_parameters={
            "framework_ids": ["soc2"],
            "control_ids": ["CC6.1"],
            "evidence_package_ids": ["pkg-1"],
            "include_gaps": True,
            "include_expired_evidence": False,
        },
    )

    assert snapshot["inputs"]["framework_ids"] == ["soc2"]
    assert snapshot["selected_frameworks"]["items"][0]["framework_id"] == "soc2"
    assert snapshot["coverage_snapshots"][0]["framework_id"] == "soc2"
    assert snapshot["control_status"][0]["control_id"] == "CC6.1"
    assert snapshot["evidence_summary"]["evidence_package_ids"] == ["pkg-1"]
    assert snapshot["evidence_summary"]["accepted_evidence_item_count"] == 1
    assert snapshot["control_gaps"][0]["control_id"] == "CC6.1"
    assert len(snapshot["snapshot_hash_sha256"]) == 64
    assert FakeAsyncClient.calls[0]["headers"]["X-Tenant-ID"] == "tenant-123"


@pytest.mark.asyncio
async def test_report_generator_persists_compliance_snapshot_metadata(monkeypatch):
    service = ReportGeneratorService()
    service.pdf_generator = FakePDFGenerator()
    service.csv_generator = FakePDFGenerator()
    service.compliance_data_provider = FakeProvider()
    service.audit_client.log_event = lambda payload: None
    service.vector_client.index_report = lambda **kwargs: None

    async def noop_async(*args, **kwargs):
        return None

    service.audit_client.log_event = noop_async
    service.vector_client.index_report = noop_async

    class Obj:
        pass

    report = Obj()
    report.id = "report-1"
    report.name = "SOC 2 Evidence Summary"
    report.format = ReportFormat.PDF
    report.sections = []
    report.report_metadata = {"template_key": "soc_2_evidence_summary"}

    template = Obj()
    template.id = "tpl-1"
    template.name = "SOC 2 Evidence Summary"
    template.type = "soc2"
    template.sections = [{"title": "Coverage", "widget": "metrics_summary", "data_source": ""}]

    await service.generate_report(
        FakeDB(),
        report,
        template,
        "tenant-123",
        realm_name="demo",
        date_range={"start": "2026-04-01", "end": "2026-06-30"},
        report_parameters={
            "framework_ids": ["soc2"],
            "evidence_package_ids": ["pkg-1"],
            "include_gaps": True,
        },
    )

    assert "Evidence Basis" in report.sections
    assert "SOC 2 Coverage Snapshot" in report.sections
    assert "Control Evidence Mapping" in report.sections
    mapping_section = next(section for section in service.pdf_generator.sections if section["widget"] == "control_evidence_mapping")
    assert mapping_section["data"]["summary"]["mapped_control_count"] == 1
    assert mapping_section["data"]["rows"][0]["evidence_item_id"] == "ev-1"
    assert report.report_metadata["compliance_snapshot_hash_sha256"] == "abc123"
    assert report.report_metadata["evidence_package_ids"] == ["pkg-1"]
    assert report.report_metadata["report_inputs"]["framework_ids"] == ["soc2"]
