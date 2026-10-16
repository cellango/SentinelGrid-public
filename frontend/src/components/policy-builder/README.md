# Policy Builder Component

> **Experimental component reference.** This monorepo publishes source for developer review. Commands and capability descriptions below are not a supported runtime or current release certification. Read [the root preview scope](../../../../RELEASE_SCOPE.md) first.


A visual drag-and-drop interface for creating and managing tenant policy graphs.

## Features

- **Visual Policy Composition**: Drag-and-drop interface for creating policies
- **8 Policy Types**: Role, Time, IP, Group, Client, User, JavaScript, and Aggregate
- **Policy Templates**: Pre-built templates for common scenarios
- **Validation**: Real-time graph structure and policy validation
- **Undo/Redo**: Full history management with undo/redo support
- **Tenant Policy Integration**: Save and evaluate policies through the IAM tenant policy APIs
- **Import/Export**: JSON import/export for policy portability

## Usage

```tsx
import { PolicyBuilderCanvas } from '@/components/policy-builder';

<PolicyBuilderCanvas
  onSave={(nodes, edges) => {
    // Handle save
  }}
  onTest={(nodes, edges) => {
    // Handle test
  }}
  roles={roles} // Optional: for role policy configuration
/>
```

## Policy Types

### Role Policy
Grants access based on user roles. Configure which roles are required (all or any).

### Time Policy
Restricts access by time of day and day of week. Configure hours, minutes, and days.

### IP Policy
Restricts access by IP address or CIDR range. Supports multiple IP ranges.

### Group Policy
Grants access to users in specific groups.

### Client Policy
Restricts access by client application.

### User Policy
Grants access to specific users by ID or username.

### JavaScript Policy
Custom policy logic via JavaScript. Uses the policy graph's JavaScript node syntax.

### Aggregate Policy
Combines multiple policies with AND/OR/NOT logic. Supports decision strategies:
- **UNANIMOUS**: All policies must grant access
- **AFFIRMATIVE**: At least one policy grants access
- **CONSENSUS**: Majority of policies grant access

## Templates

Use pre-built templates for common scenarios:

1. **SOC Manager - Business Hours Only**: Role + Time policy
2. **Office IP Address Restriction**: IP-based access
3. **Admin OR Specific Users**: Role OR User policy
4. **Contractor Time Restrictions**: Role + Time restrictions
5. **Deny Outside Office IP**: Security IP denial
6. **Weekend Access Restriction**: Time-based denial

## Keyboard Shortcuts

- `Ctrl+Z` / `Cmd+Z`: Undo
- `Ctrl+Y` / `Cmd+Y`: Redo
- Click node: Select for editing
- Click canvas: Deselect

## Validation

The Policy Builder validates:
- Graph connectivity (no orphaned nodes)
- Cycle detection (no circular dependencies)
- Policy node configuration (required fields)
- Edge connections (valid policy-to-aggregate flows)

## API Integration

Policies are saved and evaluated through the IAM Agent tenant policy APIs:

```
GET  /api/iam-portal/policies/{id}
PUT  /api/iam-portal/policies/{id}
POST /api/iam-portal/policies
POST /api/iam-portal/policies/evaluate
```

## File Structure

```
components/policy-builder/
├── PolicyBuilderCanvas.tsx    # Main canvas component
├── NodePalette.tsx             # Draggable node palette
├── PropertiesPanel.tsx         # Node configuration panel
├── PolicyTemplates.tsx         # Template gallery
└── nodes/                      # Individual node components
    ├── RolePolicyNode.tsx
    ├── TimePolicyNode.tsx
    ├── IPPolicyNode.tsx
    ├── GroupPolicyNode.tsx
    ├── ClientPolicyNode.tsx
    ├── UserPolicyNode.tsx
    ├── JavaScriptPolicyNode.tsx
    └── AggregateNode.tsx
```
