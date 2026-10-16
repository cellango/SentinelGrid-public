# Detection Rules UI - Testing Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** December 4, 2025  
**Status:** ✅ Frontend Built and Running  
**Test Environment:** Docker Development Setup

---

## 🚀 Frontend Status

**Container:** `sentinelgrid-frontend-1`  
**Status:** ✅ Up and Healthy  
**Ports:** 3000 (HTTP), 3443 (HTTPS)

---

## 🧪 How to Test the New Features

### Access the Application

Open your browser and navigate to:

**Primary URL (HTTP):**
```
http://localhost:3000
```

**Secure URL (HTTPS):**
```
https://localhost:3443
```

**Note:** HTTP (3000) redirects to HTTPS (3443) as configured in nginx

---

## 🔍 Feature Testing Checklist

### 1. ✅ Navigation Structure (Option A)

**Test:** Verify new "Detection & Response" section

**Steps:**
1. Log in to the dashboard
2. Look at the left sidebar
3. Find "Detection & Response" section with 🔍 icon
4. Click to expand (if collapsed)
5. Verify 3 submenu items:
   - ⚙️ Detection Rules (with "10" badge)
   - ⚡ Live Events
   - 📈 Rule Health

**Expected Result:**
- Section expands/collapses smoothly
- Active page is highlighted
- Badge shows "10" next to Detection Rules

---

### 2. ✅ Main Dashboard Widget

**Test:** Detection Rules widget on main dashboard

**Steps:**
1. Go to `/dashboard` (main SOC dashboard)
2. Scroll to find "Detection Rules" widget with 🔍 icon
3. Verify 4 stats cards:
   - Total Rules: 10
   - Enabled: 10
   - Events Today: 14
   - Incidents: 13
4. Click "Manage Rules" button

**Expected Result:**
- Widget displays with gradient background
- Stats are visible
- Clicking "Manage Rules" navigates to `/dashboard/siem/detection-rules`

---

### 3. ✅ Detection Rules List Page

**URL:** `http://localhost:3000/dashboard/siem/detection-rules`

**Test:** Health summary card and rule list

**Steps:**
1. Verify health summary card at top:
   - 📊 Detection Rules Health
   - 4 metric cards (Rules Configured, Enabled, Events 24h, Incidents 24h)
   - Warning indicator if rules need attention
2. Scroll down to see all 10 detection rules
3. Verify each rule card shows:
   - Rule key (SG-DET-001, etc.) and name
   - Category icon (👤, 📧, 💻, ☁️, 🌐, 📱)
   - Severity badge (CRITICAL/HIGH/MEDIUM)
   - Description
   - MITRE techniques (purple badges: T1078, T1110)
   - NIST controls (blue badges: AC-2, AC-7)
   - Statistics (Last fired, Fires 24h, Incidents 24h, Effectiveness %)
   - Enable/Disable button
   - View button

**Expected Result:**
- All 10 rules displayed
- MITRE and NIST badges visible
- Stats show realistic values

---

### 4. ✅ Advanced Search and Filtering

**Test:** Search and filter functionality

**Steps:**
1. Use search bar at top of rules page
2. Type "T1078" (MITRE technique) → Should show SG-DET-001
3. Clear and type "AC-2" (NIST control) → Should show multiple rules
4. Clear and type "phishing" → Should show SG-DET-002 and SG-DET-003
5. Use severity dropdown → Filter by "High"
6. Use status dropdown → Filter by "Enabled"
7. Use category dropdown → Filter by "Identity"
8. Verify active filters summary appears
9. Click "Clear All" to reset

**Expected Result:**
- Search works for rule names, MITRE techniques, NIST controls
- Filters work independently and together
- Active filters shown as chips
- Results count updates dynamically

---

### 5. ✅ Enable/Disable Toggle

**Test:** Toggle rule enable/disable

**Steps:**
1. Find any rule with "✓ Enabled" status
2. Click the "✓ Enabled" button
3. Observe loading state (⏳)
4. After ~0.5 seconds, status should update

**Expected Result:**
- Button shows loading indicator
- Status toggles between enabled/disabled
- Color changes (green ↔ gray)
- Console shows API call (check browser dev tools)

---

### 6. ✅ Bulk Operations

**Test:** Bulk enable/disable multiple rules

**Steps:**
1. Click "Bulk Operations" button (top right)
2. Verify checkboxes appear on all rule cards
3. Select 3-4 rules by clicking checkboxes
4. Verify bulk action bar appears showing selection count
5. Click "Select All" → All rules should be checked
6. Click "Deselect All" → All should be unchecked
7. Select 2 rules again
8. Click "Enable Selected" or "Disable Selected"
9. Verify operation completes
10. Click "Cancel Bulk Mode" to exit

**Expected Result:**
- Checkboxes appear/disappear correctly
- Selection count updates
- Bulk actions work
- Selected rules highlighted with primary color border

---

### 7. ✅ Rule Detail Page with Tabs

**Test:** Enhanced rule detail page

**Steps:**
1. Click "View" button on any rule (e.g., SG-DET-001)
2. Verify 5 tabs are present:
   - 📊 Overview
   - ⚙️ Configuration
   - 📈 Performance
   - ✓ Compliance
   - 📜 History
