# Compliance Platform API Reference

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


Complete API documentation for compliance and reporting features.

---

## Authentication

All API endpoints require Bearer token authentication with tenant_id + realm claims.

```bash
Authorization: Bearer {JWT_TOKEN}
```

The JWT token MUST contain:
- `tenant_id`: UUID of the tenant
- `realm`: Name of the Keycloak realm
- `sub`: User ID

---

## Report APIs

### Generate Report

```http
POST /api/v1/reports/generate
Content-Type: application/json
```

**Request Body:**
```json
{
  "report_type": "soc2_coverage",
  "period_start": "2025-11-01",
  "period_end": "2025-11-30"
}
```

**Report Types:**
- `soc2_coverage` - SOC 2 Trust Services Criteria Coverage
- `iam_mfa_hygiene` - IAM & MFA Hygiene Report
- `log_coverage` - Log Coverage & Retention Report
- `incident_response` - Incident & Response Effectiveness
- `cloud_posture` - Cloud Posture & Exposure Report
- `nist_csf` - NIST CSF Coverage Summary
- `security_onepager` - Security One-Pager

**Response:**
```json
{
  "report_id": "550e8400-e29b-41d4-a716-446655440000",
  "report_name": "SOC2_Coverage_Report_2025-12-02_AcmeCorp.pdf",
  "status": "generating",
  "estimated_completion": "2025-12-02T10:05:00Z"
}
```

### List Reports (Tenant-Scoped)

```http
GET /api/v1/reports?report_type={type}&start_date={date}&end_date={date}
```

**Query Parameters:**
- `report_type` (optional): Filter by report type
- `start_date` (optional): Filter by generation date
- `end_date` (optional): Filter by generation date
- `limit` (optional): Max results (default 50)
- `offset` (optional): Pagination offset

