/**
 * JSON to Graph Converter
 * Converts Keycloak policy JSON to React Flow graph
 */

import { Node, Edge } from 'reactflow';
import { KeycloakPolicy } from './types';
// Simple UUID generator (avoiding external dependency for now)
function uuidv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

interface GraphConversionResult {
  nodes: Node[];
  edges: Edge[];
}

interface NodePosition {
  x: number;
  y: number;
}

/**
 * Convert Keycloak policy JSON to React Flow graph
 */
export function keycloakJSONToGraph(
  policy: KeycloakPolicy,
  startPosition: NodePosition = { x: 250, y: 100 }
): GraphConversionResult {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const nodeIdMap = new Map<string, string>(); // Map Keycloak policy ID to React Flow node ID

  // Calculate layout
  const layout = calculateLayout(policy);

  // Convert policy tree to nodes and edges
  convertPolicyToNodes(policy, nodes, edges, nodeIdMap, layout, startPosition);

  return { nodes, edges };
}

/**
 * Recursively convert policy to nodes
 */
function convertPolicyToNodes(
  policy: KeycloakPolicy,
  nodes: Node[],
  edges: Edge[],
  nodeIdMap: Map<string, string>,
  layout: LayoutTree,
  position: NodePosition,
  parentNodeId?: string
): string {
  const nodeId = uuidv4();
  nodeIdMap.set(policy.id || uuidv4(), nodeId);

  // Determine node type and data
  let nodeType: string;
  let nodeData: any;

  switch (policy.type) {
    case 'role':
      nodeType = 'rolePolicy';
      nodeData = {
        label: policy.name,
        type: 'role',
        logic: policy.logic || 'POSITIVE',
        roles: (policy.roles || []).map((r) => ({
          id: r.id,
          name: r.id, // Fallback to ID if name not available
          required: r.required !== false,
        })),
      };
      break;
    case 'time':
      nodeType = 'timePolicy';
      nodeData = {
        label: policy.name,
        type: 'time',
        logic: policy.logic || 'POSITIVE',
        hour: parseInt(policy.hour || '0'),
        minute: parseInt(policy.minute || '0'),
        hourEnd: parseInt(policy.hourEnd || '23'),
        minuteEnd: parseInt(policy.minuteEnd || '59'),
        dayMonth: policy.dayMonth || '*',
        dayMonthEnd: policy.dayMonthEnd || '*',
        notBefore: policy.notBefore,
        notOnOrAfter: policy.notOnOrAfter,
        timezone: 'UTC', // Default, not in Keycloak policy
        daysOfWeek: [1, 2, 3, 4, 5], // Default weekdays, not in Keycloak policy
      };
      break;
    case 'ip':
      nodeType = 'ipPolicy';
      nodeData = {
        label: policy.name,
        type: 'ip',
        logic: policy.logic || 'POSITIVE',
        ipAddresses: policy.ipAddress ? [policy.ipAddress] : [],
      };
      break;
    case 'group':
      nodeType = 'groupPolicy';
      nodeData = {
        label: policy.name,
        type: 'group',
        logic: policy.logic || 'POSITIVE',
        groups: (policy.groups || []).map((g) => ({
          id: g.id,
          name: g.id, // Fallback to ID
          extendChildren: g.extendChildren || false,
        })),
      };
      break;
    case 'client':
      nodeType = 'clientPolicy';
      nodeData = {
        label: policy.name,
        type: 'client',
        logic: policy.logic || 'POSITIVE',
        clients: policy.clients || [],
      };
      break;
    case 'user':
      nodeType = 'userPolicy';
      nodeData = {
        label: policy.name,
        type: 'user',
        logic: policy.logic || 'POSITIVE',
        users: policy.users || [],
      };
      break;
    case 'js':
      nodeType = 'jsPolicy';
      nodeData = {
        label: policy.name,
        type: 'js',
        logic: policy.logic || 'POSITIVE',
        code: policy.code || '',
      };
      break;
    case 'aggregate':
      nodeType = 'aggregateNode';
      // Determine gate type from decision strategy and child count
      let gateType: 'AND' | 'OR' | 'NOT' = 'AND';
      if (policy.decisionStrategy === 'AFFIRMATIVE' && (policy.policies?.length || 0) > 1) {
        gateType = 'OR';
      } else if ((policy.policies?.length || 0) === 1 && policy.logic === 'NEGATIVE') {
        gateType = 'NOT';
      }
      nodeData = {
        label: policy.name,
        type: 'aggregate',
        gateType,
        decisionStrategy: policy.decisionStrategy || 'UNANIMOUS',
        logic: policy.logic || 'POSITIVE',
        policies: [],
      };
      break;
    default:
      throw new Error(`Unknown policy type: ${policy.type}`);
  }

  // Create node
  const node: Node = {
    id: nodeId,
    type: nodeType,
    position,
    data: nodeData,
  };

  nodes.push(node);

  // Create edge from parent if exists
  if (parentNodeId) {
    edges.push({
      id: `edge-${parentNodeId}-${nodeId}`,
      source: parentNodeId,
      target: nodeId,
      type: 'smoothstep',
    });
  }

  // Handle child policies
  if (policy.type === 'aggregate' && policy.policies) {
    const childLayout = layout.children || [];
    policy.policies.forEach((childPolicyRef, index) => {
      // Note: We need the full child policy object, but Keycloak only provides IDs
      // This is a limitation - we'd need to fetch full policies or have them in context
      // For now, we'll create placeholder nodes that need to be filled
      const childLayoutItem = childLayout[index];
      if (childLayoutItem && childLayoutItem.x !== undefined && childLayoutItem.y !== undefined) {
        const childPosition = {
          x: position.x + childLayoutItem.x,
          y: position.y + childLayoutItem.y,
        };

        // This is a simplified version - in practice, you'd need the full policy object
        // For import, we'd need to fetch all policies first
        const childNodeId = uuidv4();
        nodes.push({
          id: childNodeId,
          type: 'rolePolicy', // Placeholder
          position: childPosition,
          data: {
            label: `Policy ${childPolicyRef.id}`,
            type: 'role',
            logic: 'POSITIVE',
            roles: [],
          },
        });

        edges.push({
          id: `edge-${nodeId}-${childNodeId}`,
          source: nodeId,
          target: childNodeId,
          type: 'smoothstep',
        });
      }
    });
  }

  return nodeId;
}

