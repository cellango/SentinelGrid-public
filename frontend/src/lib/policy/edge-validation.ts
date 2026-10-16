/**
 * Edge Connection Validation
 * Validates connections between policy nodes
 */

import { Node, Edge } from 'reactflow';

export interface ValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validate if an edge connection is allowed
 */
export function validateEdge(sourceNode: Node, targetNode: Node): ValidationResult {
  // Cannot connect a node to itself
  if (sourceNode.id === targetNode.id) {
    return {
      valid: false,
      error: 'Cannot connect a node to itself',
    };
  }

  // Aggregate nodes can connect to other aggregate nodes or be terminal nodes
  if (sourceNode.type === 'aggregateNode') {
    if (targetNode.type === 'aggregateNode') {
      // AND/OR gates can connect to other gates
      return { valid: true };
    }
    // Aggregate nodes can connect to policy nodes
    return { valid: true };
  }

  // Policy nodes can connect to aggregate nodes
  if (targetNode.type === 'aggregateNode') {
    return { valid: true };
  }

  // Policy nodes should not connect directly to other policy nodes
  // They should go through aggregate nodes
  if (sourceNode.type !== 'aggregateNode' && targetNode.type !== 'aggregateNode') {
    return {
      valid: false,
      error: 'Policy nodes must connect through aggregate nodes (AND/OR/NOT)',
    };
  }

  return { valid: true };
}

/**
 * Validate the entire graph structure
 */
export function validateGraph(nodes: Node[], edges: Edge[]): {
  valid: boolean;
  errors: string[];
  warnings: string[];
} {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check for orphaned nodes (nodes with no connections)
  const connectedNodeIds = new Set<string>();
  edges.forEach((edge) => {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  });

  nodes.forEach((node) => {
    if (!connectedNodeIds.has(node.id) && nodes.length > 1) {
      warnings.push(`Node "${node.data.label || node.id}" is not connected to any other node`);
    }
  });

  // Check for cycles (basic check)
  const hasCycle = detectCycle(nodes, edges);
  if (hasCycle) {
    errors.push('Circular dependencies detected in policy graph');
  }

  // Check for multiple root nodes (nodes with no incoming edges)
  const nodesWithIncoming = new Set(edges.map((e) => e.target));
  const rootNodes = nodes.filter((node) => !nodesWithIncoming.has(node.id));
  if (rootNodes.length > 1) {
    warnings.push(
      `Multiple root nodes detected. Consider using an aggregate node to combine them.`
    );
  }

  // Check for leaf nodes (nodes with no outgoing edges)
  const nodesWithOutgoing = new Set(edges.map((e) => e.source));
  const leafNodes = nodes.filter((node) => !nodesWithOutgoing.has(node.id));
  if (leafNodes.length === 0 && nodes.length > 0) {
    warnings.push('No terminal node found. Policy needs a result node.');
  }

  // Validate each edge
  edges.forEach((edge) => {
    const sourceNode = nodes.find((n) => n.id === edge.source);
    const targetNode = nodes.find((n) => n.id === edge.target);

    if (!sourceNode || !targetNode) {
      errors.push(`Invalid edge: node not found`);
      return;
    }

    const validation = validateEdge(sourceNode, targetNode);
    if (!validation.valid) {
      errors.push(validation.error || 'Invalid edge connection');
    }
  });

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

/**
 * Detect cycles in the graph using DFS
 */
function detectCycle(nodes: Node[], edges: Edge[]): boolean {
  const visited = new Set<string>();
  const recursionStack = new Set<string>();
  const adjacencyList = new Map<string, string[]>();

  // Build adjacency list
  nodes.forEach((node) => {
    adjacencyList.set(node.id, []);
  });

  edges.forEach((edge) => {
    const neighbors = adjacencyList.get(edge.source) || [];
    neighbors.push(edge.target);
    adjacencyList.set(edge.source, neighbors);
  });

  const hasCycleDFS = (nodeId: string): boolean => {
    visited.add(nodeId);
    recursionStack.add(nodeId);

    const neighbors = adjacencyList.get(nodeId) || [];
    for (const neighborId of neighbors) {
      if (!visited.has(neighborId)) {
        if (hasCycleDFS(neighborId)) {
          return true;
        }
      } else if (recursionStack.has(neighborId)) {
        return true;
      }
    }

    recursionStack.delete(nodeId);
    return false;
  };

  for (const node of nodes) {
    if (!visited.has(node.id)) {
      if (hasCycleDFS(node.id)) {
        return true;
      }
    }
  }

  return false;
}