3. Click each tab and verify content:
   
   **Overview Tab:**
   - Configuration details (Rule Key, Version, Category, Severity, Index Pattern, Playbook)
   - Statistics cards (Fires 24h, Fires 7d, Incidents Created, Last Fired)
   
   **Configuration Tab:**
   - OpenSearch Query DSL (JSON formatted)
   - Trigger Condition (JSON formatted)
   
   **Performance Tab:**
   - Fire history section (placeholder)
   - Incident creation rate (placeholder)
   
   **Compliance Tab:**
   - MITRE ATT&CK section (Tactics and Techniques)
   - NIST SP 800-53 controls
   - CIS Controls
   - Clickable links to MITRE website
   
   **History Tab:**
   - Version history entries (v1.0.0, v0.9.0)
   - Recent activity log (Rule Enabled, Configuration Updated, Rule Created)

4. Verify action buttons at bottom:
   - Test Rule
   - Edit Configuration
   - View History

**Expected Result:**
- All 5 tabs render properly
- Tab icons and labels visible
- Active tab highlighted
- Content switches correctly between tabs

---

### 8. ✅ Rule Health Dashboard

**URL:** `http://localhost:3000/dashboard/siem/detection-rules/health`

**Test:** Aggregate performance metrics

**Steps:**
1. Navigate to Rule Health (via sidebar or direct URL)
2. Verify 4 overview cards:
   - Total Rules: 10
   - Fires (24h): 14
   - Avg Effectiveness: 93%
   - Rules Need Attention: 0
3. Scroll to "🔥 Most Active Rules (24h)" section
   - Verify top 5 rules listed
   - Each shows category badge and fire count
4. Scroll to "💤 Least Active Rules (30d)" section
   - Verify rules with 0 fires listed
   - Warning message about reviewing thresholds
5. Scroll to "🎯 Detection Coverage by MITRE ATT&CK Tactic"
   - Verify horizontal bar chart
   - Each tactic shows rule count
   - Progress bars visualize coverage

**Expected Result:**
- All metrics display correctly
- Bar charts render properly
- Rule cards are clickable links to detail pages

---

## 📸 Visual Testing

### Color Schemes to Verify

**Severity Colors:**
- Critical: Red text/border (#ef4444)
- High: Orange text/border (#f97316)
- Medium: Yellow text/border (#eab308)
- Low: Blue text/border (#3b82f6)

**Status Colors:**
- Enabled: Green (#22c55e)
- Disabled: Gray (#6b7280)
- Primary (SentinelGrid): Cyan (#22d3ee)

**Compliance Badge Colors:**
- MITRE: Purple (#a855f7)
- NIST: Blue (#3b82f6)
- CIS: Blue (#3b82f6)

### Responsive Design

Test on different screen sizes:
- Desktop (1920x1080)
- Laptop (1440x900)
- Tablet (768x1024)
- Mobile (375x667)

---

## 🔗 Page URLs Reference

| Feature | URL | Description |
|---------|-----|-------------|
| Main Dashboard | `/dashboard` | SOC dashboard with Detection Rules widget |
| Detection Rules List | `/dashboard/siem/detection-rules` | Manage all 10 rules |
| Rule Detail | `/dashboard/siem/detection-rules/1` | Detailed view with tabs (replace 1 with rule ID 1-10) |
| Rule Health | `/dashboard/siem/detection-rules/health` | Performance metrics dashboard |
| Live Events | `/dashboard/siem/detections` | Real-time detection event stream |

---

## 🐛 Known Issues / Limitations

1. **API Calls:** Currently using mock data - backend endpoints are implemented but return mock data until database integration is complete
2. **Charts:** Performance charts in Rule Detail page show placeholders (future enhancement)
3. **Real-time Updates:** Enable/disable changes don't persist (need backend database integration)
4. **Export/Import:** Not yet implemented (Phase 3 feature)
5. **Rule Testing:** UI placeholder exists, testing logic not implemented (Phase 3 feature)

---

## ✅ Success Criteria

The implementation is successful if you can:

- ✅ See "Detection & Response" in sidebar with submenu
- ✅ Access Detection Rules page in 2 clicks from dashboard
- ✅ View all 10 detection rules with MITRE/NIST mappings
- ✅ Search by MITRE technique (e.g., "T1078") and find relevant rules
- ✅ Filter by severity, status, and category
- ✅ Click enable/disable toggle and see visual feedback
- ✅ Use bulk operations to select and manage multiple rules
- ✅ View rule detail page with 5 comprehensive tabs
- ✅ See MITRE ATT&CK clickable links in Compliance tab
- ✅ Navigate to Rule Health dashboard and see metrics
- ✅ See Detection Rules widget on main dashboard

---

## 🎬 Quick Test Flow (5 Minutes)

**Quick validation:**

1. Go to `http://localhost:3000` → Log in
2. Click sidebar: **Detection & Response** → **Detection Rules**
3. Verify: Health summary card + 10 rules displayed ✅
4. Search: Type "T1078" → See SG-DET-001 ✅
5. Filter: Select "High" severity → See only high-severity rules ✅
6. Bulk: Click "Bulk Operations" → Select 2 rules → See action bar ✅
7. Detail: Click "View" on any rule → See 5 tabs ✅
8. Compliance: Click "Compliance" tab → See MITRE/NIST badges ✅
9. Health: Go to Rule Health page → See metrics and charts ✅
10. Dashboard: Go to main dashboard → See Detection Rules widget ✅

**All tests passing?** 🎉 Implementation successful!

---

## 📞 Support

**Issues?** Check:
- Frontend logs: `docker logs sentinelgrid-frontend-1`
- Browser console: F12 → Console tab
- Network tab: F12 → Network tab (check API calls)

**Documentation:**
- Implementation Summary: `DETECTION_RULES_UI_IMPLEMENTATION_SUMMARY.md`
- SIEM Detection Overview: `docs/archive/reference/detection-response/siem-detection-overview.md`

---

**Ready to Test!** 🎯 Access the app at `http://localhost:3000`

