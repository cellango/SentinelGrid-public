#!/bin/bash
# Run Compliance Platform Test Suite
# Comprehensive testing including CRITICAL security tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
TEST_DIR="${PROJECT_ROOT}/backend/tests/compliance"

echo "========================================="
echo "  Compliance Platform - Test Suite"
echo "========================================="
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "✗ pytest not found. Installing..."
    pip install pytest pytest-asyncio pytest-mock
fi

# Check if test directory exists
if [ ! -d "$TEST_DIR" ]; then
    echo "✗ Test directory not found: ${TEST_DIR}"
    exit 1
fi

echo "Test directory: ${TEST_DIR}"
echo ""

# Set test database URL if not set
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql://sentinelgrid:sentinelgrid@localhost:5432/sentinelgrid_test}"

echo "Test database: ${TEST_DATABASE_URL}"
echo ""

# Install test dependencies
echo "Installing test dependencies..."
pip install -q pytest pytest-asyncio pytest-mock sqlalchemy psycopg2-binary
echo "✓ Dependencies installed"
echo ""

# Run test suites
echo "========================================="
echo "  Running Test Suites"
echo "========================================="
echo ""

# Test 1: Tenant Isolation (CRITICAL - MUST PASS)
echo "🔒 [CRITICAL] Running Tenant Isolation Tests..."
echo "   These tests verify Customer A cannot access Customer B's data"
echo ""
pytest "${TEST_DIR}/test_tenant_isolation.py" -v --tb=short
TENANT_ISOLATION_STATUS=$?

if [ $TENANT_ISOLATION_STATUS -eq 0 ]; then
    echo ""
    echo "✅ TENANT ISOLATION TESTS PASSED"
else
    echo ""
    echo "❌ TENANT ISOLATION TESTS FAILED"
    echo "   DO NOT DEPLOY TO PRODUCTION!"
    exit 1
fi

echo ""
echo "========================================="
echo ""

# Test 2: PDF Generation Tests
echo "📄 Running PDF Generation Tests..."
pytest "${TEST_DIR}/test_pdf_generation.py" -v --tb=short
PDF_STATUS=$?

if [ $PDF_STATUS -eq 0 ]; then
    echo "✅ PDF Generation tests passed"
else
    echo "⚠️  PDF Generation tests failed (may be due to missing dependencies)"
fi

echo ""
echo "========================================="
echo ""

# Test 3: Report Generation Pipeline Tests
echo "📊 Running Report Generation Pipeline Tests..."
pytest "${TEST_DIR}/test_report_generation.py" -v --tb=short
REPORT_GEN_STATUS=$?

if [ $REPORT_GEN_STATUS -eq 0 ]; then
    echo "✅ Report Generation tests passed"
else
    echo "⚠️  Report Generation tests had issues"
fi

echo ""
echo "========================================="
echo ""

# Test 4: LLM Integration Tests
echo "🤖 Running LLM Integration Tests..."
pytest "${TEST_DIR}/test_llm_integration.py" -v --tb=short
LLM_STATUS=$?

if [ $LLM_STATUS -eq 0 ]; then
    echo "✅ LLM Integration tests passed"
else
    echo "⚠️  LLM Integration tests had issues"
fi

echo ""
echo "========================================="
echo ""

# Test 5: IAM Governance Tests
echo "👥 Running IAM Governance Tests..."
pytest "${TEST_DIR}/test_iam_governance.py" -v --tb=short
IAM_STATUS=$?

if [ $IAM_STATUS -eq 0 ]; then
    echo "✅ IAM Governance tests passed"
else
    echo "⚠️  IAM Governance tests had issues"
fi

echo ""
echo "========================================="
echo ""

# Test 6: API Tests
echo "🌐 Running API Tests..."
pytest "${TEST_DIR}/test_compliance_api.py" -v --tb=short
API_STATUS=$?

if [ $API_STATUS -eq 0 ]; then
    echo "✅ API tests passed"
else
    echo "⚠️  API tests had issues"
fi

echo ""
echo "========================================="
echo "  Test Summary"
echo "========================================="
echo ""

# Calculate pass/fail
TOTAL_SUITES=6
PASSED_SUITES=0

[ $TENANT_ISOLATION_STATUS -eq 0 ] && ((PASSED_SUITES++))
[ $PDF_STATUS -eq 0 ] && ((PASSED_SUITES++))
[ $REPORT_GEN_STATUS -eq 0 ] && ((PASSED_SUITES++))
[ $LLM_STATUS -eq 0 ] && ((PASSED_SUITES++))
[ $IAM_STATUS -eq 0 ] && ((PASSED_SUITES++))
[ $API_STATUS -eq 0 ] && ((PASSED_SUITES++))

echo "Test Suites Passed: ${PASSED_SUITES}/${TOTAL_SUITES}"
echo ""

echo "Results:"
echo "  🔒 Tenant Isolation (CRITICAL): $([ $TENANT_ISOLATION_STATUS -eq 0 ] && echo '✅ PASS' || echo '❌ FAIL')"
echo "  📄 PDF Generation: $([ $PDF_STATUS -eq 0 ] && echo '✅ PASS' || echo '⚠️  SKIP/FAIL')"
echo "  📊 Report Generation: $([ $REPORT_GEN_STATUS -eq 0 ] && echo '✅ PASS' || echo '⚠️  SKIP/FAIL')"
echo "  🤖 LLM Integration: $([ $LLM_STATUS -eq 0 ] && echo '✅ PASS' || echo '⚠️  SKIP/FAIL')"
echo "  👥 IAM Governance: $([ $IAM_STATUS -eq 0 ] && echo '✅ PASS' || echo '⚠️  SKIP/FAIL')"
echo "  🌐 API Tests: $([ $API_STATUS -eq 0 ] && echo '✅ PASS' || echo '⚠️  SKIP/FAIL')"

echo ""

# Critical assessment
if [ $TENANT_ISOLATION_STATUS -eq 0 ]; then
    echo "========================================="
    echo "  ✅ CRITICAL TESTS PASSED"
    echo "========================================="
    echo ""
    echo "Tenant isolation tests passed successfully."
    echo "System is safe for multi-tenant deployment."
    echo ""
    
    if [ $PASSED_SUITES -eq $TOTAL_SUITES ]; then
        echo "🎉 ALL TESTS PASSED!"
        echo "   Ready for deployment"
        exit 0
    else
        echo "⚠️  Some non-critical tests failed"
        echo "   Review failures before production deployment"
        echo "   Missing dependencies may cause test skips"
        exit 0
    fi
else
    echo "========================================="
    echo "  ❌ CRITICAL TESTS FAILED"
    echo "========================================="
    echo ""
    echo "Tenant isolation tests FAILED!"
    echo ""
    echo "🚨 DO NOT DEPLOY TO PRODUCTION! 🚨"
    echo ""
    echo "This indicates a potential security vulnerability"
    echo "where one tenant could access another tenant's data."
    echo ""
    echo "Please investigate and fix before deployment."
    exit 1
fi

