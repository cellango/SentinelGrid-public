#!/bin/bash
# Run Compliance Platform Migrations
# Executes all compliance-related database migrations in order

set -e

# Configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-sentinelgrid}"
POSTGRES_DB="${POSTGRES_DB:-sentinelgrid}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="${SCRIPT_DIR}/../backend/migrations"

echo "========================================="
echo "  Compliance Platform - Run Migrations"
echo "========================================="
echo ""
echo "Database: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "User: ${POSTGRES_USER}"
echo ""

# Check if PostgreSQL is accessible
echo "Checking database connection..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "SELECT version();" \
    > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Database connection successful"
else
    echo "✗ Database connection failed"
    echo "Please check your database credentials"
    exit 1
fi

# List of compliance migrations in order
MIGRATIONS=(
    "026_platform_audit_logs.sql"
    "027_access_review_campaigns.sql"
    "028_jml_workflows.sql"
    "029_mfa_enforcement_policies.sql"
    "030_compliance_control_library.sql"
    "031_evidence_repository.sql"
    "035_report_scheduling_and_storage.sql"
)

echo ""
echo "Running ${#MIGRATIONS[@]} compliance migrations..."
echo ""

# Run each migration
for migration in "${MIGRATIONS[@]}"; do
    migration_file="${MIGRATIONS_DIR}/${migration}"
    
    if [ ! -f "$migration_file" ]; then
        echo "✗ Migration file not found: ${migration}"
        exit 1
    fi
    
    echo "Running: ${migration}..."
    
    PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -f "$migration_file" \
        -q
    
    if [ $? -eq 0 ]; then
        echo "✓ ${migration} completed successfully"
    else
        echo "✗ ${migration} failed"
        exit 1
    fi
    
    echo ""
done

# Verify tables created
echo "Verifying tables created..."
echo ""

EXPECTED_TABLES=(
    "platform_audit_logs"
    "audit_retention_policies"
    "access_review_campaigns"
    "access_review_items"
    "jml_workflows"
    "jml_workflow_steps"
    "mfa_enforcement_policies"
    "user_mfa_status"
    "compliance_frameworks"
    "compliance_controls"
    "control_mappings"
    "tenant_control_status"
    "evidence_packages"
    "evidence_items"
    "generated_reports"
    "report_schedules"
    "report_access_log"
    "report_llm_documents"
)

MISSING_TABLES=()

for table in "${EXPECTED_TABLES[@]}"; do
    TABLE_EXISTS=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql \
        -h "$POSTGRES_HOST" \
        -p "$POSTGRES_PORT" \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '${table}';")
    
    if [ "$TABLE_EXISTS" -eq 1 ]; then
        echo "✓ ${table}"
    else
        echo "✗ ${table} - NOT FOUND"
        MISSING_TABLES+=("$table")
    fi
done

echo ""

if [ ${#MISSING_TABLES[@]} -eq 0 ]; then
    echo "========================================="
    echo "  ✓ All migrations completed successfully!"
    echo "========================================="
    echo ""
    echo "Tables created: ${#EXPECTED_TABLES[@]}"
    echo ""
    echo "Next steps:"
    echo "1. Deploy Qdrant: docker run -d -p 6333:6333 qdrant/qdrant"
    echo "2. Install dependencies: cd backend/services/reporting_service && pip install -r requirements.txt"
    echo "3. Configure backups: crontab -e (see docs/archive/reference/infrastructure/compliance-deployment-quickstart.md)"
    echo "4. Run tests: pytest backend/tests/compliance/test_tenant_isolation.py -v"
    echo ""
else
    echo "========================================="
    echo "  ✗ Some tables were not created"
    echo "========================================="
    echo ""
    echo "Missing tables:"
    for table in "${MISSING_TABLES[@]}"; do
        echo "  - ${table}"
    done
    echo ""
    exit 1
fi

# Show frameworks seeded
echo "Checking compliance frameworks..."
FRAMEWORK_COUNT=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -t -c "SELECT COUNT(*) FROM compliance_frameworks;")

echo "Compliance frameworks seeded: ${FRAMEWORK_COUNT}"
echo ""

if [ "$FRAMEWORK_COUNT" -ge 5 ]; then
    echo "✓ Expected frameworks found (SOC2, NIST_CSF, HIPAA, PCI_DSS, CMMC)"
else
    echo "✗ Expected 5+ frameworks, found ${FRAMEWORK_COUNT}"
fi

echo ""
echo "Deployment complete! 🎉"