**Response:**
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "realm_name": "acme-corp",
    "report_type": "soc2_coverage",
    "report_name": "SOC2_Coverage_Report_2025-12-02_AcmeCorp.pdf",
    "report_period_start": "2025-11-01",
    "report_period_end": "2025-11-30",
    "generated_at": "2025-12-02T10:00:00Z",
    "generated_by": "user@acme.com",
    "file_size_bytes": 2457600,
    "status": "ready",
    "llm_ingested": true,
    "metadata": {
      "soc2_coverage": 87.5,
      "controls_implemented": 28,
      "total_controls": 32
    }
  }
]
```

**Security:** Automatically filtered by JWT token's tenant_id + realm

### Download Report

```http
GET /api/v1/reports/{report_id}/download/{format}
```

**Path Parameters:**
- `report_id`: UUID of the report
- `format`: `pdf` or `csv`

**Response:** File download with appropriate Content-Type

**Security:**
- Validates tenant_id + realm from token matches report
- Returns 404 if not found (prevents enumeration)
- Logs access in `report_access_log`

### Query Reports

```http
POST /api/v1/reports/query
Content-Type: application/json
```

**Request:**
```json
{
  "query": "What was our MFA coverage last month?"
}
```

**Response:**
```json
{
  "query": "What was our MFA coverage last month?",
  "answer": "SentinelGrid can answer this with live identity and access evidence. The current compliance view shows mapped control checks and evidence items supporting identity-focused criteria such as CC6.1.",
  "sources": [
    {
      "report_id": "uuid",
      "report_type": "smb_customer_security_review_pack",
      "generated_at": "2025-11-30T00:00:00Z",
      "relevance_score": 0.8
    }
  ],
  "confidence": "high",
  "recommended_artifacts": [
    {
      "template_key": "smb_customer_security_review_pack",
      "reason": "Best for customer-facing security reviews and vendor questionnaires."
    }
  ],
  "follow_up": [
    "Generate the recommended trust artifact from the Compliance Reports page before sending a response."
  ]
}
```

**Security:**
- Tenant-scoped compliance data only
- Cannot access other tenants' report data
- All queries logged for audit

### Questionnaire Assist

```http
POST /api/v1/reports/questionnaire-assist
Content-Type: application/json
```

**Request:**
```json
{
  "questions": [
    "How do we answer customer security questionnaires quickly?",
    "How do we evidence MFA and access control coverage?"
  ]
}
```

**Response:**
```json
{
  "summary": {
    "question_count": 2,
    "overall_score": 84,
    "criteria_ready": 6,
    "criteria_needing_attention": 2,
    "mapped_detections": 12,
    "control_checks": 8,
    "evidence_items": 17,
    "recommended_artifacts": [
      {
        "template_key": "smb_customer_security_review_pack",
        "reason": "Best for customer-facing security reviews and vendor questionnaires."
      }
    ]
  },
  "answers": [
    {
      "question": "How do we evidence MFA and access control coverage?",
      "category": "identity_access",
      "confidence": "high",
      "answer": "SentinelGrid can answer this with live identity and access evidence rather than a static statement.",
      "recommended_artifacts": [
        {
          "template_key": "smb_customer_security_review_pack",
          "reason": "Best for customer-facing security reviews and vendor questionnaires."
        }
      ],
      "supporting_controls": [
        {
          "id": "CC6.1",
          "title": "Logical and Physical Access Controls",
          "status": "partial",
          "open_findings": 2,
          "evidence_items": 4
        }
      ],
      "supporting_signals": [
        {
          "id": "check-1",
          "title": "MFA coverage check",
          "source_label": "Identity control check",
          "status": "partial"
        }
      ],
      "follow_up": [
        "Generate the recommended trust artifact from the Compliance Reports page before sending a response."
      ]
    }
  ],
  "suggested_questions": [
    "How do we answer customer security questionnaires quickly?"
  ]
}
```

**Use Case:**
- Draft customer security-review responses
- Triage vendor questionnaire items
- Recommend the right trust artifact before sharing evidence

---

### Security Review Response Templates

```http
GET /api/v1/reports/security-review-templates
```

**Response:**
```json
{
  "summary": {
    "framework_pack_states": {
      "soc2": "live",
      "iso27001": "starter"
    },
    "recommended_artifacts": [
      {
        "template_key": "smb_customer_security_review_pack",
        "reason": "Attach this first for most customer security reviews."
      }
    ]
  },
  "templates": [
    {
      "key": "initial_security_review_reply",
      "title": "Initial Security Review Reply",
      "audience": "Sales and customer-facing operators",
      "use_when": "A prospect asks for a fast security overview before sending a full questionnaire.",
      "subject": "SentinelGrid security review materials",
      "body": "Thanks for the request. SentinelGrid can provide a current security review packet backed by live controls, detection coverage, and evidence exports.",
      "recommended_artifacts": [
        {
          "template_key": "smb_customer_security_review_pack",
          "reason": "Best first attachment for customer-facing security reviews."
        }
      ],
      "talking_points": [
        "Lead with live control and detection evidence instead of static claims.",
        "Offer a trust artifact that maps to the prospect's review motion."
      ],
      "follow_up": [
        "Share the customer security review pack link from the Compliance Reports page."
      ]
    }
  ]
}
```

**Use Case:**
- Send a consistent first-response email for customer security reviews
- Hand off a questionnaire with the right trust artifact attached
- Follow up on evidence requests without rewriting the same sales response each time
- Position SOC 2 and ISO 27001 readiness honestly for prospects

---

## Scheduling APIs

### Create Schedule

```http
POST /api/v1/reports/schedules
Content-Type: application/json
```

**Request:**
```json
{
  "report_type": "soc2_coverage",
  "schedule_name": "Weekly SOC 2 Report",
  "cron_expression": "0 9 * * MON",
  "timezone": "America/New_York",
  "recipients": ["compliance@acme.com", "ciso@acme.com"],
  "is_active": true
}
```

**Cron Expression Examples:**
- Daily at 9am: `0 9 * * *`
- Weekly on Monday 9am: `0 9 * * MON`
- Monthly on 1st at 9am: `0 9 1 * *`
- Quarterly on 1st at 9am: `0 9 1 */3 *`

**Response:**
```json
{
  "schedule_id": "uuid",
  "next_run_at": "2025-12-09T14:00:00Z",
  "message": "Schedule created successfully"
}
```

### List Schedules

```http
GET /api/v1/reports/schedules
```

**Response:**
```json
[
  {
    "id": "uuid",
    "report_type": "soc2_coverage",
    "schedule_name": "Weekly SOC 2 Report",
    "cron_expression": "0 9 * * MON",
    "recipients": ["compliance@acme.com"],
    "is_active": true,
    "last_run_at": "2025-12-02T14:00:00Z",
    "next_run_at": "2025-12-09T14:00:00Z",
    "last_run_status": "success"
  }
]
```

---

## Audit APIs

### Get Audit Logs

```http
GET /api/v1/audit/logs?start_date={date}&end_date={date}&action={action}
```

**Query Parameters:**
- `start_date`: ISO 8601 datetime
- `end_date`: ISO 8601 datetime
- `action`: Filter by action type
- `actor_user_id`: Filter by user
- `resource_type`: Filter by resource
- `limit`: Max results (default 100, max 1000)

**Response:**
```json
{
  "logs": [
    {
      "id": "uuid",
      "timestamp": "2025-12-02T10:30:00Z",
      "action": "report_generated",
      "action_category": "compliance",
      "actor_user_id": "user-123",
      "actor_email": "user@acme.com",
      "resource_type": "report",
      "resource_id": "report-uuid",
      "resource_name": "SOC2_Coverage_Report_2025-12-02_AcmeCorp.pdf",
      "success": true,
      "metadata": {"report_type": "soc2_coverage"}
    }
  ],
  "count": 1
}
```

### Export Audit Logs

```http
GET /api/v1/audit/export?start_date={date}&end_date={date}&format={csv|json}
```

**Response:**
```json
{
  "format": "csv",
  "data": "Timestamp,Action,Actor User ID,...\n2025-12-02T10:30:00Z,report_generated,user-123,...",
  "filename": "audit_logs_tenant-uuid_2025-11-01_2025-11-30.csv"
}
```

---

## Access Review APIs

### Create Campaign

```http
POST /api/v1/iam/access-reviews/campaigns
```

**Request:**
```json
{
  "name": "Q4 2025 Admin Access Review",
  "description": "Quarterly review of all admin access",
  "campaign_type": "admin_review",
  "scope": {
    "roles": ["TENANT_ADMIN", "SOC_MANAGER"]
  },
  "start_date": "2025-12-01T00:00:00Z",
  "end_date": "2025-12-15T23:59:59Z"
}
```

**Response:**
```json
{
  "campaign_id": "uuid",
  "status": "draft",
  "items_to_review": 45
}
```

### Submit Review Decision

```http
POST /api/v1/iam/access-reviews/items/{item_id}/decision
```

**Request:**
```json
{
  "decision": "approved",
  "justification": "User requires admin access for their role as Security Engineer"
}
```

**Decisions:** `approved`, `revoked`, `escalated`

---

## JML Workflow APIs

### Create Joiner Workflow

```http
POST /api/v1/iam/jml/joiner
```

**Request:**
```json
{
  "target_email": "newuser@acme.com",
  "target_name": "New User",
  "target_profile_id": "uuid"
}
```

### Create Leaver Workflow

```http
POST /api/v1/iam/jml/leaver
```

**Request:**
```json
{
  "subject_user_id": "user-uuid",
  "reason": "Employee departure"
}
```

---

## Compliance Dashboard APIs

### Get Dashboard Data

```http
GET /api/v1/compliance/dashboard
```

**Response:**
```json
{
  "overall_stats": {
    "overall_score": 87,
    "controls_implemented": 156,
    "total_controls": 180,
    "evidence_items": 342,
    "last_assessment": "2025-11-30",
    "mapped_detections": 14,
    "control_checks": 11
  },
  "reporting_summary": {
    "criteria_ready": 6,
    "criteria_needing_attention": 2
  },
  "framework_starter_packs": [
    {
      "framework_key": "soc2",
      "framework_name": "SOC 2",
      "launch_state": "live",
      "score_label": "Framework coverage",
      "score": 87,
      "summary": "Use the live readiness layer to move from abstract SOC 2 talk to exportable evidence.",
      "note": "This pack is backed by the current SOC 2 reporting payload and trust artifacts already available in product.",
      "metrics": {
        "criteria_ready": 6,
        "criteria_needing_attention": 2,
        "mapped_signals": 25,
        "evidence_items": 342
      },
      "artifact_template_keys": [
        "smb_audit_readiness_pack",
        "smb_customer_security_review_pack"
      ]
    }
  ]
}
```

---

## Security Considerations

### Tenant Isolation

**ALL endpoints enforce:**
```python
@router.get("/api/v1/reports")
async def list_reports(
    tenant_id: UUID = Depends(get_tenant_id),  # From JWT
    realm: str = Depends(get_realm),           # From JWT
    ...
):
    # Query MUST include tenant_id + realm filter
    query = db.query(GeneratedReport).filter(
        GeneratedReport.tenant_id == tenant_id,
        GeneratedReport.realm_name == realm
    )
