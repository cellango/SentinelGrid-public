# Hero Flow 2 Testing Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-01-28  
**Status:** 📋 Testing Guide  
**Phase:** Integration & Testing (Week 8-9)

---

## Overview

This guide provides comprehensive testing instructions for Hero Flow 2: Suspicious Login Handled End-to-End. It covers end-to-end integration tests, UI testing, and performance testing.

---

## End-to-End Integration Tests

### Test Flow: Suspicious Login → Ticket → Enrichment → Resolution

#### 1. Alert Detection & Ticket Creation

**Test:** `test_suspicious_login_detection_to_ticket_creation`

**Steps:**
1. SIEM Agent detects suspicious login (multiple failed attempts)
2. Detection Service analyzes alert and creates ticket
3. Verify ticket created with correct metadata
4. Verify TheHive case created

**Expected Results:**
- ✅ Ticket created with status "open"
- ✅ Severity set to "high"
- ✅ Category set to "suspicious_login"
- ✅ TheHive case ID in `external_id`
- ✅ Alert linked to ticket

**Run Test:**
```bash
cd backend/services/ticketing_agent
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_suspicious_login_detection_to_ticket_creation -v
```

#### 2. AI Enrichment Trigger

**Test:** `test_ai_enrichment_trigger`

**Steps:**
1. Create ticket with user identifier
2. Verify AI enrichment triggered automatically
3. Check enrichment status

**Expected Results:**
- ✅ Enrichment triggered for ticket
- ✅ IAM data populated (user, supervisor, groups)
- ✅ Network data populated (IPs, domains)
- ✅ Enrichment status updated

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_ai_enrichment_trigger -v
```

#### 3. Framework Mapping

**Test:** `test_framework_mapping`

**Steps:**
1. Create ticket with category "malware"
2. Verify NIST controls mapped
3. Verify MITRE tactics/techniques mapped

**Expected Results:**
- ✅ NIST controls assigned (e.g., IR-4, SI-3)
- ✅ MITRE tactics assigned (e.g., TA0001, TA0002)
- ✅ MITRE techniques assigned (e.g., T1059)

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_framework_mapping -v
```

#### 4. TheHive Case Creation

**Test:** `test_thehive_case_creation`

**Steps:**
1. Create ticket
2. Verify TheHive case created
3. Verify observables added
4. Verify tasks added

**Expected Results:**
- ✅ TheHive case created
- ✅ Observables added (IPs, user identifiers)
- ✅ Tasks added (from playbook)
- ✅ Case status synced

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_thehive_case_creation -v
```

#### 5. Playbook Recommendation

**Test:** `test_playbook_recommendation`

**Steps:**
1. Create ticket with category and framework mappings
2. Request playbook recommendations
3. Verify recommendations returned

**Expected Results:**
- ✅ Playbooks recommended based on category
- ✅ Playbooks scored by relevance
- ✅ Top playbooks returned

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_playbook_recommendation -v
```

#### 6. Automated Action Execution

**Test:** `test_automated_action_execution`

**Steps:**
1. Execute playbook with action steps
2. Verify action executed
3. Verify ticket updated with action result

**Expected Results:**
- ✅ Action executed successfully
- ✅ Ticket timeline updated
- ✅ Action logged

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_automated_action_execution -v
```

#### 7. NIST Workflow Transitions

**Test:** `test_nist_workflow_transitions`

**Steps:**
1. Create ticket with status "new"
2. Transition to "triaged"
3. Transition to "contained"
4. Verify invalid transitions rejected

**Expected Results:**
- ✅ Valid transitions allowed
- ✅ Invalid transitions rejected
- ✅ Phase tracking updated
- ✅ Workflow history maintained

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_nist_workflow_transitions -v
```

#### 8. Ticket Tab Data Retrieval

**Test:** `test_ticket_tab_data_retrieval`

**Steps:**
1. Create and enrich ticket
2. Retrieve IAM tab data
3. Retrieve VM tab data
4. Retrieve CMDB tab data
5. Retrieve Network tab data
6. Retrieve Timeline tab data

**Expected Results:**
- ✅ All tab data endpoints return data
- ✅ Data structure matches expected format
- ✅ Empty states handled gracefully

**Run Test:**
```bash
pytest tests/test_hero_flow_2.py::TestHeroFlow2Integration::test_ticket_tab_data_retrieval -v
```

---

## UI Testing

### Frontend Component Tests

#### 1. Ticket Detail Page

**Test:** Ticket detail page loads and displays data

**Steps:**
1. Navigate to `/dashboard/tickets/{ticket_id}`
2. Verify overview section displays
3. Verify tabs render
4. Verify framework badges display

**Expected Results:**
- ✅ Page loads without errors
- ✅ Ticket data displayed
- ✅ Tabs navigable
- ✅ Framework badges visible

#### 2. Tab Navigation

**Test:** Tab switching works correctly

**Steps:**
1. Click each tab (IAM, VM, CMDB, Network, Timeline)
2. Verify tab content loads
3. Verify loading states display
4. Verify empty states display

**Expected Results:**
- ✅ Tabs switch smoothly
- ✅ Content loads for each tab
- ✅ Loading indicators show
- ✅ Empty states handled

#### 3. IAM Tab

**Test:** IAM tab displays user data

**Steps:**
1. Navigate to IAM tab
2. Verify user details display
3. Verify supervisor information
4. Verify groups and permissions

