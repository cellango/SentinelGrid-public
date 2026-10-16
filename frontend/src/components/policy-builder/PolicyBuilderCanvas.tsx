/**
 * Policy Builder Canvas Component
 * Main React Flow canvas for policy builder
 */

'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  Connection,
  addEdge,
  useNodesState,
  useEdgesState,
  NodeTypes,
  ReactFlowProvider,
  ReactFlowInstance,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { NodePalette } from './NodePalette';
import { PropertiesPanel } from './PropertiesPanel';
import { GraphStateManager } from '@/lib/policy/graph-state';
import { validateEdge, validateGraph } from '@/lib/policy/edge-validation';
import { graphToKeycloakJSON, exportPolicyAsJSON, validateKeycloakPolicy } from '@/lib/policy/graph-to-json';
import { keycloakJSONToGraph, parseKeycloakPolicyJSON } from '@/lib/policy/json-to-graph';
import { PolicyTemplate } from '@/lib/policy/templates';
import { PolicyTemplates } from './PolicyTemplates';
import { toast } from 'react-hot-toast';
import { RolePolicyNode } from './nodes/RolePolicyNode';
import { TimePolicyNode } from './nodes/TimePolicyNode';
import { IPPolicyNode } from './nodes/IPPolicyNode';
import { GroupPolicyNode } from './nodes/GroupPolicyNode';
import { ClientPolicyNode } from './nodes/ClientPolicyNode';
import { UserPolicyNode } from './nodes/UserPolicyNode';
import { JavaScriptPolicyNode } from './nodes/JavaScriptPolicyNode';
import { AggregateNode } from './nodes/AggregateNode';
import { NodePaletteItem } from '@/lib/policy/types';

interface PolicyBuilderCanvasProps {
  onSave?: (nodes: Node[], edges: Edge[]) => Promise<void> | void;
  onTest?: (nodes: Node[], edges: Edge[]) => Promise<void> | void;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  readonly?: boolean;
  roles?: Array<{ id: string; name: string }>; // For role policy configuration
}

// Node types for React Flow
const nodeTypes: NodeTypes = {
  rolePolicy: RolePolicyNode,
  timePolicy: TimePolicyNode,
  ipPolicy: IPPolicyNode,
  groupPolicy: GroupPolicyNode,
  clientPolicy: ClientPolicyNode,
  userPolicy: UserPolicyNode,
  jsPolicy: JavaScriptPolicyNode,
  aggregateNode: AggregateNode,
};

