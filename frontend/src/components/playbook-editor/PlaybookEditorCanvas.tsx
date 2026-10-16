/**
 * Playbook Editor Canvas Component
 * Main React Flow canvas for playbook editor
 */

'use client';

import { useCallback, useRef, useState, useEffect } from 'react';
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
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { PlaybookNodePalette } from './PlaybookNodePalette';
import { PlaybookPropertiesPanel } from './PlaybookPropertiesPanel';
import { toast } from 'react-hot-toast';

// Import node types (to be created)
import { TriggerNode } from './nodes/TriggerNode';
import { ActionNode } from './nodes/ActionNode';
import { ObservableNode } from './nodes/ObservableNode';
import { AnalyzerNode } from './nodes/AnalyzerNode';
import { DecisionNode } from './nodes/DecisionNode';
import { TerminalNode } from './nodes/TerminalNode';

interface PlaybookEditorCanvasProps {
  playbookId?: string;
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node[], edges: Edge[]) => void;
  readonly?: boolean;
}

// Node types for React Flow
const nodeTypes: NodeTypes = {
  trigger: TriggerNode,
  action: ActionNode,
  observable: ObservableNode,
  analyzer: AnalyzerNode,
  decision: DecisionNode,
  terminal: TerminalNode,
};

export function PlaybookEditorCanvas({
  playbookId,
  initialNodes = [],
  initialEdges = [],
  onSave,
  readonly = false,
}: PlaybookEditorCanvasProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [savedState, setSavedState] = useState<{ nodes: Node[]; edges: Edge[] } | null>(null);

  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // Update nodes/edges when playbook data changes
  useEffect(() => {
    if (initialNodes.length > 0 || initialEdges.length > 0) {
      setNodes(initialNodes);
      setEdges(initialEdges);
    }
  }, [playbookId, initialNodes, initialEdges, setNodes, setEdges]);

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: 'smoothstep',
            markerEnd: {
              type: MarkerType.ArrowClosed,
            },
          },
          eds
        )
      );
    },
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current || !reactFlowInstance) return;

      const type = event.dataTransfer.getData('application/reactflow');
      if (!type) return;

      const position = reactFlowInstance.screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const newNode: Node = {
        id: `${type}-${Date.now()}`,
        type,
        position,
        data: {
          label: `${type} node`,
          ...getDefaultNodeData(type),
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(nodes, edges);
      setSavedState({ nodes, edges });
      toast.success('Playbook saved successfully');
    }
  }, [nodes, edges, onSave]);

  const handleValidate = useCallback(async () => {
    // Basic validation
    const triggerNodes = nodes.filter((n) => n.type === 'trigger');
    if (triggerNodes.length === 0) {
      toast.error('Playbook must have at least one trigger node');
      return;
    }

    // Check for valid connections
    const nodeIds = new Set(nodes.map((n) => n.id));
    for (const edge of edges) {
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
        toast.error('Invalid edge connection detected');
        return;
      }
    }

    // If playbook ID exists, validate via API
    if (playbookId) {
      try {
        const { playbooksApi } = await import('@/lib/api/playbooks');
        const result = await playbooksApi.validate(playbookId);
        if (result.valid) {
          toast.success('Playbook is valid');
          if (result.warnings.length > 0) {
            toast(`Warnings: ${result.warnings.join(', ')}`, { icon: '⚠️' });
          }
        } else {
          toast.error(`Validation failed: ${result.errors.join(', ')}`);
        }
      } catch (error) {
        toast.error('Failed to validate playbook');
      }
    } else {
      toast.success('Playbook structure is valid');
    }
  }, [nodes, edges, playbookId]);

  const hasUnsavedChanges = savedState
    ? JSON.stringify(savedState) !== JSON.stringify({ nodes, edges })
    : nodes.length > 0 || edges.length > 0;

  return (
    <div className="h-screen flex flex-col bg-surface-hover dark:bg-bg">
      {/* Toolbar */}
      <div className="flex items-center justify-between p-4 border-b border-surface-card-border dark:border-surface-card-border bg-surface-card">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-text-main">
            {playbookId ? 'Edit Playbook' : 'New Playbook'}
          </h2>
          {hasUnsavedChanges && (
            <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded dark:bg-yellow-900 dark:text-yellow-200">
              Unsaved changes
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleValidate}
            className="px-4 py-2 text-sm font-medium text-text-muted bg-surface-card border border-border rounded-md hover:bg-surface-hover focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:text-text-main dark:border-border dark:hover:bg-bg-alt"
          >
            Validate Playbook
          </button>
          {!readonly && (
            <button
              onClick={handleSave}
              disabled={!hasUnsavedChanges}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Save Playbook Workflow
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Node Palette Sidebar */}
        {!readonly && (
          <div className="w-64 border-r border-surface-card-border dark:border-surface-card-border bg-surface-card overflow-y-auto">
            <PlaybookNodePalette />
          </div>
        )}

        {/* Canvas */}
        <div className="flex-1 relative" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypes}
            fitView
          >
            <Background />
            <Controls />
            <MiniMap />
          </ReactFlow>
        </div>

        {/* Properties Panel */}
        {selectedNode && (
          <div className="w-80 border-l border-surface-card-border dark:border-surface-card-border bg-surface-card overflow-y-auto">
            <PlaybookPropertiesPanel
              node={selectedNode}
              onUpdate={(updatedNode) => {
                setNodes((nds) =>
                  nds.map((node) => (node.id === updatedNode.id ? updatedNode : node))
                );
                setSelectedNode(updatedNode);
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Get default data for a node type
 */
function getDefaultNodeData(type: string): any {
  switch (type) {
    case 'trigger':
      return { trigger_type: 'manual' };
    case 'action':
      return { action_type: 'iam_action' };
    case 'observable':
      return { data_type: 'ip' };
    case 'analyzer':
      return { analyzer_id: '' };
    case 'decision':
      return { condition: '' };
    case 'terminal':
      return { result: 'success' };
    default:
      return {};
  }
}

// Wrapper component with ReactFlowProvider
export function PlaybookEditorCanvasWrapper(props: PlaybookEditorCanvasProps) {
  return (
    <ReactFlowProvider>
      <PlaybookEditorCanvas {...props} />
    </ReactFlowProvider>
  );
}
