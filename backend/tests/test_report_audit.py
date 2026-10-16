import os
import sys
import pytest

# Make reporting_service importable
REPORTING_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "reporting_service"))
if REPORTING_ROOT not in sys.path:
    sys.path.insert(0, REPORTING_ROOT)
LIBS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "libs"))
if LIBS_ROOT not in sys.path:
    sys.path.insert(0, LIBS_ROOT)

from app.services.report_generator import ReportGeneratorService  # type: ignore
from app.models.report import ReportFormat  # type: ignore


class FakeSession:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def add(self, *args, **kwargs):
        return None

    def close(self):
        return None


class FakePDFGenerator:
    def generate(self, report_id, template_name, sections, tenant_id, date_range=None):
        return {
            "file_path": f"/tmp/{tenant_id}/{report_id}.pdf",
            "file_size_bytes": 1234,
            "download_url": f"https://files/{tenant_id}/{report_id}.pdf",
        }


@pytest.mark.asyncio
async def test_report_generation_logs_audit(monkeypatch):
    service = ReportGeneratorService()
    service.pdf_generator = FakePDFGenerator()
    service.csv_generator = FakePDFGenerator()

    audit_calls = []

    async def fake_audit(payload):
        audit_calls.append(payload)

    service.audit_client.log_event = fake_audit  # type: ignore
    vector_calls = []

    async def fake_index(**kwargs):
        vector_calls.append(kwargs)

    service.vector_client.index_report = fake_index  # type: ignore

    # Minimal report/template
    class Obj:
        pass

    report = Obj()
    report.id = "r1"
    report.name = "Test SOC2"
    report.format = ReportFormat.PDF
    report.sections = []

    template = Obj()
    template.id = "tpl1"
    template.name = "SOC2 Coverage"
    template.sections = [{"title": "Overview", "widget": "text", "data_source": ""}]

    tenant_id = "tenant-demo"
    realm = "demo"
    session = FakeSession()

    await service.generate_report(session, report, template, tenant_id, realm_name=realm)

    assert audit_calls, "Audit should be invoked"
    payload = audit_calls[0]
    assert payload["tenant_id"] == tenant_id
    assert payload["realm_name"] == realm
    assert payload["action"] == "report_generated"
    assert payload["resource_type"] == "report"
    assert payload["success"] is True
    assert payload["metadata"]["template_id"] == template.id
    assert payload["metadata"]["download_url"]
    # Vectorization should be attempted with tenant + realm
    assert vector_calls, "Vectorization should be invoked"
    vec_args = vector_calls[0]
    assert vec_args["tenant_id"] == tenant_id
    assert vec_args["realm_name"] == realm
    assert vec_args["report_id"] == report.id
