# Out-of-the-Box (OOTB) Playbooks Implementation

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

SentinelGrid ships with 12 built-in playbooks aligned with NIST IR phases, MITRE ATT&CK, and NIST SP 800-53 controls. These playbooks provide "sane defaults" for common security incidents and can be cloned/customized by tenants.

## Playbook List

1. **PHISH-USER-REPORTED-v1** - Phishing – User Reported
2. **PHISH-GATEWAY-ALERT-v1** - Phishing – Email Security Alert
3. **ID-ACCOUNT-COMPROMISE-v1** - Account Compromise / Suspicious Login
4. **ID-PASSWORD-SPRAY-v1** - Password Spray / Brute Force Attack
5. **MAL-GENERIC-ENDPOINT-v1** - Malware – Endpoint Infection
6. **MAL-RANSOMWARE-v1** - Ransomware – Suspected / Confirmed
7. **CSPM-PUBLIC-STORAGE-v1** - Cloud – Public Storage Misconfiguration
8. **CLOUD-SUSPICIOUS-API-v1** - Cloud – Suspicious API Activity
9. **DATA-EXFIL-v1** - Data Exfiltration / Unusual Downloads
10. **WEB-WAF-ATTACK-v1** - Web Application Attack (WAF Alert)
11. **ADMIN-ABUSE-REMOTE-TOOLS-v1** - Suspicious Use of Admin Tools / Remote Access
12. **DEVICE-LOST-STOLEN-v1** - Lost / Stolen Device (Laptop / Mobile)

## Architecture

### Database Schema

The `playbooks` table has been enhanced with OOTB-specific fields:

- `playbook_key` - Unique identifier (e.g., "PHISH-USER-REPORTED-v1")
- `is_builtin` - Boolean flag marking SentinelGrid built-in playbooks
- `severity_default` - Default severity level
- `applicable_sources` - Data sources this playbook applies to
- `triggers` - Trigger conditions
- `prerequisites` - Prerequisites required
- `artifacts_required` - Required artifacts
- `phases` - NIST IR phases structure (JSONB)
- `cis_controls` - CIS Controls mapping

### Playbook Structure

Each playbook follows a consistent NIST IR structure:

1. **Metadata** - Name, category, severity, triggers, prerequisites
2. **Phases** - NIST IR lifecycle phases:
   - Preparation (optional)
   - Detection & Analysis
   - Containment
   - Eradication & Recovery
   - Post-Incident
3. **Framework Mappings** - MITRE ATT&CK, NIST SP 800-53, CIS Controls
4. **Workflow** - React Flow workflow structure (auto-generated from phases)

### Phase-to-Workflow Conversion

The `playbook_seeder.py` service converts NIST phase structure to React Flow format:

- Each phase becomes a visual swimlane
- Each step becomes a node (action, decision, or manual)
- Edges connect steps sequentially
- Phase headers provide visual grouping

## Implementation Files

### Database Migration

- `backend/migrations/007_ootb_playbooks.sql` - Adds OOTB fields to playbooks table

### Playbook Definitions

- `backend/services/soar_agent/app/data/ootb_playbooks.yaml` - YAML definitions for all 12 playbooks

### Services

- `backend/services/soar_agent/app/services/playbook_seeder.py` - Seeding and cloning logic
- `backend/services/soar_agent/app/api/ootb_playbooks.py` - API endpoints for OOTB playbooks

### Scripts

- `backend/services/soar_agent/scripts/seed_ootb_playbooks.py` - Standalone seeding script

## Usage

### Seeding Playbooks

#### Option 1: Via API Endpoint

```bash
curl -X POST http://localhost:8004/soar/ootb/seed \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant-id>"
```

#### Option 2: Via Script

```bash
cd backend/services/soar_agent
python scripts/seed_ootb_playbooks.py
```

#### Option 3: Via Python Module

```python
from app.services.playbook_seeder import seed_all_ootb_playbooks
from app.core.database import get_db

db = next(get_db())
seeded = seed_all_ootb_playbooks(db)
```

### Listing OOTB Playbooks

```bash
curl http://localhost:8004/soar/ootb \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant-id>"
```

### Cloning a Playbook for Customization

```bash
curl -X POST http://localhost:8004/soar/ootb/PHISH-USER-REPORTED-v1/clone \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant-id>" \
  -H "Content-Type: application/json" \
  -d '{"new_name": "My Custom Phishing Playbook"}'
```

## UI Integration

### Playbook Editor

The graphical drag-and-drop playbook editor can:

1. **View Built-in Playbooks** - Display OOTB playbooks as read-only templates
2. **Clone for Customization** - Create a tenant-specific copy
3. **Edit Custom Playbooks** - Modify cloned playbooks
4. **Visual Phase Display** - Show NIST phases as swimlanes

### Playbook Library

The UI should display:

- **Built-in Playbooks** section with all 12 OOTB playbooks
- **Custom Playbooks** section with tenant-specific playbooks
- **Clone** button on each OOTB playbook
- **Locked** indicator on built-in playbooks (cannot be deleted/modified directly)

## Framework Mappings

Each playbook includes:

### MITRE ATT&CK

- **Tactics** - High-level adversary tactics (e.g., TA0001 - Initial Access)
- **Techniques** - Specific techniques (e.g., T1566.001 - Spearphishing Attachment)

### NIST SP 800-53

- Control IDs mapped to playbook steps (e.g., IR-4, AC-2, SI-3)

### CIS Controls

- CIS Control IDs (e.g., "4", "7", "8")

## Vector DB Integration

Playbook descriptions and steps are indexed in the vector database for:

- **SecGPT Recommendations** - AI can suggest appropriate playbooks for alerts
- **Natural Language Guidance** - AI can reference specific playbook steps
- **Context-Aware Help** - AI can explain playbook phases and actions

## Customization Workflow

1. Tenant views OOTB playbook library
2. Tenant selects a playbook to customize
3. System creates a clone (marked as `is_builtin=False`)
4. Tenant modifies the cloned playbook via drag-and-drop editor
5. Custom playbook is saved and available for execution

## Protection

Built-in playbooks are protected:

- Cannot be deleted (`is_builtin=True`)
- Cannot be modified directly
- Can only be cloned
- Original remains available for all tenants

## Future Enhancements

- **Versioning** - Support multiple versions of OOTB playbooks
- **Updates** - Push updates to built-in playbooks
- **Analytics** - Track which playbooks are most used
- **Community Playbooks** - Allow sharing of custom playbooks
- **Playbook Marketplace** - Third-party playbook integrations

## Testing

Run the smoketest to ensure OOTB playbooks are seeded:

```bash
pytest backend/tests/test_hero_flow_*_suite.py -v
```

The playbooks should be available for:
- Hero Flow 2 (Suspicious Login)
- Hero Flow 3 (Phishing Triage)
- Hero Flow 4 (Automated Threat Response)
- Hero Flow 5 (Compliance Remediation)

