from pathlib import Path
import sys
from uuid import uuid4

SERVICE_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = Path(__file__).resolve().parents[3]

for path in (SERVICE_ROOT, BACKEND_ROOT / "libs"):
    sys.path.insert(0, str(path))

from app.services.phase8_backfill import (  # noqa: E402
    CompliancePhase8BackfillService,
    build_legacy_report_metadata,
)


class FakeResult:
    def __init__(self, *, first_row=None, rows=None):
        self._first_row = first_row
        self._rows = rows or []

    def first(self):
        return self._first_row

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self, *, tenant_rows=None, selection_counts=None, report_rows=None, legacy_report_rows=None):
        self.tenant_rows = tenant_rows or []
        self.selection_counts = selection_counts or {}
        self.report_rows = report_rows or []
        self.legacy_report_rows = legacy_report_rows or []
        self.calls = []
        self.inserted_selections = []
        self.updated_reports = []
        self.updated_legacy_reports = []
        self.commits = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        params = params or {}
        self.calls.append({"sql": sql, "params": params})
        normalized_sql = " ".join(sql.split()).lower()

        if "from tenants t" in normalized_sql:
            return FakeResult(rows=self.tenant_rows)

        if "select count(*) as count from tenant_framework_selections" in normalized_sql:
            tenant_id = params["tenant_id"]
            return FakeResult(first_row={"count": self.selection_counts.get(tenant_id, 0)})

        if normalized_sql.startswith("insert into tenant_framework_selections"):
            self.inserted_selections.append(dict(params))
            return FakeResult()

        if "from reporting.generated_reports r" in normalized_sql:
            return FakeResult(rows=self.legacy_report_rows)

        if "from reporting.reports r" in normalized_sql:
            return FakeResult(rows=self.report_rows)

        if normalized_sql.startswith("update reporting.generated_reports"):
            self.updated_legacy_reports.append(dict(params))
            return FakeResult()

        if normalized_sql.startswith("update reporting.reports"):
            self.updated_reports.append(dict(params))
            return FakeResult()

        return FakeResult()

    def commit(self):
        self.commits += 1


def test_phase8_backfill_dry_run_plans_trust_profile_legacy_soc2_and_report_metadata():
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    tenant_c = str(uuid4())
    db = FakeDB(
        tenant_rows=[
            {
                "tenant_id": tenant_a,
                "tenant_services": {},
                "onboarding_services": {"trustProfile": {"frameworks": ["soc2", "iso27001", "unknown"]}},
            },
            {"tenant_id": tenant_b, "tenant_services": {}, "onboarding_services": {}},
            {
                "tenant_id": tenant_c,
                "tenant_services": {"trustProfile": {"frameworks": ["hipaa"]}},
                "onboarding_services": {},
            },
        ],
        selection_counts={tenant_c: 1},
        report_rows=[
            {
                "id": "report-1",
                "tenant_id": tenant_a,
                "name": "SOC 2 Coverage Report",
                "metadata": {},
                "template_type": "soc2",
                "template_name": "SOC 2 Coverage",
            },
            {
                "id": "report-2",
                "tenant_id": tenant_b,
                "name": "Operations Summary",
                "metadata": {},
                "template_type": "executive",
                "template_name": "Operations Summary",
            },
        ],
        legacy_report_rows=[
            {
                "id": str(uuid4()),
                "tenant_id": tenant_b,
                "name": "Legacy SOC2 Report",
                "report_type": "soc2_coverage",
                "metadata": {},
            }
        ],
    )

    result = CompliancePhase8BackfillService().run(db, dry_run=True)
    payload = result.as_dict()

    assert payload["dry_run"] is True
    assert payload["tenants_seen"] == 3
    assert payload["tenants_seeded_from_trust_profile"] == 1
    assert payload["tenants_seeded_from_legacy_soc2"] == 1
    assert payload["tenants_with_existing_selections"] == 1
    assert payload["framework_selection_rows_planned"] == 3
    assert payload["framework_selection_rows_written"] == 0
    assert [item["framework_id"] for item in payload["planned_framework_selections"]] == [
        "soc2",
        "iso27001",
        "soc2",
    ]
    assert payload["planned_framework_selections"][1]["status"] == "evaluating"
    assert payload["reports_seen"] == 2
    assert payload["reports_planned"] == 1
    assert payload["legacy_generated_reports_seen"] == 1
    assert payload["legacy_generated_reports_planned"] == 1
    assert payload["evidence_items_created"] == 0
    assert db.inserted_selections == []
    assert db.updated_reports == []
    assert db.updated_legacy_reports == []
    assert db.commits == 0


def test_phase8_backfill_apply_writes_only_metadata_and_framework_selection_rows():
    tenant_id = str(uuid4())
    legacy_report_id = str(uuid4())
    db = FakeDB(
        tenant_rows=[
            {
                "tenant_id": tenant_id,
                "tenant_services": {"trustProfile": {"frameworks": ["hipaa"]}},
                "onboarding_services": {},
            }
        ],
        report_rows=[
            {
                "id": "report-1",
                "tenant_id": tenant_id,
                "name": "HIPAA Compliance Report",
                "metadata": {"template_key": "hipaa_compliance"},
                "template_type": "compliance",
                "template_name": "HIPAA Compliance Report",
            }
        ],
        legacy_report_rows=[
            {
                "id": legacy_report_id,
                "tenant_id": tenant_id,
                "name": "Legacy SOC2 Report",
                "report_type": "soc2_coverage",
                "metadata": {},
            }
        ],
    )

    result = CompliancePhase8BackfillService().run(db, dry_run=False)

    assert result.framework_selection_rows_written == 1
    assert db.inserted_selections[0]["framework_id"] == "hipaa"
    assert db.inserted_selections[0]["source"] == "onboarding_trust_profile"
    assert result.reports_written == 1
    assert result.legacy_generated_reports_written == 1
    assert result.evidence_items_created == 0
    assert "evidence_items" not in " ".join(call["sql"].lower() for call in db.calls)
    assert '"evidence_items_created": 0' in db.updated_reports[0]["metadata"]
    assert '"framework_ids": ["hipaa"]' in db.updated_reports[0]["metadata"]
    assert '"framework_ids": ["soc2"]' in db.updated_legacy_reports[0]["metadata"]
    assert db.commits == 1


def test_legacy_report_metadata_backfill_preserves_existing_snapshot_hash_and_marks_no_evidence_backfill():
    already_snapshotted = build_legacy_report_metadata(
        {
            "id": "report-1",
            "name": "SOC 2 Report",
            "metadata": {"compliance_snapshot": {"snapshot_hash_sha256": "abc123"}},
        }
    )
    assert already_snapshotted is None

    metadata = build_legacy_report_metadata(
        {
            "id": "report-2",
            "name": "PCI DSS Audit Report",
            "metadata": {},
            "template_type": "compliance",
        }
    )

    assert metadata is not None
    assert metadata["report_inputs"]["framework_ids"] == ["pci_dss"]
    assert metadata["compliance_snapshot"]["status"] == "legacy_metadata_only"
    assert metadata["compliance_snapshot"]["snapshot_hash_sha256"] is None
    assert metadata["phase8_migration_backfill"]["evidence_items_created"] == 0
    assert metadata["phase8_migration_backfill"]["evidence_backfilled"] is False
