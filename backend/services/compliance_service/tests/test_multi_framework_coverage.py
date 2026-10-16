from pathlib import Path
import os
import sys

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

os.environ.setdefault("DB_HOST", "localhost")

from app.services.framework_catalog import load_framework_catalog
from app.services import multi_framework_coverage as coverage_service


TENANT_ID = "00000000-0000-0000-0000-000000000111"
EMPTY_INPUTS = {
    "iam_rows": [],
    "posture_rows": [],
    "alerts": [],
    "playbooks": [],
    "executions": [],
}


def test_multi_framework_coverage_returns_selected_soc2_and_catalog_framework(monkeypatch):
    def fake_list_selections(db, tenant_id):
        return {
            "tenant_id": tenant_id,
            "items": [
                {"framework_id": "soc2", "framework_name": "SOC 2", "runtime_support": "readiness", "status": "active"},
                {"framework_id": "hipaa", "framework_name": "HIPAA", "runtime_support": "catalog", "status": "active"},
            ],
        }

    monkeypatch.setattr(coverage_service.framework_selection_service, "list_selections", fake_list_selections)

    payload = coverage_service.build_multi_framework_coverage_payload(
        db=object(),
        tenant_id=TENANT_ID,
        inputs=EMPTY_INPUTS,
        limit=2,
        offset=0,
    )

    assert payload["tenant_id"] == TENANT_ID
    assert [item["framework_id"] for item in payload["items"]] == ["soc2", "hipaa"]
    assert payload["items"][0]["status"] == "not_started"
    assert payload["items"][0]["control_count"] == 9
    assert payload["items"][1]["runtime_support"] == "catalog"
    assert payload["items"][1]["returned_control_count"] == 2
    assert payload["items"][1]["controls"][0]["status"] == "not_started"
    assert "signal and evidence mapping are not active" in payload["items"][1]["controls"][0]["trace"][0]


def test_multi_framework_coverage_defaults_to_soc2_when_no_selection(monkeypatch):
    monkeypatch.setattr(
        coverage_service.framework_selection_service,
        "list_selections",
        lambda db, tenant_id: {"tenant_id": tenant_id, "items": []},
    )

    payload = coverage_service.build_multi_framework_coverage_payload(
        db=object(),
        tenant_id=TENANT_ID,
        inputs=EMPTY_INPUTS,
    )

    assert payload["count"] == 1
    assert payload["items"][0]["framework_id"] == "soc2"
    assert payload["items"][0]["selection_source"] == "default_soc2_readiness"


def test_framework_coverage_and_control_status_for_catalog_framework(monkeypatch):
    def fake_list_selections(db, tenant_id):
        return {
            "tenant_id": tenant_id,
            "items": [
                {"framework_id": "hipaa", "framework_name": "HIPAA", "runtime_support": "catalog", "status": "active"},
            ],
        }

    monkeypatch.setattr(coverage_service.framework_selection_service, "list_selections", fake_list_selections)
    hipaa_control = load_framework_catalog()["hipaa"]["controls"][0]["control_id"]

    framework_payload = coverage_service.build_framework_coverage_payload(
        db=object(),
        tenant_id=TENANT_ID,
        framework_id="hipaa",
        inputs=EMPTY_INPUTS,
        limit=1,
        offset=0,
    )
    control_payload = coverage_service.build_control_status_payload(
        db=object(),
        tenant_id=TENANT_ID,
        control_id=hipaa_control,
        inputs=EMPTY_INPUTS,
        framework_id="hipaa",
    )

    assert framework_payload is not None
    assert framework_payload["framework_id"] == "hipaa"
    assert framework_payload["returned_control_count"] == 1
    assert control_payload is not None
    assert control_payload["count"] == 1
    assert control_payload["items"][0]["control_id"] == hipaa_control