**Expected Results:**
- ✅ User information displayed
- ✅ Supervisor shown
- ✅ Groups listed
- ✅ Permissions shown
- ✅ Access history displayed

#### 4. VM Tab

**Test:** VM tab displays vulnerability data

**Steps:**
1. Navigate to VM tab
2. Verify CVE list displays
3. Verify remediation steps shown
4. Verify patches available

**Expected Results:**
- ✅ CVEs listed with badges
- ✅ Severity color-coded
- ✅ Remediation steps shown
- ✅ Patches with download links

#### 5. CMDB Tab

**Test:** CMDB tab displays asset data

**Steps:**
1. Navigate to CMDB tab
2. Verify assets listed
3. Verify software inventory
4. Verify hardware inventory

**Expected Results:**
- ✅ Assets displayed
- ✅ Software inventory shown
- ✅ Hardware specs displayed
- ✅ Compliance status shown

#### 6. Network Tab

**Test:** Network tab displays network data

**Steps:**
1. Navigate to Network tab
2. Verify IP addresses listed
3. Verify domains listed
4. Verify connections shown

**Expected Results:**
- ✅ IPs with reputation
- ✅ Domains with reputation
- ✅ Connections displayed
- ✅ Firewall rules shown

#### 7. Timeline Tab

**Test:** Timeline tab displays events

**Steps:**
1. Navigate to Timeline tab
2. Verify events listed chronologically
3. Verify actions shown
4. Verify history displayed

**Expected Results:**
- ✅ Events in chronological order
- ✅ Actions tracked
- ✅ History maintained
- ✅ Type color-coded

---

## Performance Testing

### 1. Enrichment Performance

**Test:** Parallel enrichment execution

**Steps:**
1. Create ticket with multiple enrichment triggers
2. Measure enrichment time
3. Verify parallel execution

**Expected Results:**
- ✅ Enrichment completes within timeout (5 minutes)
- ✅ Parallel modules execute simultaneously
- ✅ No blocking between modules

**Performance Targets:**
- IAM enrichment: < 10 seconds
- Vulnerability enrichment: < 30 seconds
- CMDB enrichment: < 10 seconds
- Network enrichment: < 10 seconds
- Framework mapping: < 5 seconds
- **Total enrichment: < 60 seconds**

### 2. Ticket Loading Performance

**Test:** Ticket detail page load time

**Steps:**
1. Load ticket detail page
2. Measure initial load time
3. Measure tab switching time

**Expected Results:**
- ✅ Initial load < 2 seconds
- ✅ Tab switching < 1 second
- ✅ Smooth user experience

### 3. Large Data Sets

**Test:** Performance with large data sets

**Steps:**
1. Create ticket with 100+ CVEs
2. Create ticket with 50+ assets
3. Verify UI performance

**Expected Results:**
- ✅ UI remains responsive
- ✅ Data paginated if needed
- ✅ No performance degradation

---

## Test Execution

### Run All Integration Tests

```bash
# Backend integration tests
cd backend/services/ticketing_agent
pytest tests/test_hero_flow_2.py -v

cd ../ai_enrichment_agent
pytest tests/test_enrichment_integration.py -v

cd ../framework_service
pytest tests/test_framework_mapping.py -v

cd ../action_agent
pytest tests/test_action_execution.py -v
```

### Run All Tests with Coverage

```bash
# Backend
pytest --cov=app --cov-report=html tests/

# Frontend
cd frontend
npm test -- --coverage
```

### Run Specific Test Suite

```bash
# Hero Flow 2 E2E tests
pytest backend/services/ticketing_agent/tests/test_hero_flow_2.py -v

# Enrichment tests
pytest backend/services/ai_enrichment_agent/tests/test_enrichment_integration.py -v
```

---

## Test Data Setup

### Prerequisites

1. **Database:** PostgreSQL running with test database
2. **Services:** All services running (or mocked)
3. **TheHive:** TheHive running (or mocked)
4. **Test Tenant:** Test tenant created

### Test Data

```python
# Test tenant
tenant_id = "00000000-0000-0000-0000-000000000001"

# Test alert
alert = {
    "id": "alert-123",
    "title": "Suspicious Login Detected",
    "user_identifier": "user@example.com",
    "severity": "high"
}

# Test ticket
ticket = {
    "title": "Suspicious Login",
    "category": "suspicious_login",
    "severity": "high"
}
```

---

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify PostgreSQL is running
   - Check database credentials
   - Ensure test database exists

2. **Service Connection Errors**
   - Verify all services are running
   - Check service URLs in config
   - Verify network connectivity

3. **Mock Failures**
   - Check mock setup
   - Verify async/await usage
   - Check return values

4. **UI Test Failures**
   - Verify API endpoints are accessible
   - Check CORS configuration
   - Verify authentication tokens

---

## Success Criteria

### Integration Tests
- ✅ All E2E tests pass
- ✅ All enrichment tests pass
- ✅ All framework mapping tests pass
- ✅ All action execution tests pass

### UI Tests
- ✅ All components render correctly
- ✅ All tabs functional
- ✅ All data displays correctly
- ✅ Loading/error states work

### Performance Tests
- ✅ Enrichment completes within timeout
- ✅ Ticket loading < 2 seconds
- ✅ Tab switching < 1 second
- ✅ Large data sets handled gracefully

---

**Last Updated:** 2025-01-28

