from pathlib import Path
import sys
from uuid import uuid4

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.services.launch_demo_seed import ComplianceLaunchDemoSeedService  # noqa: E402


class FakeResult:
    def __init__(self, *, first_row=None):
        self._first_row = first_row

    def first(self):
        return self._first_row

    def mappings(self):
        return self


class FakeDB:
    def __init__(self, tenant_row):
        self.tenant_row = tenant_row
        self.calls = []
        self.commits = 0

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).split()).lower()
        self.calls.append({"sql": sql, "params": params or {}})
        if "from tenants" in sql:
            return FakeResult(first_row=self.tenant_row)
        return FakeResult()

    def commit(self):
        self.commits += 1


def test_launch_demo_seed_dry_run_builds_complete_customer_journey_without_writes():
    tenant_id = str(uuid4())
    db = FakeDB(
        {
            "tenant_id": tenant_id,
            "tenant_slug": "demo",
            "tenant_name": "Demo Tenant",
            "realm_name": "demo",
        }
    )

    result = ComplianceLaunchDemoSeedService().run(db, tenant_slug="demo", dry_run=True)
    payload = result.as_dict()

    assert payload["dry_run"] is True
    assert payload["tenant_id"] == tenant_id
    assert payload["framework_selections_planned"] == 3
    assert [item["framework_id"] for item in payload["planned_framework_selections"]] == [
        "soc2",
        "hipaa",
        "pci_dss",
    ]
    assert payload["evidence_packages_planned"] == 1
    assert payload["evidence_items_planned"] == 2
    assert payload["collection_tasks_planned"] == 1
    assert payload["reports_planned"] == 1
    assert payload["recommendations_planned"] == 1
    assert payload["planned_reports"][0]["metadata"]["report_inputs"]["evidence_package_ids"] == [
        payload["planned_evidence_packages"][0]["id"]
    ]
    assert payload["planned_recommendations"][0]["framework_id"] == "hipaa"
    assert db.commits == 0
    assert not any("insert into" in call["sql"] for call in db.calls)
