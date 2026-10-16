# IAM Policy Editor Implementation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

The IAM Policy Editor is the "brain UI" for SentinelGrid's IAM system. It allows admins to define who can do what, when, and how **without ever seeing Keycloak roles, clients, or JSON**. This makes SentinelGrid feel fundamentally different from "just Keycloak with a skin."

## Architecture

### Policy DSL (Domain-Specific Language)

Policies are defined using a high-level DSL that abstracts away Keycloak:

```json
{
  "id": "policy.admin_signon",
  "type": "signon",
  "scope": "tenant",
  "rules": [
    {
      "id": "rule_admin_high_risk",
      "name": "Admin High-Risk Sign-on",
      "conditions": [
        { "type": "role", "op": "includes", "value": "sg_admin" },
        { "type": "risk_level", "op": "in", "value": ["high", "critical"] }
      ],
      "actions": [
        { "type": "require_factor", "value": "webauthn" },
        { "type": "log", "level": "warn", "message": "High-risk admin sign-on" },
        { "type": "deny" }
      ],
      "priority": 100
    }
  ]
}
```

### Policy Types

1. **Sign-on Policies** - Control when and how users can sign in
   - Conditions: role, location, IP, device, time, risk level
   - Actions: require MFA, require WebAuthn, block sign-in, log event

2. **Access Policies** - Define who can access which resources
   - Conditions: department, team, role, group, resource
   - Actions: allow, deny, require approval

3. **Approval & Workflow Policies** - Configure approval workflows
   - Conditions: entitlement type, risk level, requester attributes
   - Actions: require manager approval, require app owner approval, auto-approve, auto-expire

4. **SoD & Risk Policies** (Phase 2) - Separation of duties
   - Conditions: existing entitlements, role combinations
   - Actions: deny, warn, require additional approval

## Implementation

### Database Schema

**File:** `backend/migrations/016_iam_policies_schema.sql`

Tables:
- `policies` - Policy instances (tenant-specific)
- `policy_rules` - Individual rules within policies (for indexing)
- `policy_templates` - Pre-built policy templates
- `policy_evaluations` - Audit log of policy evaluations
- `policy_conflicts` - Detected conflicts between policies

### Backend Service

**File:** `backend/services/iam_agent/app/services/policy_service.py`

The `PolicyService` provides:

- **Policy CRUD** - Create, read, update, delete policies
- **Policy Evaluation** - Evaluate policies against context
- **Template Management** - Create policies from templates
- **Conflict Detection** - Detect conflicting policies

**Key Methods:**

```python
def evaluate_policy(policy_type: str, context: EvaluationContext) -> PolicyEvaluationResult
```

Evaluates policies of a given type against a context (user, resource, IP, risk level, etc.) and returns:
- Result: `allow`, `deny`, `step_up`, `require_approval`
- Matched rules
- Actions to take

### API Endpoints

**File:** `backend/services/iam_agent/app/api/policies.py`

- `POST /api/iam-portal/policies` - Create policy
- `GET /api/iam-portal/policies` - List policies
- `GET /api/iam-portal/policies/{id}` - Get policy
- `PUT /api/iam-portal/policies/{id}` - Update policy
- `DELETE /api/iam-portal/policies/{id}` - Delete policy
- `GET /api/iam-portal/policies/templates` - List templates
- `POST /api/iam-portal/policies/templates/{id}/create` - Create from template
- `POST /api/iam-portal/policies/evaluate` - Evaluate policy
- `GET /api/iam-portal/policies/{id}/analyze` - Analyze policy
- `POST /api/iam-portal/policies/{id}/explain` - AI explanation
- `POST /api/iam-portal/policies/generate` - Generate from natural language

### Frontend Components

#### Policies Page
**File:** `frontend/src/app/dashboard/iam/policies/page.tsx`

- Tabs for each policy type (Sign-on, Access, Approval, SoD)
- List of policies with edit/delete actions
- Template selection modal
- Integration with policy editor

#### Policy Editor
**File:** `frontend/src/components/iam/PolicyEditor.tsx`

- Rule-based editor (simplified version)
- Add/edit/delete rules
- Define conditions and actions
- Save policy with validation

**Future Enhancement:** Full drag-and-drop graph editor using React Flow

## Integration Points

### 1. Sign-on Policies

**Enforcement Point:** Login Proxy / Access Gateway

After Keycloak authentication:
1. Get user context (IP, country, device, risk score)
2. Evaluate sign-on policies
3. If `step_up`: require additional MFA/WebAuthn
4. If `deny`: block sign-in
5. If `allow`: proceed

**Keycloak Integration:**
- Some policies can be pushed to Keycloak auth flows
- Others enforced by SentinelGrid's login proxy

### 2. Access Policies

**Enforcement Point:** IAM Service

When granting entitlements:
1. Evaluate access policies
2. If `deny`: reject entitlement grant
3. If `require_approval`: create approval workflow
4. If `allow`: proceed with grant

**Keycloak Integration:**
- Policies control which Keycloak groups/roles can be assigned
- IAM Service enforces policies before updating Keycloak

### 3. Approval Policies

**Enforcement Point:** Access Request Engine

When processing access requests:
1. Evaluate approval policies
2. Determine required approvers (manager, app owner, security)
3. Create approval tasks
4. Only grant when approvals complete

