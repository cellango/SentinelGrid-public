/**
 * Graph to JSON Converter
 * Converts React Flow graph to Keycloak-compatible policy JSON
 */

import { Node, Edge } from 'reactflow';
import {
  KeycloakPolicy,
  PolicyType,
  PolicyLogic,
  DecisionStrategy,
  AggregateGateType,
} from './types';
// Simple UUID generator (avoiding external dependency for now)
function uuidv4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

interface ConversionContext {
  nodeMap: Map<string, KeycloakPolicy>;
  edgeMap: Map<string, Edge[]>;
  visited: Set<string>;
}

/**
 * Convert graph (nodes + edges) to Keycloak policy JSON
 */
export function graphToKeycloakJSON(
  nodes: Node[],
  edges: Edge[],
  policyName: string = 'Generated Policy'
): KeycloakPolicy {
  if (nodes.length === 0) {
    throw new Error('Policy graph must contain at least one node');
  }

  // Build maps for efficient lookup
  const context: ConversionContext = {
    nodeMap: new Map(),
    edgeMap: new Map(),
    visited: new Set(),
  };

  // Group edges by source node
  edges.forEach((edge) => {
    const sourceEdges = context.edgeMap.get(edge.source) || [];
    sourceEdges.push(edge);
    context.edgeMap.set(edge.source, sourceEdges);
  });

  // Find root node (node with no incoming edges)
  const nodesWithIncoming = new Set(edges.map((e) => e.target));
  const rootNodes = nodes.filter((node) => !nodesWithIncoming.has(node.id));

  if (rootNodes.length === 0) {
    // No root found, use first node
    const firstNode = nodes[0];
    return convertNodeToPolicy(firstNode, nodes, edges, context);
  }

  if (rootNodes.length === 1) {
    // Single root - convert it
    const rootNode = rootNodes[0];
    return convertNodeToPolicy(rootNode, nodes, edges, context);
  }

  // Multiple roots - create an aggregate policy
  const rootPolicyIds = rootNodes.map((node) => {
    const policy = convertNodeToPolicy(node, nodes, edges, context);
    context.nodeMap.set(node.id, policy);
    return { id: policy.id! };
  });

  return {
    id: uuidv4(),
    name: policyName,
    type: 'aggregate',
    logic: 'POSITIVE',
    decisionStrategy: 'AFFIRMATIVE',
    policies: rootPolicyIds,
  };
}

/**
 * Convert a single node to Keycloak policy
 */
function convertNodeToPolicy(
  node: Node,
  allNodes: Node[],
  allEdges: Edge[],
  context: ConversionContext
): KeycloakPolicy {
  // Avoid infinite loops
  if (context.visited.has(node.id)) {
    // Return reference to already converted policy
    const existing = context.nodeMap.get(node.id);
    if (existing) {
      return existing;
    }
  }

  context.visited.add(node.id);

  const nodeData = node.data;
  const policyId = uuidv4();
  let policy: KeycloakPolicy;

  // Convert based on node type
  switch (nodeData.type) {
    case 'role':
      policy = convertRolePolicy(node, policyId);
      break;
    case 'time':
      policy = convertTimePolicy(node, policyId);
      break;
    case 'ip':
      policy = convertIPPolicy(node, policyId);
      break;
    case 'group':
      policy = convertGroupPolicy(node, policyId);
      break;
    case 'client':
      policy = convertClientPolicy(node, policyId);
      break;
    case 'user':
      policy = convertUserPolicy(node, policyId);
      break;
    case 'js':
      policy = convertJavaScriptPolicy(node, policyId);
      break;
    case 'aggregate':
      policy = convertAggregatePolicy(node, allNodes, allEdges, context, policyId);
      break;
    default:
      throw new Error(`Unknown policy type: ${nodeData.type}`);
  }

  context.nodeMap.set(node.id, policy);
  return policy;
}

/**
 * Convert Role Policy node
 */
function convertRolePolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;
  const roles = (data.roles || []).map((role: any) => ({
    id: role.id,
    required: role.required !== false, // Default to true if not specified
  }));

  return {
    id: policyId,
    name: data.label || 'Role Policy',
    type: 'role',
    logic: data.logic || 'POSITIVE',
    decisionStrategy: roles.every((r: any) => r.required) ? 'UNANIMOUS' : 'AFFIRMATIVE',
    roles,
  };
}

/**
 * Convert Time Policy node
 */
function convertTimePolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;

  return {
    id: policyId,
    name: data.label || 'Time Policy',
    type: 'time',
    logic: data.logic || 'POSITIVE',
    dayMonth: data.dayMonth || '*',
    dayMonthEnd: data.dayMonthEnd || '*',
    hour: String(data.hour || 0).padStart(2, '0'),
    minute: String(data.minute || 0).padStart(2, '0'),
    hourEnd: String(data.hourEnd || 23).padStart(2, '0'),
    minuteEnd: String(data.minuteEnd || 59).padStart(2, '0'),
    notBefore: data.notBefore || undefined,
    notOnOrAfter: data.notOnOrAfter || undefined,
  };
}

/**
 * Convert IP Policy node
 */
function convertIPPolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;
  const ipAddresses = data.ipAddresses || [];

  // Keycloak IP policy supports single IP address
  // For multiple IPs, we'd need to create multiple policies and aggregate them
  if (ipAddresses.length === 0) {
    throw new Error('IP Policy must have at least one IP address');
  }

  // Use first IP for single policy
  // For multiple IPs, this should be handled by creating an aggregate
  const ipAddress = ipAddresses[0];

  return {
    id: policyId,
    name: data.label || 'IP Policy',
    type: 'ip',
    logic: data.logic || 'POSITIVE',
    ipAddress,
  };
}

