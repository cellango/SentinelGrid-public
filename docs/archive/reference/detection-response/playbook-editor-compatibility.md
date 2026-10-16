# Playbook Editor Compatibility Guide

> **Historical reference — superseded for release decisions.** This records an earlier design, operation, or validation attempt. It is not the current architecture, a supported quick start, or evidence that the source preview is production ready. Start with the repository README and current documentation index.


## Overview

All 10 SOC/SOAR playbooks are fully compatible with the SentinelGrid Playbook Editor. This document explains how the playbooks work with the editor and how to customize them.

## Architecture

### Phase-to-Workflow Conversion

The playbooks are defined in YAML format using **NIST IR phases** structure:

```yaml
phases:
  - name: "Detection & Analysis"
    steps:
      - id: collect_email
        label: "Collect reported email"
        type: automated
        actor: system
```

The `playbook_seeder.py` service automatically converts these phases into **React Flow workflow format** for the editor:

- Each **phase** becomes a visual swimlane (grouped nodes)
- Each **step** becomes a node (action, decision, or manual)
- **Edges** connect steps sequentially
- **Phase headers** provide visual grouping

### Storage Format

Playbooks are stored in the database with **both formats**:

1. **Original Phases** (`phases` field): NIST IR phase structure (JSON)
2. **React Flow Workflow** (`workflow` field): Editor-compatible format (JSON)

This dual storage allows:
- **Viewing** playbooks in the visual editor
- **Editing** playbooks via drag-and-drop
- **Preserving** the original phase structure for documentation

## Built-in vs. Custom Playbooks

### Built-in Playbooks

- **Read-only**: Cannot be modified directly
- **Shared**: Available to all tenants
- **Versioned**: Tracked by playbook key (e.g., `ATO-SUSPICIOUS-LOGIN-v2`)
- **Clonable**: Can be cloned for customization

### Custom Playbooks (Cloned)

- **Editable**: Can be modified in the Playbook Editor
- **Tenant-specific**: Belongs to the tenant that cloned it
- **No key**: Custom playbooks don't have a playbook key
- **Full control**: All aspects can be customized

## Editing Playbooks

### Step 1: Clone a Built-in Playbook

1. Navigate to **Playbooks** → **Built-in Playbooks**
2. Find the playbook you want to customize
3. Click **Clone** button
4. Give it a new name (e.g., "Suspicious Login - Custom")

### Step 2: Open in Playbook Editor

1. Navigate to **Playbooks** → **Custom Playbooks**
2. Click on your cloned playbook
3. Click **Edit** button
4. Playbook opens in the visual editor

### Step 3: Edit Workflow

The editor displays:
- **Phase Headers**: Visual grouping by NIST IR phase
- **Action Nodes**: Automated steps (blue)
- **Decision Nodes**: Analyst decision points (yellow, circular)
- **Manual Nodes**: Manual analyst steps (blue)

You can:
- **Add Nodes**: Drag new nodes from the palette
- **Modify Nodes**: Click a node to edit its properties
- **Reorder Steps**: Drag nodes to reorder
- **Add Connections**: Connect nodes with edges
- **Delete Nodes**: Remove unnecessary steps

### Step 4: Save Changes

1. Click **Save** button
2. Changes are saved to the database
3. Workflow is updated (phases are preserved for reference)

## Node Types

### Action Node (Automated)
- **Type**: `action`
- **Color**: Blue
- **Actor**: `system`
- **Purpose**: Automated steps executed by the system

### Decision Node
- **Type**: `decision`
- **Color**: Yellow (circular)
- **Actor**: `analyst`
- **Purpose**: Analyst decision points requiring review

### Manual Node
- **Type**: `manual`
- **Color**: Blue
- **Actor**: `analyst` or `manager`
- **Purpose**: Manual steps requiring analyst action

## Phase Structure

The playbooks follow NIST IR phases:

1. **Detection & Analysis**: Initial detection and analysis
2. **Containment**: Immediate containment actions
3. **Eradication & Recovery**: Remediation and recovery
4. **Post-Incident**: Lessons learned and improvements

Some playbooks may include:
- **Preparation**: Pre-incident preparation (optional)

## Action References

Automated steps reference actions via `action_ref`:

```yaml
action_ref: "connector:email:fetch_message"
action_ref: "workflow:block_iocs"
action_ref: "iam:terminate_sessions"
```

These references map to:
- **Connectors**: External system integrations
- **Workflows**: Multi-step automated processes
- **Services**: Internal SentinelGrid services

## Best Practices

### When Customizing

1. **Preserve Phase Structure**: Keep NIST IR phases for consistency
2. **Document Changes**: Add notes explaining why you changed something
3. **Test First**: Test custom playbooks in non-production
4. **Version Control**: Consider versioning custom playbooks

### When Adding Steps

1. **Use Appropriate Node Type**: Automated vs. manual vs. decision
2. **Set Correct Actor**: System, analyst, or manager
3. **Add Action References**: For automated steps, specify action_ref
4. **Update Descriptions**: Clear descriptions help analysts

### When Modifying Triggers

1. **Keep Original Triggers**: Don't remove original triggers unless necessary
2. **Add Tenant-Specific Triggers**: Add triggers specific to your environment
3. **Test Trigger Logic**: Ensure triggers fire correctly

## Troubleshooting

### Playbook Won't Load in Editor

- **Check Format**: Ensure workflow field contains valid React Flow JSON
- **Check Permissions**: Ensure you have edit permissions
- **Check Status**: Ensure playbook is not disabled

### Changes Not Saving

- **Check Permissions**: Ensure you have edit permissions
- **Check Validation**: Ensure workflow structure is valid
- **Check Network**: Ensure API calls are succeeding

### Phase Headers Not Showing

- **Check Phase Data**: Ensure phases field contains phase structure
- **Check Conversion**: Phases should convert to phase header nodes
- **Check Editor Version**: Ensure editor supports phase headers

## API Integration

### Loading Playbook

```http
GET /api/v1/playbooks/{playbook_id}
```

Response includes:
- `workflow`: React Flow format for editor
- `phases`: Original phase structure
- `is_builtin`: Whether playbook is built-in
- `is_template`: Whether playbook is a template

### Saving Playbook

```http
PUT /api/v1/playbooks/{playbook_id}
```

Request includes:
- `workflow`: Updated React Flow format
- `phases`: Updated phase structure (optional, auto-generated)

### Cloning Playbook

```http
POST /api/v1/playbooks/{playbook_id}/clone
```

Request includes:
- `new_name`: Name for cloned playbook
- `tenant_id`: Tenant to create playbook for

## Example: Customizing Phishing Playbook

### Original Built-in Playbook
- **ID**: `PHISH-USER-REPORTED-v2`
- **Steps**: Standard phishing response steps

### Customized Version
1. **Clone** the playbook
2. **Add Step**: Add "Notify user's manager" step
3. **Modify Step**: Change "Send awareness note" to include specific template
4. **Save** changes

### Result
- Original playbook remains unchanged
- Custom playbook available for your tenant
- Can be further customized as needed

## Summary

✅ **All 10 playbooks are editor-compatible**
✅ **Built-in playbooks can be cloned for customization**
✅ **Custom playbooks are fully editable**
✅ **Phase structure is preserved for documentation**
✅ **Workflow format supports visual editing**

For questions or issues, contact the SOC team or refer to the [SOC Playbooks SOP](soc-playbooks-sop.md).

