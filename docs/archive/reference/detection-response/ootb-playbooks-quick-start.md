# OOTB Playbooks Quick Start Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

SentinelGrid ships with 12 Out-of-the-Box (OOTB) playbooks covering common security incidents. These playbooks are:

- **Built-in** - Available to all tenants
- **NIST-aligned** - Follow NIST SP 800-61 IR lifecycle
- **Framework-mapped** - Include MITRE ATT&CK and NIST SP 800-53 controls
- **Customizable** - Can be cloned and modified per tenant

## Quick Setup

### 1. Run Database Migration

```bash
# Apply the migration to add OOTB fields
psql -U sg -d sg -f backend/migrations/007_ootb_playbooks.sql
```

### 2. Seed OOTB Playbooks

#### Option A: Via API (Recommended)

```bash
curl -X POST http://localhost:8004/soar/ootb/seed \
  -H "Authorization: Bearer <admin-token>" \
  -H "X-Tenant-ID: <system-tenant-id>"
```

#### Option B: Via Script

```bash
cd backend/services/soar_agent
python scripts/seed_ootb_playbooks.py
```

### 3. Verify Playbooks

```bash
curl http://localhost:8004/soar/ootb \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <tenant-id>"
```

You should see 12 playbooks listed.

## Available Playbooks

| ID | Name | Category | Severity |
|---|---|---|---|
| PHISH-USER-REPORTED-v1 | Phishing – User Reported | email, identity | medium |
| PHISH-GATEWAY-ALERT-v1 | Phishing – Email Security Alert | email | medium |
| ID-ACCOUNT-COMPROMISE-v1 | Account Compromise / Suspicious Login | identity, siem | high |
| ID-PASSWORD-SPRAY-v1 | Password Spray / Brute Force Attack | identity, siem | high |
| MAL-GENERIC-ENDPOINT-v1 | Malware – Endpoint Infection | endpoint | high |
| MAL-RANSOMWARE-v1 | Ransomware – Suspected / Confirmed | endpoint, data | critical |
| CSPM-PUBLIC-STORAGE-v1 | Cloud – Public Storage Misconfiguration | cloud, data | high |
| CLOUD-SUSPICIOUS-API-v1 | Cloud – Suspicious API Activity | cloud | high |
| DATA-EXFIL-v1 | Data Exfiltration / Unusual Downloads | data, network | high |
| WEB-WAF-ATTACK-v1 | Web Application Attack (WAF Alert) | appsec, network | medium |
| ADMIN-ABUSE-REMOTE-TOOLS-v1 | Suspicious Use of Admin Tools / Remote Access | endpoint, identity | high |
| DEVICE-LOST-STOLEN-v1 | Lost / Stolen Device (Laptop / Mobile) | endpoint, data | medium |

## Using OOTB Playbooks

### View All OOTB Playbooks

```bash
GET /soar/ootb
```

### Clone a Playbook for Customization

```bash
POST /soar/ootb/{playbook_key}/clone
{
  "new_name": "My Custom Phishing Playbook"
}
```

This creates a copy you can edit in the playbook editor.

### Execute a Playbook

OOTB playbooks can be executed just like custom playbooks:

```bash
POST /soar/playbooks/{playbook_id}/execute
{
  "trigger_type": "alert",
  "trigger_id": "<alert-id>",
  "parameters": {}
}
```

## Playbook Structure

Each playbook includes:

### Metadata
- Name, description, category
- Default severity
- Applicable data sources
- Trigger conditions
- Prerequisites
- Required artifacts

### NIST IR Phases
1. **Detection & Analysis** - Identify and confirm incident
2. **Containment** - Limit damage
3. **Eradication & Recovery** - Remove threat and restore
4. **Post-Incident** - Document and improve

### Framework Mappings
- **MITRE ATT&CK** - Tactics and techniques
- **NIST SP 800-53** - Security controls
- **CIS Controls** - Best practices

### Workflow
- React Flow visual representation
- Automated and manual steps
- Decision points
- Action references for SOAR integration

## Integration with Hero Flows

OOTB playbooks are used in:

- **Hero Flow 2** - Suspicious Login (ID-ACCOUNT-COMPROMISE-v1)
- **Hero Flow 3** - Phishing Triage (PHISH-USER-REPORTED-v1)
- **Hero Flow 4** - Automated Threat Response (all playbooks)
- **Hero Flow 5** - Compliance Remediation (CSPM playbooks)

## Customization

1. **Clone** - Create a tenant-specific copy
2. **Edit** - Modify via drag-and-drop editor
3. **Save** - Store as custom playbook
4. **Execute** - Use like any other playbook

Built-in playbooks remain unchanged and available to all tenants.

## Troubleshooting

### Playbooks Not Appearing

1. Check migration was applied:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'playbooks' AND column_name = 'is_builtin';
   ```

2. Verify seeding completed:
   ```sql
   SELECT COUNT(*) FROM playbooks WHERE is_builtin = true;
   ```
   Should return 12.

3. Check logs:
   ```bash
   docker logs soar_agent | grep -i "seeded"
   ```

### Cloning Fails

- Ensure playbook_key exists
- Check tenant_id is valid
- Verify database permissions

### Workflow Not Rendering

- Check workflow JSON structure
- Verify React Flow node types
- Check browser console for errors

## Next Steps

1. **Review Playbooks** - Familiarize yourself with the 12 OOTB playbooks
2. **Test Execution** - Try executing a playbook manually
3. **Customize** - Clone and modify a playbook for your needs
4. **Integrate** - Connect playbooks to your SOAR workflows
5. **Extend** - Create additional custom playbooks as needed

