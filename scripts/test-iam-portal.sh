#!/bin/bash
# Quick test script for IAM Portal UI

set -e

echo "🚀 IAM Portal Testing Quick Start"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if services are running
echo "📋 Checking services..."

# Check PostgreSQL
if docker ps | grep -q postgres; then
    echo -e "${GREEN}✓${NC} PostgreSQL is running"
else
    echo -e "${RED}✗${NC} PostgreSQL is not running"
    echo "   Start with: docker-compose -f docker-compose.dev.yml up -d postgres"
    exit 1
fi

# Check Keycloak
if curl -s http://localhost:8081/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Keycloak is running"
else
    echo -e "${YELLOW}⚠${NC} Keycloak might not be running"
    echo "   Check: curl http://localhost:8081/health"
fi

# Check IAM Agent
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} IAM Agent is running"
    IAM_AGENT_STATUS=$(curl -s http://localhost:8000/health | jq -r '.status' 2>/dev/null || echo "unknown")
    echo "   Status: $IAM_AGENT_STATUS"
else
    echo -e "${RED}✗${NC} IAM Agent is not running"
    echo "   Start with: cd backend/services/iam_agent && python -m uvicorn app.main:app --reload --port 8000"
    exit 1
fi

# Check Frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend is running"
else
    echo -e "${YELLOW}⚠${NC} Frontend might not be running"
    echo "   Start with: cd frontend && npm run dev"
fi

echo ""
echo "📝 Testing Checklist:"
echo "===================="
echo ""
echo "1. Open browser: http://localhost:3000"
echo "2. Login with Keycloak credentials"
echo "3. Navigate to: http://localhost:3000/dashboard/iam/people"
echo ""
echo "📚 Test Flows:"
echo "  • People Page: Add a new user"
echo "  • My Access: Request access to an entitlement"
echo "  • Apps & Profiles: View apps and access profiles"
echo "  • Policies: Create/edit policies"
echo ""
echo "🔍 Debugging:"
echo "  • Browser DevTools (F12) → Network tab"
echo "  • Browser DevTools (F12) → Console tab"
echo "  • IAM Agent logs: docker-compose logs -f iam_agent"
echo ""
echo "📖 Full guide: docs/archive/reference/identity/iam-portal-testing-guide.md"
echo ""

# Test API endpoint if token is provided
if [ -n "$1" ]; then
    TOKEN=$1
    echo "🧪 Testing API with provided token..."
    echo ""
    
    echo "Testing: GET /api/iam-portal/users"
    RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -H "Authorization: Bearer $TOKEN" \
        http://localhost:8000/api/iam-portal/users)
    
    HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
    BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE/d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓${NC} API is working"
        echo "Response: $BODY" | jq '.' 2>/dev/null || echo "$BODY"
    else
        echo -e "${RED}✗${NC} API returned HTTP $HTTP_CODE"
        echo "Response: $BODY"
    fi
fi

echo ""
echo "✅ Ready to test!"