**Keycloak Integration:**
- Policies drive workflow, not Keycloak directly
- IAM Service updates Keycloak after approvals

## Policy Templates

Templates provide pre-built policies for common scenarios:

### Sign-on Templates
- "Secure Admin Sign-on" - Admins must use WebAuthn, block high-risk countries
- "Standard Employee Sign-on" - Basic MFA, allow from trusted locations
- "Contractor Sign-on" - Restricted hours, additional verification

### Access Templates
- "Production Access" - Requires manager + owner approval
- "Read-only Access" - Auto-approved for standard employees
- "Privileged Access" - Multi-level approval required

### Approval Templates
- "Basic Privileged Access Approvals" - Manager approval required
- "High-Risk Approvals" - Manager + security approval
- "Temporary Access Approvals" - Auto-expire after duration

## UX Flows

### Flow 1: Edit "Admin Sign-on Policy"

1. Navigate to **Policies → Sign-on Policies**
2. Click on "Admin Sign-on Policy" (or create new)
3. Policy editor opens
4. View/edit rules:
   - Rule 1: Admin + low/medium risk → Require MFA → Allow
   - Rule 2: Admin + high risk → Require WebAuthn → If fail → Deny
5. Save policy
6. Policy is automatically enforced on next sign-on

### Flow 2: "Who can get Production AWS access?"

1. Navigate to **Apps → AWS Prod Account → Access Rules**
2. View existing access policy
3. Click "Edit rule"
4. Policy editor opens, pre-filtered to AWS Prod
5. Define conditions:
   - Department = "Engineering"
   - Team = "Platform"
   - Employment type ≠ contractor
6. Define workflow:
   - Require manager approval
   - Require AWS owner approval for >8 hours
7. Save policy
8. Policy is evaluated when users request AWS Prod access

### Flow 3: Define Approval Policy

1. Navigate to **Policies → Approval & Workflow**
2. Click "New Policy" or use template
3. Define trigger: "Any request for privileged entitlements"
4. Define conditions:
   - Requester's manager exists?
   - Risk score < threshold?
5. Define actions:
   - If low risk → require manager approval
   - If medium/high risk → manager + security approver
   - Auto-expire entitlement in 4 hours
6. Save policy
7. Policy is used when processing access requests

## AI Integration

### Policy Explanation

Click "Explain" button in policy editor:
- AI generates human-readable explanation
- Explains what each rule does
- Highlights potential issues
- Provides recommendations

### Policy Generation

Use natural language to generate policies:
- "Only admins can log in from outside US/EU"
- "Production access requires manager and owner approval"
- "Block logins from high-risk countries"

AI generates policy DSL that can be reviewed and customized.

### Conflict Detection

AI analyzes policies to detect:
- Overlapping rules
- Contradictory policies
- Circular dependencies
- Overly permissive rules

## Keycloak Abstraction

**Customers never see:**
- Keycloak groups
- Keycloak roles
- Keycloak clients
- Keycloak JSON configuration
- Keycloak auth flows

**Customers only see:**
- Policies (human-readable rules)
- Conditions (role, location, risk, etc.)
- Actions (require MFA, deny, approve, etc.)

**Behind the scenes:**
- IAM Service compiles policies into Keycloak settings
- Some policies → Keycloak auth flows
- Some policies → SentinelGrid enforcement points
- All policies → Audit logs

## Future Enhancements

1. **Full Graph Editor** - Drag-and-drop visual policy builder
2. **Policy Testing** - Test policies against sample contexts
3. **Policy Versioning** - Track policy changes over time
4. **Policy Analytics** - See how often policies are triggered
5. **Advanced SoD** - Complex separation of duties rules
6. **Risk-Based Policies** - AI-driven risk scoring integration
7. **External Provisioning** - Policies that trigger external system changes

## Testing

### Backend Testing

```bash
cd backend/services/iam_agent
pytest tests/test_policy_service.py
```

### Policy Evaluation Testing

```python
context = EvaluationContext(
    user_id="user-123",
    roles=["sg_admin"],
    ip_address="192.168.1.1",
    country="US",
    risk_level="high"
)

result = policy_service.evaluate_policy("signon", context)
assert result.result == "step_up"
assert "require_webauthn" in [a.type for a in result.actions]
```

## Configuration

### Environment Variables

```bash
# Policy evaluation
POLICY_EVALUATION_ENABLED=true
POLICY_CACHE_TTL=3600

# AI integration (for explanations/generation)
AI_SERVICE_URL=http://ai_service:8000
```

## Migration

To apply the database migration:

```bash
psql -U sg -d sg -f backend/migrations/016_iam_policies_schema.sql
```

## Summary

The Policy Editor makes SentinelGrid's IAM system feel fundamentally different from Keycloak by:

1. **Abstraction** - High-level policy DSL, no Keycloak concepts
2. **Visual Editor** - Graphical interface (even if simplified initially)
3. **Templates** - Pre-built policies for common scenarios
4. **AI Integration** - Natural language explanations and generation
5. **Business Logic** - Policies drive workflows, not just Keycloak config

This creates a frictionless experience where admins think in business terms (who, what, when) rather than technical Keycloak concepts.

