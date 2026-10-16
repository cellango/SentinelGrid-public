# Workflow Technology Evaluation & Recommendation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


**Date:** 2025-11-28  
**Status:** Decision Document  
**Purpose:** Evaluate workflow technologies for multiple SentinelGrid use cases

---

## Executive Summary

We need a unified workflow technology solution that can handle:
1. **SOAR Playbooks** - Drag-and-drop incident response playbooks
2. **IAM Policy Builder** - Visual policy editor (similar to Keycloak's authorization policies)
3. **General Workflows** - Access certification workflows, audit campaigns

**Recommendation:** **React Flow (Custom Implementation)** + **Embedded n8n (for SOAR)**

---

## Use Cases Overview

### Use Case 1: SOAR Playbooks
**Requirements:**
- Drag-and-drop playbook builder
- Pre-built nodes for common actions (isolate endpoint, block IP, create ticket, etc.)
- Conditional logic, loops, parallel execution
- Integration with TheHive, SIEM, EDR, ticketing systems
- Execution engine (runs workflows)
- State management during execution

**Example Flow:**
```
Alert Trigger → Triage → If High Severity → 
  → Isolate Endpoint → Block IP → Create Ticket → Notify Team
```

### Use Case 2: IAM Policy Builder (Keycloak-style)
**Requirements:**
- Visual policy composition
- Policy types: Role-based, Resource-based, Time-based, IP-based
- Combine policies with operators (AND, OR, NOT)
- Visual representation of policy logic tree
- Generate Keycloak JSON policy format
- Support for ABAC (Attribute-Based Access Control)

**Keycloak Policy Example:**
```json
{
  "type": "aggregate",
  "logic": "POSITIVE",
  "decisionStrategy": "AFFIRMATIVE",
  "policies": [
    {
      "type": "role",
      "roles": ["SOC_MANAGER"]
    },
    {
      "type": "time",
      "dayMonth": "*",
      "dayMonthEnd": "*",
      "hour": "9-17"
    }
  ]
}
```

**Visual Representation:**
```
            [AND Gate]
           /         \
    [Role Policy]  [Time Policy]
    SOC_MANAGER    9 AM - 5 PM
```

### Use Case 3: General Workflows (Access Certification)
**Requirements:**
- Certification workflow builder
- Approval workflows (multi-stage)
- Notification triggers
- Task assignments
- State tracking
- Integration with Entitlement Agent API

**Example Flow:**
```
Campaign Start → Generate Certifications → 
  → Notify Users → Wait for Response → 
  → If Pending > 7 days → Send Reminder →
  → After Deadline → Auto-Revoke Uncertified
```

---

## Technology Options Analysis

### Option 1: n8n (Embedded Workflow Engine)

**Description:**
n8n is an open-source workflow automation platform with a built-in visual editor. It can be self-hosted and embedded.

**Pros:**
- ✅ **Mature workflow engine** - Production-ready, battle-tested
- ✅ **Built-in execution engine** - Handles workflow execution, retries, error handling
- ✅ **400+ integrations** - Pre-built connectors for common services
- ✅ **Visual editor** - Drag-and-drop interface already built
- ✅ **Event-driven & scheduled** - Supports triggers and scheduling
- ✅ **Self-hostable** - Can deploy in our infrastructure
- ✅ **API-first** - Can be controlled via REST API
- ✅ **Good for SOAR** - Perfect fit for playbook automation

**Cons:**
- ❌ **Hard to embed** - Not designed as a library, would need iframe or separate service
- ❌ **Limited customization** - UI is fixed, hard to brand/style to match our design
- ❌ **Overkill for simple workflows** - May be too complex for IAM policy builder
- ❌ **Policy builder mismatch** - n8n is action-oriented, not policy-oriented
- ❌ **Tight coupling** - Would require adapting our use cases to n8n's model
- ❌ **License considerations** - Community version is free, but enterprise features require paid license

**Embedding Options:**
1. **Iframe approach** - Embed n8n UI in iframe (not ideal UX)
2. **Separate service** - Deploy n8n as microservice, use API (better but still disconnected)
3. **Fork and customize** - Significant development effort

**Best For:**
- ✅ SOAR Playbooks (standalone service)
- ⚠️ General workflows (if we can work with API-only)
- ❌ IAM Policy Builder (not a good fit)

---

### Option 2: React Flow (Custom Implementation)

**Description:**
React Flow is a React library for building node-based, interactive graphs and workflows. It provides the canvas and node system, but you build everything else.

**Pros:**
- ✅ **Full control** - Complete customization of UI, nodes, edges
- ✅ **React-native** - Fits perfectly with our Next.js/React stack
- ✅ **Lightweight** - Only the visualization layer, no execution engine
- ✅ **Flexible** - Can model any type of workflow (playbooks, policies, certifications)
- ✅ **Branding** - Can style to match SentinelGrid design system
- ✅ **No vendor lock-in** - Own the code, full control
- ✅ **Policy builder support** - Can create custom nodes for policy types
- ✅ **Good performance** - Optimized for rendering large graphs
- ✅ **Active development** - Well-maintained, active community

**Cons:**
- ❌ **No execution engine** - Need to build workflow execution ourselves
- ❌ **More development** - Significant frontend work required
- ❌ **No pre-built integrations** - Need to build all connectors
- ❌ **Testing burden** - Must thoroughly test execution logic

**Best For:**
- ✅ IAM Policy Builder (perfect fit - visual composition)
- ✅ General Workflows (good fit - full control)
- ⚠️ SOAR Playbooks (need to build execution engine)

---

### Option 3: Hybrid: React Flow + n8n API

**Description:**
Build custom React Flow UI for IAM Policy Builder and General Workflows. Use n8n as backend execution engine for SOAR playbooks.

**Pros:**
- ✅ **Best of both worlds** - Visual control where needed, execution engine for complex workflows
- ✅ **IAM Policy Builder** - React Flow for visual composition
- ✅ **SOAR Playbooks** - n8n for execution (API-driven)
- ✅ **Flexibility** - Can evolve each independently

**Cons:**
- ❌ **Two systems** - More to maintain
- ❌ **Different UX** - Two different interfaces
- ⚠️ **SOAR UI** - Would still need iframe or separate window for n8n editor

**Best For:**
- ✅ IAM Policy Builder (React Flow)
- ✅ General Workflows (React Flow + custom execution)
- ⚠️ SOAR Playbooks (n8n backend, but UI still needs work)

---

### Option 4: Custom Solution (React Flow + Execution Engine)

**Description:**
Build everything custom using React Flow for visualization and our own execution engine.

**Pros:**
- ✅ **Complete control** - Own everything, no dependencies
- ✅ **Unified UX** - Single interface for all workflows
- ✅ **Perfect fit** - Built specifically for our use cases
- ✅ **Integration** - Native integration with SentinelGrid services
- ✅ **Policy builder** - Can create specialized UI for IAM policies

**Cons:**
- ❌ **Development time** - Significant effort to build execution engine
- ❌ **Risk** - Need to handle edge cases, error handling, retries
- ❌ **Maintenance** - Ongoing maintenance burden

**Best For:**
- ✅ All use cases (if we have time/resources)
- ❌ Not recommended for MVP (too much work)

---

### Option 5: Other Tools

#### StackStorm
- **Pros:** Powerful workflow engine, Python-based, good for SOAR
- **Cons:** Older tech, less modern UI, harder to embed

#### Temporal
- **Pros:** Excellent execution engine, fault-tolerant
- **Cons:** No visual builder, would need to build UI ourselves

#### Camunda
- **Pros:** BPMN-based, enterprise-grade
- **Cons:** BPMN may be too complex for our use cases, Java-based

#### Rete.js
- **Pros:** Framework for building node editors
- **Cons:** Less popular than React Flow, smaller community

---

## Detailed Comparison Matrix

| Feature | n8n (Embedded) | React Flow (Custom) | Hybrid | Custom Solution |
|---------|----------------|---------------------|--------|-----------------|
| **Visual Editor** | ✅ Built-in | ✅ Custom build | ✅ Custom + n8n | ✅ Custom build |
| **Execution Engine** | ✅ Built-in | ❌ Need to build | ✅ n8n + Custom | ❌ Need to build |
| **IAM Policy Builder** | ❌ Not suitable | ✅ Perfect fit | ✅ React Flow | ✅ Perfect fit |
| **SOAR Playbooks** | ✅ Perfect fit | ⚠️ Need execution | ✅ n8n backend | ⚠️ Need execution |
| **General Workflows** | ⚠️ Overkill | ✅ Good fit | ✅ React Flow | ✅ Good fit |
| **Development Time** | Low (embed) | Medium | Medium-High | High |
| **Customization** | ❌ Limited | ✅ Full control | ⚠️ Mixed | ✅ Full control |
| **Branding/UX** | ❌ Fixed | ✅ Full control | ⚠️ Mixed | ✅ Full control |
| **Integration** | ✅ 400+ built-in | ❌ Need to build | ⚠️ Mixed | ❌ Need to build |
| **Maintenance** | ✅ Community | ✅ Own code | ⚠️ Two systems | ✅ Own code |
| **License** | ⚠️ Community/Paid | ✅ MIT (React Flow) | ⚠️ Mixed | ✅ Own code |

---

## Recommended Approach: **Hybrid Solution (Phase 1 & 2)**

### Phase 1: React Flow for IAM Policy Builder & General Workflows

**Rationale:**
- IAM Policy Builder needs custom UI that matches our design system
- General workflows (certifications) can be simpler, don't need complex execution
- React Flow gives us full control and flexibility

**Implementation:**
```
IAM Policy Builder:
├── React Flow canvas
├── Custom nodes: Role Policy, Time Policy, IP Policy, Resource Policy, Aggregate
├── Visual operators: AND, OR, NOT gates
├── Policy JSON generator
└── Keycloak API integration

General Workflows:
├── React Flow canvas
├── Custom nodes: Task, Approval, Notification, Wait, API Call
├── Simple execution engine (workflow state machine)
└── Integration with Entitlement Agent
```

### Phase 2: n8n for SOAR Playbooks (Separate Service)

**Rationale:**
- SOAR playbooks need powerful execution engine
- n8n has built-in retries, error handling, integrations
- Can deploy as separate microservice, use API to trigger workflows

**Implementation:**
```
SOAR Service:
├── Deploy n8n as microservice (soar-workflow-engine)
├── Pre-configure common playbook templates
├── n8n REST API wrapper (soar-agent service)
├── Integration with TheHive, SIEM, EDR
└── Optional: Embed n8n UI in iframe (or provide link to separate UI)
```

### Phase 3: Unified UI (Future)

**Future Enhancement:**
- Build custom React Flow UI for SOAR playbooks
- Use n8n execution engine via API
- Unified workflow experience across all use cases

---

## Architecture: Hybrid Approach

```
┌─────────────────────────────────────────────────────────┐
│                   SentinelGrid Frontend                  │
│                    (Next.js + React)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │  IAM Policy      │  │  General         │           │
│  │  Builder         │  │  Workflows       │           │
│  │  (React Flow)    │  │  (React Flow)    │           │
│  └────────┬─────────┘  └────────┬─────────┘           │
│           │                      │                      │
│           │                      │                      │
│  ┌────────▼──────────────────────▼──────────┐         │
│  │     Workflow Execution Service            │         │
│  │     (Custom - Simple State Machine)       │         │
│  └───────────────────────────────────────────┘         │
│                                                          │
│  ┌──────────────────────────────────────────┐          │
│  │   SOAR Playbook Builder (Link to n8n)    │          │
│  │   or Embedded n8n UI (iframe)            │          │
│  └──────────────────┬───────────────────────┘          │
└─────────────────────┼───────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────┐
        │   n8n Workflow Engine   │
        │   (Separate Service)    │
        │   - Playbook Execution  │
        │   - Integrations        │
        │   - Error Handling      │
        └─────────────────────────┘
```

---

## Implementation Plan

### Phase 1: React Flow Foundation (Weeks 1-4)

**Week 1-2: Setup & IAM Policy Builder**
- [ ] Install and configure React Flow
- [ ] Design policy node types (Role, Time, IP, Resource, Aggregate)
- [ ] Build policy builder UI
- [ ] Implement policy JSON generator
- [ ] Integrate with Keycloak Admin API

**Week 3-4: General Workflows (Certification)**
- [ ] Design workflow node types (Task, Approval, Notification, Wait)
- [ ] Build simple execution engine (state machine)
- [ ] Create workflow builder UI
- [ ] Integrate with Entitlement Agent

### Phase 2: n8n SOAR Integration (Weeks 5-6)

**Week 5: n8n Setup**
- [ ] Deploy n8n as Docker service
- [ ] Configure authentication
- [ ] Set up multi-tenancy (workflow isolation)
- [ ] Create playbook templates

**Week 6: Integration**
- [ ] Build soar-agent API wrapper for n8n
- [ ] Implement playbook execution endpoints
- [ ] Add n8n UI link/iframe to SentinelGrid
- [ ] Document playbook creation process

### Phase 3: Enhanced SOAR UI (Future)

- [ ] Build custom React Flow UI for SOAR playbooks
- [ ] Connect to n8n execution engine via API
- [ ] Unified workflow experience

---

## Technology Stack

### React Flow Components

**Core:**
- `reactflow` - Main library
- `@xyflow/react` - Latest version (v11+)

**UI Components:**
- Custom node components (React components)
- Custom edge components
- Toolbar and controls

**Execution Engine (Custom):**
- State machine (XState or custom)
- Workflow persistence (PostgreSQL)
- Execution queue (Celery or simple async tasks)

### n8n Setup

**Deployment:**
- Docker container
- PostgreSQL database for workflow storage
- Redis for execution queue

**Configuration:**
- Environment variables for multi-tenancy
- API authentication
- Workflow templates

---

## Keycloak Policy Builder Reference

### Keycloak Authorization Model

Keycloak supports various policy types:
- **Role-based** - User has role
- **User-based** - Specific users
- **Time-based** - Time of day, day of week
- **Client-based** - Client requesting access
- **Group-based** - User in group
- **IP-based** - IP address range
- **Aggregate** - Combine multiple policies
- **JavaScript** - Custom logic

### Visual Representation Needed

```
[AND] Gate
├── [Role Policy] → SOC_MANAGER
├── [Time Policy] → 9 AM - 5 PM, Weekdays
└── [IP Policy] → 10.0.0.0/8 OR Office IPs

Result: Allow if user has SOC_MANAGER role AND 
        it's between 9-5 on weekdays AND 
        IP is in allowed range
```

### Policy JSON Structure

```json
{
  "type": "aggregate",
  "logic": "POSITIVE",
  "decisionStrategy": "AFFIRMATIVE",
  "policies": [
    {
      "type": "role",
      "roles": [{"id": "...", "required": true}]
    },
    {
      "type": "time",
      "dayMonth": "*",
      "dayMonthEnd": "*",
      "hour": "9",
      "minute": "0",
      "hourEnd": "17",
      "minuteEnd": "0"
    },
    {
      "type": "aggregate",
      "logic": "POSITIVE",
      "decisionStrategy": "UNANIMOUS",
      "policies": [
        {"type": "ip", "ipAddress": "10.0.0.0/8"},
        {"type": "ip", "ipAddress": "192.168.1.0/24"}
      ]
    }
  ]
}
```

---

## File Structure

```
frontend/src/
├── components/
│   ├── workflows/
│   │   ├── ReactFlowCanvas.tsx          # Base React Flow canvas
│   │   ├── nodes/
│   │   │   ├── PolicyNode.tsx           # IAM Policy nodes
│   │   │   ├── WorkflowNode.tsx         # General workflow nodes
│   │   │   └── SOARNode.tsx             # SOAR playbook nodes (future)
│   │   ├── edges/
│   │   │   └── CustomEdge.tsx
│   │   └── toolbar/
│   │       ├── NodePalette.tsx
│   │       └── WorkflowControls.tsx
│   ├── iam/
│   │   ├── PolicyBuilder.tsx            # IAM Policy Builder page
│   │   ├── PolicyNodeTypes.tsx          # Policy node definitions
│   │   └── PolicyGenerator.tsx          # JSON generator
│   └── soar/
│       ├── PlaybookBuilder.tsx          # SOAR Playbook Builder (iframe or link)
│       └── PlaybookExecution.tsx        # Playbook execution status

backend/services/
├── workflow_execution/                  # Custom execution engine
│   ├── app/
│   │   ├── execution/
│   │   │   ├── engine.py                # State machine executor
│   │   │   ├── tasks.py                 # Task definitions
│   │   │   └── state.py                 # Workflow state management
│   │   └── api/
│   │       └── workflows.py             # Workflow API endpoints
├── soar_agent/
│   ├── app/
│   │   ├── n8n_client.py                # n8n API client
│   │   └── playbooks.py                 # Playbook management
└── iam_agent/
    └── app/
        └── policy/
            └── keycloak_policy.py       # Keycloak policy management
```

---

## Migration Path

### Phase 1: IAM Policy Builder (React Flow)
1. Build React Flow policy builder
2. Test with Keycloak API
3. Replace manual JSON editing

### Phase 2: General Workflows (React Flow)
1. Build workflow builder
2. Implement simple execution engine
3. Integrate with Entitlement Agent

### Phase 3: SOAR Playbooks (n8n)
1. Deploy n8n service
2. Create playbook templates
3. Integrate with soar-agent
4. Provide UI link/iframe

### Phase 4: Unified Experience (Future)
1. Build custom SOAR playbook UI (React Flow)
2. Connect to n8n execution engine
3. Unified workflow experience

---

## Decision Criteria

### Must Have
- ✅ Visual drag-and-drop interface
- ✅ Support for IAM policy composition
- ✅ Support for SOAR playbooks
- ✅ Integration with Keycloak
- ✅ Multi-tenant support
- ✅ Self-hostable (no SaaS dependency)

### Should Have
- ✅ Customizable UI/branding
- ✅ Built-in execution engine (for SOAR)
- ✅ Pre-built integrations (for SOAR)
- ✅ React/TypeScript compatible

### Nice to Have
- ✅ Unified UI for all workflows
- ✅ Advanced error handling
- ✅ Workflow versioning
- ✅ Workflow templates

---

## Final Recommendation

**Use React Flow for IAM Policy Builder and General Workflows**  
**Use n8n (as separate service) for SOAR Playbooks**

### Rationale:

1. **IAM Policy Builder** needs custom UI that matches our design - React Flow is perfect
2. **General Workflows** (certifications) are simpler - React Flow + simple execution engine is sufficient
3. **SOAR Playbooks** need powerful execution engine - n8n provides this out of the box
4. **Unified UX** can be achieved later by building custom SOAR UI that uses n8n execution engine

### Next Steps:

1. ✅ **Approve this recommendation**
2. **Start Phase 1** - React Flow for IAM Policy Builder
3. **Design policy node types** and visual representation
4. **Build MVP** of policy builder
5. **Phase 2** - General workflows with React Flow
6. **Phase 3** - Deploy n8n for SOAR playbooks

---

**Document Status:** Ready for Review  
**Next Action:** Approve recommendation and begin Phase 1 implementation