```

### Rate Limiting

Recommended rate limits:
- Report generation: 10 per hour per tenant
- Report download: 100 per hour per user
- LLM queries: 50 per hour per user

### Audit Logging

ALL operations are logged:
- Report generation
- Report downloads
- LLM queries
- Access review decisions
- JML workflow executions

---

## Example Integration

### Python Client

```python
import requests
from datetime import datetime, timedelta

class SentinelGridComplianceClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def generate_soc2_report(self):
        """Generate monthly SOC 2 report."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        response = requests.post(
            f"{self.base_url}/api/v1/reports/generate",
            headers=self.headers,
            json={
                "report_type": "soc2_coverage",
                "period_start": start_date.strftime("%Y-%m-%d"),
                "period_end": end_date.strftime("%Y-%m-%d")
            }
        )
        
        return response.json()
    
    def query_reports(self, question: str):
        """Ask question about compliance reports."""
        response = requests.post(
            f"{self.base_url}/api/v1/reports/query",
            headers=self.headers,
            json={"query": question}
        )
        
        return response.json()["answer"]

    def questionnaire_assist(self, questions: list[str]):
        """Draft answers for customer security-review or audit questionnaire items."""
        response = requests.post(
            f"{self.base_url}/api/v1/reports/questionnaire-assist",
            headers=self.headers,
            json={"questions": questions}
        )

        return response.json()["answers"]

# Usage
client = SentinelGridComplianceClient("https://api.sentinelgrid.io", "your_jwt_token")
report = client.generate_soc2_report()
answer = client.query_reports("What is our MFA coverage?")
drafts = client.questionnaire_assist([
    "How do we answer customer security questionnaires quickly?"
])
```

---

**Document Owner:** API Team  
**Last Updated:** December 2, 2025