export function PolicyBuilderCanvas({
  onSave,
  onTest,
  initialNodes,
  initialEdges,
  readonly = false,
  roles = [],
}: PolicyBuilderCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges || []);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [validationStatus, setValidationStatus] = useState<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  } | null>(null);
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const stateManagerRef = useRef<GraphStateManager | null>(null);

  // Initialize state manager
  if (!stateManagerRef.current) {
    stateManagerRef.current = new GraphStateManager(initialNodes || [], initialEdges || []);
  }

  // Fit view whenever we have a graph and a live instance
  useEffect(() => {
    if (reactFlowInstance && nodes.length > 0) {
      requestAnimationFrame(() => reactFlowInstance.fitView({ padding: 0.2 }));
    }
  }, [reactFlowInstance, nodes.length]);


  const onConnect = useCallback(
    (params: Connection) => {
      if (readonly) {
        return;
      }
      // Validate connection before adding
      const sourceNode = nodes.find((n) => n.id === params.source);
      const targetNode = nodes.find((n) => n.id === params.target);

      if (!sourceNode || !targetNode) {
        return;
      }

      const validation = validateEdge(sourceNode, targetNode);
      if (!validation.valid) {
        alert(validation.error || 'Invalid connection');
        return;
      }

      setEdges((eds) => {
        const newEdges = addEdge({ ...params, type: 'smoothstep', animated: false }, eds);
        
        // Update state history
        if (stateManagerRef.current) {
          stateManagerRef.current.pushState({ nodes, edges: newEdges });
        }

        // Validate graph
        const graphValidation = validateGraph(nodes, newEdges);
        setValidationStatus(graphValidation);
        setValidationMessages({
          errors: graphValidation.errors,
          warnings: graphValidation.warnings,
        });

        return newEdges;
      });
    },
    [nodes, readonly, setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (readonly) return;
      if (!reactFlowInstance || !reactFlowWrapper.current) return;

      const nodeTypeData = event.dataTransfer.getData('application/reactflow');
      if (!nodeTypeData) return;

      const nodeType: NodePaletteItem = JSON.parse(nodeTypeData);

      // Get mouse position relative to React Flow viewport
      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      // Create new node based on type
      let nodeTypeId: string;
      let defaultData: any = {
        label: nodeType.label,
        description: nodeType.description,
        type: nodeType.type,
        logic: 'POSITIVE',
      };

      if (nodeType.type === 'aggregate') {
        nodeTypeId = 'aggregateNode';
        defaultData = {
          ...defaultData,
          gateType: nodeType.gateType,
          decisionStrategy: nodeType.gateType === 'AND' ? 'UNANIMOUS' : undefined,
          policies: [],
        };
      } else if (nodeType.type === 'role') {
        nodeTypeId = 'rolePolicy';
        defaultData = {
          ...defaultData,
          roles: [],
        };
      } else if (nodeType.type === 'time') {
        nodeTypeId = 'timePolicy';
        defaultData = {
          ...defaultData,
          daysOfWeek: [1, 2, 3, 4, 5], // Weekdays by default
          hour: 9,
          minute: 0,
          hourEnd: 17,
          minuteEnd: 0,
          timezone: 'UTC',
        };
      } else if (nodeType.type === 'ip') {
        nodeTypeId = 'ipPolicy';
        defaultData = {
          ...defaultData,
          ipAddresses: [],
        };
      } else if (nodeType.type === 'group') {
        nodeTypeId = 'groupPolicy';
        defaultData = {
          ...defaultData,
          groups: [],
        };
      } else if (nodeType.type === 'client') {
        nodeTypeId = 'clientPolicy';
        defaultData = {
          ...defaultData,
          clients: [],
        };
      } else if (nodeType.type === 'user') {
        nodeTypeId = 'userPolicy';
        defaultData = {
          ...defaultData,
          users: [],
        };
      } else if (nodeType.type === 'js') {
        nodeTypeId = 'jsPolicy';
        defaultData = {
          ...defaultData,
          code: '',
        };
      } else {
        nodeTypeId = 'rolePolicy'; // Fallback
      }

      const newNode: Node = {
        id: `${nodeType.type}-${Date.now()}`,
        type: nodeTypeId,
        position,
        data: defaultData,
        style: {
          borderColor: nodeType.color,
        },
      };

      setNodes((nds) => {
        const newNodes = nds.concat(newNode);
        
        // Update state history
        if (stateManagerRef.current) {
          stateManagerRef.current.pushState({ nodes: newNodes, edges });
        }

        // Validate graph
        const graphValidation = validateGraph(newNodes, edges);
        setValidationStatus(graphValidation);
        setValidationMessages({
          errors: graphValidation.errors,
          warnings: graphValidation.warnings,
        });

        return newNodes;
      });
    },
    [reactFlowInstance, readonly, setNodes, edges]
  );

  const [isSaving, setIsSaving] = useState(false);
  const [hasFitView, setHasFitView] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);

  const handleSave = useCallback(async () => {
    try {
      if (readonly) {
        toast.error('Read-only preview: clone the policy first to edit or save it.');
        return;
      }
      if (!onSave) {
        toast.error('This builder surface does not have a live save handler configured.');
        return;
      }
      setIsSaving(true);
      
      // Convert graph to Keycloak policy JSON
      const policy = graphToKeycloakJSON(nodes, edges, 'My Policy');
      
      // Validate the policy
      const validation = validateKeycloakPolicy(policy);
      if (!validation.valid) {
        toast.error(`Policy validation failed:\n${validation.errors.join('\n')}`);
        setIsSaving(false);
        return;
      }

      await onSave(nodes, edges);
      setLastSavedAt(new Date());
      toast.success('Policy saved');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Save failed');
    } finally {
      setIsSaving(false);
    }
  }, [nodes, edges, onSave, readonly]);

  const [showTemplates, setShowTemplates] = useState(false);
  const [validationMessages, setValidationMessages] = useState<{
    errors: string[];
    warnings: string[];
  }>({ errors: [], warnings: [] });

  // Sync canvas when parent provides a new graph (template import / existing policy)
  useEffect(() => {
    const hasGraph = Array.isArray(initialNodes) || Array.isArray(initialEdges);
    if (!hasGraph) return;

    const safeNodes = initialNodes || [];
    const safeEdges = initialEdges || [];

    setNodes(safeNodes);
    setEdges(safeEdges);

    if (stateManagerRef.current) {
      stateManagerRef.current.clear();
      stateManagerRef.current.pushState({ nodes: safeNodes, edges: safeEdges });
    } else {
      stateManagerRef.current = new GraphStateManager(safeNodes, safeEdges);
    }

    const graphValidation = validateGraph(safeNodes, safeEdges);
    setValidationStatus(graphValidation);
    setValidationMessages({
      errors: graphValidation.errors,
      warnings: graphValidation.warnings,
    });

    // Fit viewport to imported graph so nodes are visible after a preview/clone load
    if (reactFlowInstance && safeNodes.length > 0 && !hasFitView) {
      reactFlowInstance.fitView({ padding: 0.2, duration: 400 });
      setHasFitView(true);
    }
  }, [initialNodes, initialEdges, setNodes, setEdges, reactFlowInstance, hasFitView]);

  const handleTest = useCallback(async () => {
    if (!onTest) {
      toast.error('Policy evaluation is only available from the tenant policy builder page.');
      return;
    }
    try {
      await onTest(nodes, edges);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Policy evaluation failed');
    }
  }, [edges, nodes, onTest]);

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const handlePaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleUpdateNode = useCallback(
    (nodeId: string, data: any) => {
      if (readonly) {
        toast.error('Read-only preview: node editing is disabled.');
        return;
      }
      setNodes((nds) => {
        const newNodes = nds.map((node) => (node.id === nodeId ? { ...node, data } : node));
        
        // Update state history
        if (stateManagerRef.current) {
          stateManagerRef.current.pushState({ nodes: newNodes, edges });
        }

        return newNodes;
      });
      // Update selected node if it's the one being updated
      if (selectedNode?.id === nodeId) {
        setSelectedNode({ ...selectedNode, data });
      }
    },
    [setNodes, selectedNode, edges, readonly]
  );

  const handleUndo = useCallback(() => {
    if (stateManagerRef.current?.canUndo()) {
      const previousState = stateManagerRef.current.undo();
      if (previousState) {
        setNodes(previousState.nodes);
        setEdges(previousState.edges);
        const graphValidation = validateGraph(previousState.nodes, previousState.edges);
        setValidationStatus(graphValidation);
        setValidationMessages({
          errors: graphValidation.errors,
          warnings: graphValidation.warnings,
        });
      }
    }
  }, [setNodes, setEdges]);

  const handleRedo = useCallback(() => {
    if (stateManagerRef.current?.canRedo()) {
      const nextState = stateManagerRef.current.redo();
      if (nextState) {
        setNodes(nextState.nodes);
        setEdges(nextState.edges);
        const graphValidation = validateGraph(nextState.nodes, nextState.edges);
        setValidationStatus(graphValidation);
        setValidationMessages({
          errors: graphValidation.errors,
          warnings: graphValidation.warnings,
        });
      }
    }
  }, [setNodes, setEdges]);

  return (
    <div className="flex h-screen">
      {/* Node Palette */}
      <NodePalette readonly={readonly} />

      {/* Canvas Area */}
      <div className="flex-1 flex flex-col relative">
        {/* Toolbar */}
        <div className="bg-surface-card border-b border-surface-card-border px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-text-main">Policy Builder</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleUndo}
              disabled={readonly || !stateManagerRef.current?.canUndo()}
              className="px-3 py-1.5 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed"
              title="Undo (Ctrl+Z)"
            >
              ↶ Undo
            </button>
            <button
              onClick={handleRedo}
              disabled={readonly || !stateManagerRef.current?.canRedo()}
              className="px-3 py-1.5 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed"
              title="Redo (Ctrl+Y)"
            >
              ↷ Redo
            </button>
            <div className="w-px h-6 bg-border-muted"></div>
            <button
              onClick={() => {
                try {
                  const policy = graphToKeycloakJSON(nodes, edges);
                  const jsonString = exportPolicyAsJSON(policy, true);
                  // Copy to clipboard
                  navigator.clipboard.writeText(jsonString);
                  alert('Policy JSON copied to clipboard!');
                } catch (error) {
                  alert(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
                }
              }}
              className="px-3 py-1.5 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
              title="Export as JSON"
            >
              Export JSON
            </button>
            <button
              onClick={() => setShowTemplates(true)}
              disabled={readonly}
              className="px-3 py-1.5 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed"
              title="Load Template"
            >
              📋 Templates
            </button>
            <button
              onClick={() => {
                if (readonly) {
                  toast.error('Read-only preview: import is disabled.');
                  return;
                }
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = '.json';
                input.onchange = (e) => {
                  const file = (e.target as HTMLInputElement).files?.[0];
                  if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                      try {
                        const jsonString = event.target?.result as string;
                        const policy = parseKeycloakPolicyJSON(jsonString);
                        const graph = keycloakJSONToGraph(policy);
                        setNodes(graph.nodes);
                        setEdges(graph.edges);
                        if (stateManagerRef.current) {
                          stateManagerRef.current.clear();
                          stateManagerRef.current.pushState(graph);
                        }
                        const graphValidation = validateGraph(graph.nodes, graph.edges);
                        setValidationStatus(graphValidation);
                        setValidationMessages({
                          errors: graphValidation.errors,
                          warnings: graphValidation.warnings,
                        });
                        toast.success('Policy imported successfully!');
                      } catch (error) {
                        toast.error(`Import failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
                      }
                    };
                    reader.readAsText(file);
                  }
                };
                input.click();
              }}
              className="px-3 py-1.5 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
              title="Import from JSON"
            >
              Import JSON
            </button>
            <button
              onClick={handleTest}
              className="px-3 py-1.5 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
            >
              Open Policy Test
            </button>
            <button
              onClick={handleSave}
              disabled={readonly || isSaving}
              className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {readonly ? 'Preview Only' : isSaving ? 'Saving Policy...' : 'Save Tenant Policy'}
            </button>
          </div>
        </div>

        {/* React Flow Canvas */}
        <div ref={reactFlowWrapper} className="flex-1 min-h-[720px]">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={readonly ? undefined : onNodesChange}
            onEdgesChange={readonly ? undefined : onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={handleNodeClick}
            onPaneClick={handlePaneClick}
            nodeTypes={nodeTypes}
            nodesDraggable={!readonly}
            nodesConnectable={!readonly}
            fitView
            className="bg-surface-hover"
          >
            <Background />
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                if (node.type === 'rolePolicy') return '#3B82F6';
                if (node.type === 'timePolicy') return '#F59E0B';
                if (node.type === 'ipPolicy') return '#10B981';
                if (node.type === 'aggregateNode') return '#8B5CF6';
                return '#6B7280';
              }}
              maskColor="rgba(0, 0, 0, 0.1)"
            />
          </ReactFlow>
        </div>

        {/* Properties Panel */}
        <PropertiesPanel
          selectedNode={selectedNode}
          onUpdateNode={handleUpdateNode}
          roles={roles}
          readonly={readonly}
        />

        {/* Templates Modal */}
        {showTemplates && (
          <PolicyTemplates
            onSelectTemplate={(template: PolicyTemplate) => {
              // Generate unique IDs for template nodes
              const nodeIdMap = new Map<string, string>();
              const newNodes = template.nodes.map((node) => {
                const newId = `${node.type}-${Date.now()}-${Math.random()}`;
                nodeIdMap.set(node.id, newId);
                return {
                  ...node,
                  id: newId,
                };
              });

              const newEdges = template.edges.map((edge) => ({
                ...edge,
                id: `edge-${Date.now()}-${Math.random()}`,
                source: nodeIdMap.get(edge.source) || edge.source,
                target: nodeIdMap.get(edge.target) || edge.target,
              }));

              setNodes((nds) => [...nds, ...newNodes]);
              setEdges((eds) => [...eds, ...newEdges]);
              
              if (stateManagerRef.current) {
                stateManagerRef.current.pushState({
                  nodes: [...nodes, ...newNodes],
                  edges: [...edges, ...newEdges],
                });
              }

              const graphValidation = validateGraph([...nodes, ...newNodes], [...edges, ...newEdges]);
              setValidationStatus(graphValidation);
              setValidationMessages({
                errors: graphValidation.errors,
                warnings: graphValidation.warnings,
              });

              toast.success(`Template "${template.name}" loaded!`);
            }}
            onClose={() => setShowTemplates(false)}
          />
        )}

        {/* Status Bar */}
        <div className="bg-surface-hover border-t border-surface-card-border px-4 py-2">
          <div className="flex items-center justify-between text-xs text-text-muted mb-1">
            <div className="flex items-center gap-4">
              {validationStatus ? (
                <>
                  {validationStatus.valid ? (
                    <span className="text-green-600">✅ Valid</span>
                  ) : (
                    <span className="text-red-600">
                      ❌ {validationStatus.errors.length} error{validationStatus.errors.length !== 1 ? 's' : ''}
                    </span>
                  )}
                  {validationStatus.warnings.length > 0 && (
                    <span className="text-yellow-600">
                      ⚠️ {validationStatus.warnings.length} warning{validationStatus.warnings.length !== 1 ? 's' : ''}
                    </span>
                  )}
                </>
              ) : (
                <span>✅ Valid</span>
              )}
              <span>Nodes: {nodes.length}</span>
              <span>Connections: {edges.length}</span>
            </div>
            <div>Last saved: {lastSavedAt ? lastSavedAt.toLocaleTimeString() : 'Not yet in this session'}</div>
          </div>

          {/* Validation Messages */}
          {(validationMessages.errors.length > 0 || validationMessages.warnings.length > 0) && (
            <div className="mt-2 space-y-1">
              {validationMessages.errors.map((error, index) => (
                <div key={`error-${index}`} className="text-xs text-red-600">
                  ❌ {error}
                </div>
              ))}
              {validationMessages.warnings.map((warning, index) => (
                <div key={`warning-${index}`} className="text-xs text-yellow-600">
                  ⚠️ {warning}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Wrapper with ReactFlowProvider
export function PolicyBuilderCanvasWrapper(props: PolicyBuilderCanvasProps) {
  return (
    <ReactFlowProvider>
      <PolicyBuilderCanvas {...props} />
    </ReactFlowProvider>
  );
}