/**
 * Calculate layout tree for policies
 */
interface LayoutTree {
  width: number;
  height: number;
  x?: number;
  y?: number;
  children?: LayoutTree[];
}

function calculateLayout(policy: KeycloakPolicy): LayoutTree {
  const NODE_WIDTH = 200;
  const NODE_HEIGHT = 100;
  const HORIZONTAL_SPACING = 250;
  const VERTICAL_SPACING = 150;

  if (policy.type !== 'aggregate' || !policy.policies || policy.policies.length === 0) {
    return {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
    };
  }

  const children = policy.policies.map(() => ({
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
  }));

  const totalWidth = Math.max(
    NODE_WIDTH,
    children.length * HORIZONTAL_SPACING
  );

  return {
    width: totalWidth,
    height: NODE_HEIGHT + VERTICAL_SPACING + NODE_HEIGHT,
    children: children.map((_, index) => ({
      ...children[index],
      x: (index - (children.length - 1) / 2) * HORIZONTAL_SPACING,
      y: VERTICAL_SPACING,
    })) as any,
  };
}

/**
 * Parse Keycloak policy JSON string
 */
export function parseKeycloakPolicyJSON(jsonString: string): KeycloakPolicy {
  try {
    const policy = JSON.parse(jsonString);
    return validateAndNormalizePolicy(policy);
  } catch (error) {
    throw new Error(`Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Validate and normalize policy structure
 */
function validateAndNormalizePolicy(policy: any): KeycloakPolicy {
  if (!policy || typeof policy !== 'object') {
    throw new Error('Policy must be an object');
  }

  if (!policy.type) {
    throw new Error('Policy type is required');
  }

  // Ensure required fields have defaults
  return {
    id: policy.id || uuidv4(),
    name: policy.name || 'Unnamed Policy',
    type: policy.type,
    logic: policy.logic || 'POSITIVE',
    decisionStrategy: policy.decisionStrategy,
    roles: policy.roles,
    users: policy.users,
    groups: policy.groups,
    clients: policy.clients,
    ipAddress: policy.ipAddress,
    dayMonth: policy.dayMonth,
    dayMonthEnd: policy.dayMonthEnd,
    hour: policy.hour,
    minute: policy.minute,
    hourEnd: policy.hourEnd,
    minuteEnd: policy.minuteEnd,
    notBefore: policy.notBefore,
    notOnOrAfter: policy.notOnOrAfter,
    code: policy.code,
    policies: policy.policies,
  };
}

