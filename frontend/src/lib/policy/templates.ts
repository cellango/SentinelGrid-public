/**
 * Policy Templates
 * Pre-built policy templates for common scenarios
 */

import { Node, Edge } from 'reactflow';

export interface PolicyTemplate {
  id: string;
  name: string;
  description: string;
  category: 'security' | 'access' | 'time' | 'location' | 'compliance';
  nodes: Node[];
  edges: Edge[];
  tags: string[];
}

/**
 * Pre-built policy templates
 */
export const policyTemplates: PolicyTemplate[] = [
  {
    id: 'soc-manager-business-hours',
    name: 'SOC Manager - Business Hours Only',
    description: 'Allow SOC managers access only during business hours (9 AM - 5 PM, Weekdays)',
    category: 'access',
    nodes: [
      {
        id: 'role-1',
        type: 'rolePolicy',
        position: { x: 250, y: 100 },
        data: {
          label: 'SOC Manager Role',
          type: 'role',
          logic: 'POSITIVE',
          roles: [{ id: 'SOC_MANAGER', name: 'SOC_MANAGER', required: true }],
        },
      },
      {
        id: 'time-1',
        type: 'timePolicy',
        position: { x: 250, y: 250 },
        data: {
          label: 'Business Hours',
          type: 'time',
          logic: 'POSITIVE',
          daysOfWeek: [1, 2, 3, 4, 5], // Mon-Fri
          hour: 9,
          minute: 0,
          hourEnd: 17,
          minuteEnd: 0,
          timezone: 'UTC',
        },
      },
      {
        id: 'aggregate-1',
        type: 'aggregateNode',
        position: { x: 250, y: 400 },
        data: {
          label: 'AND Gate',
          type: 'aggregate',
          gateType: 'AND',
          decisionStrategy: 'UNANIMOUS',
          logic: 'POSITIVE',
          policies: [],
        },
      },
    ],
    edges: [
      {
        id: 'e1-1',
        source: 'role-1',
        target: 'aggregate-1',
        type: 'smoothstep',
      },
      {
        id: 'e1-2',
        source: 'time-1',
        target: 'aggregate-1',
        type: 'smoothstep',
      },
    ],
    tags: ['SOC', 'time-based', 'business-hours'],
  },
  {
    id: 'office-ip-only',
    name: 'Office IP Address Restriction',
    description: 'Restrict access to office IP address range (10.0.0.0/8)',
    category: 'location',
    nodes: [
      {
        id: 'ip-1',
        type: 'ipPolicy',
        position: { x: 250, y: 200 },
        data: {
          label: 'Office IP Range',
          type: 'ip',
          logic: 'POSITIVE',
          ipAddresses: ['10.0.0.0/8'],
        },
      },
    ],
    edges: [],
    tags: ['IP', 'network', 'office'],
  },
  {
    id: 'admin-or-specific-users',
    name: 'Admin Role OR Specific Users',
    description: 'Allow access to admin role OR specific listed users',
    category: 'access',
    nodes: [
      {
        id: 'role-1',
        type: 'rolePolicy',
        position: { x: 150, y: 200 },
        data: {
          label: 'Admin Role',
          type: 'role',
          logic: 'POSITIVE',
          roles: [{ id: 'ADMIN', name: 'ADMIN', required: true }],
        },
      },
      {
        id: 'user-1',
        type: 'userPolicy',
        position: { x: 350, y: 200 },
        data: {
          label: 'Specific Users',
          type: 'user',
          logic: 'POSITIVE',
          users: [],
        },
      },
      {
        id: 'aggregate-1',
        type: 'aggregateNode',
        position: { x: 250, y: 350 },
        data: {
          label: 'OR Gate',
          type: 'aggregate',
          gateType: 'OR',
          decisionStrategy: 'AFFIRMATIVE',
          logic: 'POSITIVE',
          policies: [],
        },
      },
    ],
    edges: [
      {
        id: 'e1-1',
        source: 'role-1',
        target: 'aggregate-1',
        type: 'smoothstep',
      },
      {
        id: 'e1-2',
        source: 'user-1',
        target: 'aggregate-1',
        type: 'smoothstep',
      },
    ],
    tags: ['admin', 'users', 'flexible'],
  },
  {
    id: 'time-restricted-contractors',
    name: 'Contractor Time Restrictions',
    description: 'Restrict contractor access to business hours and specific days',
    category: 'time',
    nodes: [
      {
        id: 'role-1',
        type: 'rolePolicy',
        position: { x: 150, y: 100 },
        data: {
          label: 'Contractor Role',
          type: 'role',
          logic: 'POSITIVE',
          roles: [{ id: 'CONTRACTOR', name: 'CONTRACTOR', required: true }],
        },
      },
      {
        id: 'time-1',
        type: 'timePolicy',
        position: { x: 350, y: 100 },
        data: {
          label: 'Business Hours',
          type: 'time',
          logic: 'POSITIVE',
          daysOfWeek: [1, 2, 3, 4, 5], // Mon-Fri
          hour: 9,
          minute: 0,
          hourEnd: 17,
          minuteEnd: 0,
          timezone: 'UTC',
        },
      },
      {
        id: 'aggregate-1',
        type: 'aggregateNode',
        position: { x: 250, y: 250 },
        data: {
          label: 'AND Gate',
          type: 'aggregate',
          gateType: 'AND',
          decisionStrategy: 'UNANIMOUS',
          logic: 'POSITIVE',
          policies: [],
        },
      },
    ],
    edges: [
      {
        id: 'e1-1',
        source: 'role-1',
        target: 'aggregate-1',
        type: 'smoothstep',
      },
      {
        id: 'e1-2',
        source: 'time-1',
        target: 'aggregate-1',
        type: 'smoothstep',
      },
    ],
    tags: ['contractor', 'time-based', 'restriction'],
  },
  {
    id: 'deny-outside-office-ip',
    name: 'Deny Access Outside Office IP',
    description: 'Explicitly deny access for IPs outside the office network',
    category: 'security',
    nodes: [
      {
        id: 'ip-1',
        type: 'ipPolicy',
        position: { x: 250, y: 200 },
        data: {
          label: 'Outside Office IP',
          type: 'ip',
          logic: 'NEGATIVE', // Deny logic
          ipAddresses: ['10.0.0.0/8'], // Everything except office network
        },
      },
    ],
    edges: [],
    tags: ['security', 'IP', 'deny', 'network'],
  },
  {
    id: 'weekend-access',
    name: 'Weekend Access Restriction',
    description: 'Deny access on weekends (Saturday and Sunday)',
    category: 'time',
    nodes: [
      {
        id: 'time-1',
        type: 'timePolicy',
        position: { x: 250, y: 200 },
        data: {
          label: 'Weekends',
          type: 'time',
          logic: 'NEGATIVE', // Deny on weekends
          daysOfWeek: [0, 6], // Sunday and Saturday
          hour: 0,
          minute: 0,
          hourEnd: 23,
          minuteEnd: 59,
          timezone: 'UTC',
        },
      },
    ],
    edges: [],
    tags: ['weekend', 'time-based', 'restriction'],
  },
];

/**
 * Get templates by category
 */
export function getTemplatesByCategory(category: PolicyTemplate['category']): PolicyTemplate[] {
  return policyTemplates.filter((template) => template.category === category);
}

/**
 * Search templates by name, description, or tags
 */
export function searchTemplates(query: string): PolicyTemplate[] {
  const lowerQuery = query.toLowerCase();
  return policyTemplates.filter(
    (template) =>
      template.name.toLowerCase().includes(lowerQuery) ||
      template.description.toLowerCase().includes(lowerQuery) ||
      template.tags.some((tag) => tag.toLowerCase().includes(lowerQuery))
  );
}

/**
 * Get template by ID
 */
export function getTemplateById(id: string): PolicyTemplate | undefined {
  return policyTemplates.find((template) => template.id === id);
}

