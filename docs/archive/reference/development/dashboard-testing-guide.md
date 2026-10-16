# Dashboard Testing Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Purpose:** Guide for testing the Enhanced Dashboard with AI Snapshot

---

## Prerequisites

1. **Backend Services Running:**
   - API Gateway (port 8082)
   - Orchestrator Service (port 8012)
   - IAM Agent (port 8005)
   - SIEM Agent (port 8003)
   - Model Gateway (port 8002)

2. **Environment Variables:**
   ```bash
   INTERNAL_SERVICE_TOKEN=your-internal-token-here
   ORCHESTRATOR_URL=http://orchestrator:8000
   ```

3. **Frontend Running:**
   - Next.js dev server (port 3000)

---

## Testing Checklist

### 1. API Gateway Configuration ✅

**Test:** Verify orchestrator endpoint is accessible through API Gateway

```bash
# Test endpoint directly
curl -X GET "http://localhost:8082/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot" \
  -H "Authorization: Bearer {user_token}" \
  -H "X-Tenant-ID: {tenant_id}"
```

**Expected:** 200 OK with security snapshot JSON

**If 503:** Check orchestrator service is running
**If 401:** Check INTERNAL_SERVICE_TOKEN matches in both services
**If 404:** Check tenant_id exists

---

### 2. Frontend API Client ✅

**Test:** Verify frontend can fetch snapshot

1. Open browser DevTools → Network tab
2. Navigate to `/dashboard`
3. Check for request to `/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot`
4. Verify response status is 200

**Expected:**
- Request includes `Authorization` header
- Request includes `X-Tenant-ID` header
- Response contains `SecuritySnapshot` data

---

### 3. Dashboard Components ✅

#### 3.1 Security Snapshot Panel

**Test Cases:**
- [ ] Panel displays when snapshot loads
- [ ] Posture shows correct color (Good=green, Needs Attention=yellow, At Risk=red)
- [ ] Risk level badge displays correctly
- [ ] Summary text is readable
- [ ] Timestamp shows last update time

**Test Data:**
```json
{
  "ai_analysis": {
    "posture": "Good",
    "risk_level": "Low",
    "summary": "Your security posture is healthy..."
  }
}
```

#### 3.2 AI Insights Widget

**Test Cases:**
- [ ] Key findings section expands/collapses
- [ ] Recommendations section expands/collapses
- [ ] Priority colors are correct (High=red, Medium=yellow, Low=green)
- [ ] All findings and recommendations display

**Test Data:**
```json
{
  "ai_analysis": {
    "key_findings": [
      "Finding 1",
      "Finding 2"
    ],
    "recommendations": [
      {"priority": "High", "action": "Action 1"},
      {"priority": "Medium", "action": "Action 2"}
    ]
  }
}
```

#### 3.3 Top Findings Widget

**Test Cases:**
- [ ] Top 5 alerts display
- [ ] Severity badges show correct colors
- [ ] Clicking alert navigates to alert detail page
- [ ] "View all" link works
- [ ] Empty state shows when no findings

**Test Data:**
```json
{
  "top_findings": [
    {
      "id": "alert-1",
      "title": "Suspicious Login",
      "severity": "high",
      "status": "open"
    }
  ]
}
```

#### 3.4 Activity Timeline Chart

**Test Cases:**
- [ ] Chart renders without errors
- [ ] Both lines (events + alerts) display
- [ ] Tooltip shows on hover
- [ ] Chart is responsive (resize window)
- [ ] Data points are visible

**Note:** Currently uses mock data. Will test with real data in Step 3.

#### 3.5 Enhanced Stats Cards

**Test Cases:**
- [ ] All 4 cards display
- [ ] Numbers match snapshot data
- [ ] Subtitles show correctly
- [ ] Color coding is appropriate
- [ ] Responsive grid layout works

---

### 4. Error Handling ✅

**Test Cases:**

#### 4.1 API Failure
- [ ] Dashboard shows error message when API fails
- [ ] Fallback to basic dashboard view works
- [ ] Error message is user-friendly

**Simulate:** Stop orchestrator service, refresh dashboard

#### 4.2 Missing Tenant ID
- [ ] Dashboard handles missing tenant_id gracefully
- [ ] Shows appropriate message
- [ ] Doesn't crash

**Simulate:** Clear localStorage `tenant_id`, refresh

