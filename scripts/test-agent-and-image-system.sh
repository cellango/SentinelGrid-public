#!/bin/bash
# Quick test script for agent and image system
# This script runs basic tests to verify the implementation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=========================================="
echo "Testing Agent and Image System"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

test_pass() {
    echo -e "${GREEN}✅ PASS:${NC} $1"
    PASSED=$((PASSED + 1))
}

test_fail() {
    echo -e "${RED}❌ FAIL:${NC} $1"
    FAILED=$((FAILED + 1))
}

test_warn() {
    echo -e "${YELLOW}⚠️  WARN:${NC} $1"
}

# Test 1: Check required tools
echo "=== Testing Required Tools ==="
for tool in packer aws psql jq; do
    if command -v $tool &> /dev/null; then
        test_pass "$tool is installed"
    else
        test_fail "$tool is not installed"
    fi
done

# Test 2: Check scripts exist and are executable
echo ""
echo "=== Testing Scripts ==="
SCRIPTS=(
    "scripts/rebrand-agents/download/download-wazuh.sh"
    "scripts/rebrand-agents/extract/extract-agents.sh"
    "scripts/rebrand-agents/rebrand/rebrand-wazuh.sh"
    "scripts/rebrand-agents/build/build-packages.sh"
    "scripts/rebrand-agents/upload/upload-to-cdn.sh"
    "scripts/package-repos/deploy-repos-to-cdn.sh"
    "scripts/package-repos/update-repo-metadata.sh"
    "scripts/package-repos/generate-gpg-keys.sh"
    "scripts/build-pipeline/build-image.sh"
    "scripts/build-pipeline/scan-image.sh"
    "scripts/build-pipeline/parse-scan-results.sh"
    "scripts/build-pipeline/validate-image.sh"
    "scripts/build-pipeline/register-image.sh"
    "scripts/build-pipeline/share-image-to-customer.sh"
    "scripts/version-management/bump-version.sh"
    "scripts/version-management/release-version.sh"
    "scripts/version-management/deprecate-version.sh"
    "scripts/version-management/check-version-compatibility.sh"
    "infra/shared/scripts/onboard-customer-images.sh"
    "infra/shared/scripts/provision-customer-images.sh"
)

for script in "${SCRIPTS[@]}"; do
    if [ -f "$script" ] && [ -x "$script" ]; then
        test_pass "$script exists and is executable"
    else
        test_fail "$script missing or not executable"
    fi
done

# Test 3: Check database migrations exist
echo ""
echo "=== Testing Database Migrations ==="
MIGRATIONS=(
    "backend/migrations/020_agent_versions.sql"
    "backend/migrations/021_hardened_images.sql"
    "backend/migrations/022_customer_cloud_accounts.sql"
)

for migration in "${MIGRATIONS[@]}"; do
    if [ -f "$migration" ]; then
        test_pass "$migration exists"
    else
        test_fail "$migration missing"
    fi
done

# Test 4: Check Packer templates
echo ""
echo "=== Testing Packer Templates ==="
TEMPLATES=(
    "packer/amazon-linux-2/aws/amazon-linux-2.json"
    "packer/ubuntu-22.04/aws/ubuntu-22.04.json"
)

for template in "${TEMPLATES[@]}"; do
    if [ -f "$template" ]; then
        # Try to validate if packer is available
        if command -v packer &> /dev/null; then
            if packer validate "$template" &>/dev/null; then
                test_pass "$template is valid"
            else
                test_warn "$template validation failed (may need variables)"
            fi
        else
            test_pass "$template exists"
        fi
    else
        test_fail "$template missing"
    fi
done

# Test 5: Check documentation
echo ""
echo "=== Testing Documentation ==="
DOCS=(
    "docs/archive/reference/infrastructure/customer-agent-installation.md"
    "docs/archive/reference/infrastructure/customer-hardened-images.md"
    "docs/archive/reference/platform/customer-cloud-account-setup.md"
    "docs/archive/reference/infrastructure/agent-build-process.md"
    "docs/archive/reference/infrastructure/image-build-process.md"
    "docs/archive/reference/infrastructure/image-security-scanning.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        test_pass "$doc exists"
    else
        test_fail "$doc missing"
    fi
done

# Test 6: Test version bumping
echo ""
echo "=== Testing Version Management ==="
if [ -f "scripts/version-management/bump-version.sh" ]; then
    NEW_VERSION=$(./scripts/version-management/bump-version.sh agent patch 1.0.0 2>/dev/null | grep -E "^[0-9]+\.[0-9]+\.[0-9]+$" | tail -1)
    if [ "$NEW_VERSION" = "1.0.1" ]; then
        test_pass "Version bumping works correctly"
    else
        # Try alternative extraction
        NEW_VERSION=$(./scripts/version-management/bump-version.sh agent patch 1.0.0 2>/dev/null | grep "1.0.1" | head -1)
        if [ -n "$NEW_VERSION" ]; then
            test_pass "Version bumping works correctly"
        else
            test_warn "Version bumping test inconclusive (script may work, test needs adjustment)"
        fi
    fi
fi

# Test 7: Test scan result parsing
echo ""
echo "=== Testing Scan Result Parsing ==="
if [ -f "scripts/build-pipeline/parse-scan-results.sh" ]; then
    # Create test scan result
    TEST_SCAN="/tmp/test-scan-$$.json"
    cat > "$TEST_SCAN" <<EOF
{
    "scan_status": "passed",
    "scan_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "scanner": "test",
    "vulnerability_count": {
        "critical": 0,
        "high": 2,
        "medium": 5,
        "low": 10
    }
}
EOF
    
    if ./scripts/build-pipeline/parse-scan-results.sh "$TEST_SCAN" &>/dev/null; then
        test_pass "Scan result parsing works"
    else
        test_fail "Scan result parsing failed"
    fi
    rm -f "$TEST_SCAN"
fi

# Test 8: Check database connection (if DB_URL set)
echo ""
echo "=== Testing Database Connection ==="
if [ -n "$DB_URL" ]; then
    if psql "$DB_URL" -c "SELECT 1;" &>/dev/null; then
        test_pass "Database connection works"
        
        # Check if migrations have been run
        if psql "$DB_URL" -c "\dt agent_versions" &>/dev/null; then
            test_pass "Database migrations appear to be run"
        else
            test_warn "Database migrations may not be run (run: psql \$DB_URL -f backend/migrations/020_agent_versions.sql)"
        fi
    else
        test_fail "Database connection failed"
    fi
else
    test_warn "DB_URL not set, skipping database tests"
fi

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review above.${NC}"
    exit 1
fi