/**
 * Convert Group Policy node
 */
function convertGroupPolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;
  const groups = (data.groups || []).map((group: any) => ({
    id: typeof group === 'string' ? group : group.id,
    extendChildren: group.extendChildren || false,
  }));

  return {
    id: policyId,
    name: data.label || 'Group Policy',
    type: 'group',
    logic: data.logic || 'POSITIVE',
    groups,
  };
}

/**
 * Convert Client Policy node
 */
function convertClientPolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;
  const clients = data.clients || [];

  return {
    id: policyId,
    name: data.label || 'Client Policy',
    type: 'client',
    logic: data.logic || 'POSITIVE',
    clients,
  };
}

/**
 * Convert User Policy node
 */
function convertUserPolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;
  const users = data.users || [];

  return {
    id: policyId,
    name: data.label || 'User Policy',
    type: 'user',
    logic: data.logic || 'POSITIVE',
    users,
  };
}

/**
 * Convert JavaScript Policy node
 */
function convertJavaScriptPolicy(node: Node, policyId: string): KeycloakPolicy {
  const data = node.data;

  if (!data.code || data.code.trim() === '') {
    throw new Error('JavaScript Policy must have code defined');
  }

  return {
    id: policyId,
    name: data.label || 'JavaScript Policy',
    type: 'js',
    logic: data.logic || 'POSITIVE',
    code: data.code,
  };
}

/**
 * Convert Aggregate Policy node
 */
function convertAggregatePolicy(
  node: Node,
  allNodes: Node[],
  allEdges: Edge[],
  context: ConversionContext,
  policyId: string
): KeycloakPolicy {
  const data = node.data;
  const gateType: AggregateGateType = data.gateType || 'AND';

  // Find child policies (nodes connected from this aggregate node)
  const childEdges = allEdges.filter((edge) => edge.source === node.id);
  const childNodes = childEdges.map((edge) => {
    const childNode = allNodes.find((n) => n.id === edge.target);
    if (!childNode) {
      throw new Error(`Child node not found for edge: ${edge.target}`);
    }
    return childNode;
  });

  // Convert child nodes to policies
  const childPolicies = childNodes.map((childNode) => {
    const childPolicy = convertNodeToPolicy(childNode, allNodes, allEdges, context);
    return { id: childPolicy.id! };
  });

  // Determine decision strategy based on gate type
  let decisionStrategy: DecisionStrategy = 'UNANIMOUS';
  if (gateType === 'AND') {
    decisionStrategy = (data.decisionStrategy as DecisionStrategy) || 'UNANIMOUS';
  } else if (gateType === 'OR') {
    decisionStrategy = 'AFFIRMATIVE';
  } else if (gateType === 'NOT') {
    // NOT gate is handled via logic (NEGATIVE)
    decisionStrategy = 'UNANIMOUS';
  }

  // For NOT gate, we need to handle it differently
  // NOT is typically handled via NEGATIVE logic on the child policy
  if (gateType === 'NOT' && childPolicies.length === 1) {
    // Apply NOT by using NEGATIVE logic on the child
    const childPolicy = context.nodeMap.get(childNodes[0].id);
    if (childPolicy) {
      childPolicy.logic = 'NEGATIVE';
    }
  }

  return {
    id: policyId,
    name: data.label || `${gateType} Gate`,
    type: 'aggregate',
    logic: gateType === 'NOT' ? 'POSITIVE' : (data.logic || 'POSITIVE'),
    decisionStrategy,
    policies: childPolicies,
  };
}

/**
 * Export policy as JSON string
 */
export function exportPolicyAsJSON(policy: KeycloakPolicy, pretty: boolean = true): string {
  return pretty ? JSON.stringify(policy, null, 2) : JSON.stringify(policy);
}

/**
 * Validate generated policy structure
 */
export function validateKeycloakPolicy(policy: KeycloakPolicy): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Required fields
  if (!policy.name || policy.name.trim() === '') {
    errors.push('Policy name is required');
  }

  if (!policy.type) {
    errors.push('Policy type is required');
  }

  if (!policy.logic) {
    errors.push('Policy logic is required');
  }

  // Type-specific validation
  switch (policy.type) {
    case 'role':
      if (!policy.roles || policy.roles.length === 0) {
        errors.push('Role policy must have at least one role');
      }
      break;
    case 'time':
      if (policy.hour === undefined || policy.minute === undefined) {
        errors.push('Time policy must have hour and minute defined');
      }
      break;
    case 'ip':
      if (!policy.ipAddress) {
        errors.push('IP policy must have an IP address defined');
      }
      break;
    case 'group':
      if (!policy.groups || policy.groups.length === 0) {
        errors.push('Group policy must have at least one group');
      }
      break;
    case 'client':
      if (!policy.clients || policy.clients.length === 0) {
        errors.push('Client policy must have at least one client');
      }
      break;
    case 'user':
      if (!policy.users || policy.users.length === 0) {
        errors.push('User policy must have at least one user');
      }
      break;
    case 'js':
      if (!policy.code || policy.code.trim() === '') {
        errors.push('JavaScript policy must have code defined');
      }
      break;
    case 'aggregate':
      if (!policy.policies || policy.policies.length === 0) {
        errors.push('Aggregate policy must have at least one child policy');
      }
      break;
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