#### 4.3 Loading States
- [ ] Loading spinner shows during fetch
- [ ] Components don't flash/jump during load
- [ ] Loading state is clear to user

---

### 5. Performance ✅

**Test Cases:**
- [ ] Dashboard loads in < 3 seconds
- [ ] No layout shift during load
- [ ] Auto-refresh works (wait 5 minutes)
- [ ] No memory leaks (check DevTools → Memory)

**Performance Metrics:**
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- API Response Time: < 2s

---

### 6. Responsive Design ✅

**Test Cases:**
- [ ] Desktop (1920x1080): 3-column grid works
- [ ] Tablet (768x1024): 2-column grid works
- [ ] Mobile (375x667): 1-column stack works
- [ ] All components readable on mobile
- [ ] No horizontal scrolling

**Breakpoints:**
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

---

## Manual Testing Script

### Step 1: Setup
```bash
# Start all services
docker-compose up -d

# Check services are running
curl http://localhost:8082/health
curl http://localhost:8012/health
```

### Step 2: Get Test Token
```bash
# Login via IAM Agent (or use existing token)
# Store token in localStorage or use in API calls
```

### Step 3: Test API Endpoint
```bash
# Replace {tenant_id} and {token} with real values
curl -X GET "http://localhost:8082/api/v1/orchestrator/tenant/{tenant_id}/security-snapshot" \
  -H "Authorization: Bearer {token}" \
  -H "X-Tenant-ID: {tenant_id}" \
  | jq .
```

### Step 4: Test Frontend
1. Open `http://localhost:3000/dashboard`
2. Open DevTools → Console
3. Check for errors
4. Open DevTools → Network
5. Verify API call succeeds
6. Check all components render

### Step 5: Test Error Cases
1. Stop orchestrator: `docker-compose stop orchestrator`
2. Refresh dashboard
3. Verify error handling works
4. Restart orchestrator: `docker-compose start orchestrator`

---

## Automated Testing

### Unit Tests (Future)
```typescript
// Example test structure
describe('SecuritySnapshotPanel', () => {
  it('displays posture correctly', () => {
    // Test component rendering
  });
  
  it('handles missing data', () => {
    // Test error states
  });
});
```

### Integration Tests (Future)
```typescript
describe('Dashboard Integration', () => {
  it('fetches and displays snapshot', async () => {
    // Test full flow
  });
});
```

---

## Common Issues & Solutions

### Issue: 503 Service Unavailable
**Cause:** Orchestrator service not running  
**Solution:** `docker-compose start orchestrator`

### Issue: 401 Unauthorized
**Cause:** INTERNAL_SERVICE_TOKEN mismatch  
**Solution:** Ensure same token in API Gateway and Orchestrator env vars

### Issue: CORS Error
**Cause:** Frontend origin not in CORS_ORIGINS  
**Solution:** Add `http://localhost:3000` to API Gateway CORS_ORIGINS

### Issue: Empty Dashboard
**Cause:** No tenant_id in localStorage  
**Solution:** Set `localStorage.setItem('tenant_id', 'your-tenant-id')`

### Issue: Chart Not Rendering
**Cause:** Recharts not installed or data format wrong  
**Solution:** Check `package.json` has `recharts`, verify data structure

---

## Test Data Examples

### Minimal Valid Snapshot
```json
{
  "tenant_id": "test-tenant-123",
  "generated_at": "2025-01-28T10:00:00Z",
  "summary": {
    "events_count": 1000,
    "alerts_count": 5,
    "users_active": 10,
    "users_total": 15
  },
  "alerts_by_severity": {
    "critical": 1,
    "high": 2,
    "medium": 2
  },
  "alerts_by_status": {
    "open": 3,
    "resolved": 2
  },
  "top_findings": [],
  "iam_summary": {
    "users_count": 15,
    "active_users_count": 10
  },
  "ai_analysis": {
    "posture": "Good",
    "risk_level": "Low",
    "key_findings": [],
    "recommendations": [],
    "summary": "Test summary"
  }
}
```

---

## Success Criteria

✅ All components render without errors  
✅ API calls succeed  
✅ Error handling works  
✅ Responsive design works  
✅ Performance is acceptable  
✅ Auto-refresh works  
✅ No console errors  

---

**Last Updated:** 2025-01-28

