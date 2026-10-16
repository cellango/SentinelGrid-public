from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = REPO_ROOT / "backend/migrations_consolidated/V008__evidence_repository_lifecycle.sql"
IDEMPOTENCY_MIGRATION = REPO_ROOT / "backend/migrations_consolidated/V009__evidence_idempotency_keys.sql"
AGENT_RECOMMENDATIONS_MIGRATION = (
    REPO_ROOT / "backend/migrations_consolidated/V010__compliance_agent_recommendations.sql"
)
INTEGRITY_RETENTION_MIGRATION = (
    REPO_ROOT / "backend/migrations_consolidated/V011__evidence_integrity_retention_controls.sql"
)


def _migration_sql() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_evidence_repository_migration_normalizes_required_tables():
    sql = _migration_sql()

    for table_name in (
        "evidence_packages",
        "evidence_items",
        "evidence_control_links",
        "evidence_collection_tasks",
        "evidence_reviews",
        "evidence_exports",
    ):
        assert table_name in sql


def test_evidence_items_have_required_provenance_integrity_and_lifecycle_fields():
    sql = _migration_sql()

    for column_name in (
        "tenant_id",
        "source_system",
        "source_resource_id",
        "collector",
        "collection_method",
        "collected_at",
        "valid_from",
        "valid_until",
        "hash_sha256",
        "storage_uri",
        "summary",
        "sensitivity",
        "review_status",
        "created_by",
        "retention_until",
        "immutable_after",
        "deleted_at",
        "provenance",
        "integrity_metadata",
        "chain_of_custody",
    ):
        assert column_name in sql

    assert "evidence_items_required_fields_check" in sql
    assert "evidence_items_hash_sha256_check" in sql
    assert "not valid" in sql


def test_evidence_repository_has_links_reviews_exports_and_tenant_isolation():
    sql = _migration_sql()

    assert "foreign key (evidence_item_id) references public.evidence_items" in sql
    assert "foreign key (control_id) references public.compliance_controls" in sql
    assert "foreign key (evidence_requirement_id) references public.control_evidence_requirements" in sql
    assert "create table if not exists public.evidence_reviews" in sql
    assert "create table if not exists public.evidence_exports" in sql

    for table_name in (
        "evidence_items",
        "evidence_packages",
        "evidence_collection_tasks",
        "evidence_control_links",
        "evidence_reviews",
        "evidence_exports",
    ):
        assert f"alter table public.{table_name} enable row level security" in sql
        assert f"alter table public.{table_name} force row level security" in sql


def test_evidence_repository_migration_is_schema_only():
    sql = _migration_sql()

    data_statements = re.findall(r"^\s*(insert|update|delete|merge|copy)\b", sql, flags=re.MULTILINE)
    assert data_statements == []


def test_evidence_idempotency_migration_adds_tenant_scoped_unique_keys():
    sql = IDEMPOTENCY_MIGRATION.read_text(encoding="utf-8").lower()

    assert "evidence_items" in sql
    assert "evidence_collection_tasks" in sql
    assert "idempotency_key" in sql
    assert "idx_evidence_items_tenant_idempotency" in sql
    assert "idx_evidence_tasks_tenant_idempotency" in sql
    assert "where idempotency_key is not null and deleted_at is null" in sql
    assert re.findall(r"^\s*(insert|update|delete|merge|copy)\b", sql, flags=re.MULTILINE) == []


def test_compliance_agent_recommendations_migration_is_reviewable_and_schema_only():
    sql = AGENT_RECOMMENDATIONS_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.compliance_agent_recommendations" in sql
    for column_name in (
        "tenant_id",
        "agent_task_id",
        "trigger_type",
        "recommendation_type",
        "state",
        "source_type",
        "framework_id",
        "control_id",
        "evidence_item_id",
        "evidence_package_id",
        "report_id",
        "proposed_actions",
        "requires_approval",
        "decided_by",
        "idempotency_key",
    ):
        assert column_name in sql

    for state in ("draft", "proposed", "accepted", "rejected", "superseded"):
        assert state in sql

    assert "idx_compliance_agent_recommendations_idempotency" in sql
    assert "alter table public.compliance_agent_recommendations enable row level security" in sql
    assert "alter table public.compliance_agent_recommendations force row level security" in sql
    assert re.findall(r"^\s*(insert|update|delete|merge|copy)\b", sql, flags=re.MULTILINE) == []


def test_evidence_integrity_retention_migration_is_schema_only_and_tenant_scoped():
    sql = INTEGRITY_RETENTION_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create table if not exists public.evidence_integrity_verifications" in sql
    assert "create table if not exists public.evidence_retention_policies" in sql
    assert "expected_hash_sha256" in sql
    assert "observed_hash_sha256" in sql
    assert "retention_days" in sql
    assert "legal_hold" in sql
    assert "prevent_completed_evidence_export_mutation" in sql
    assert "completed evidence exports are immutable" in sql

    for table_name in ("evidence_integrity_verifications", "evidence_retention_policies"):
        assert f"alter table public.{table_name} enable row level security" in sql
        assert f"alter table public.{table_name} force row level security" in sql
        assert f"create policy tenant_isolation_select on public.{table_name}" in sql

    assert "idx_evidence_retention_policies_default_unique" in sql
    assert "idx_evidence_retention_policies_framework_unique" in sql
    assert re.findall(r"^\s*(insert|update|delete|merge|copy)\b", sql, flags=re.MULTILINE) == []
