/**
 * Security Graph — Attack Path Visualization
 * Wiz-competitive visual attack path analysis using ReactFlow.
 * Shows connected risks: assets → vulnerabilities → lateral movement → impact.
 */

'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  ReactFlowProvider,
  MarkerType,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { AssetNode } from './nodes/AssetNode';
import { VulnerabilityNode } from './nodes/VulnerabilityNode';
import { ThreatActorNode } from './nodes/ThreatActorNode';
import { ImpactNode } from './nodes/ImpactNode';
import { ControlNode } from './nodes/ControlNode';
import clsx from 'clsx';

// ── Types ──────────────────────────────────────────────────────────────

export interface AttackPathEntity {
  id: string;
  type: 'asset' | 'vulnerability' | 'threat_actor' | 'impact' | 'control';
  label: string;
  severity?: 'critical' | 'high' | 'medium' | 'low' | 'info';
  domain?: string;
  status?: string;
  metadata?: Record<string, unknown>;
}

export interface AttackPathLink {
  source: string;
  target: string;
  label?: string;
  type?: 'exploits' | 'lateral_move' | 'escalates' | 'mitigates' | 'exposes';
}

export interface AttackPath {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  entities: AttackPathEntity[];
  links: AttackPathLink[];
}

interface SecurityGraphProps {
  paths: AttackPath[];
  selectedPathId?: string | null;
  onSelectPath?: (pathId: string) => void;
  onNodeClick?: (entity: AttackPathEntity) => void;
  className?: string;
}

// ── Node types ─────────────────────────────────────────────────────────

const nodeTypes = {
  asset: AssetNode,
  vulnerability: VulnerabilityNode,
  threat_actor: ThreatActorNode,
  impact: ImpactNode,
  control: ControlNode,
};

// ── Edge color by relationship ────────────────────────────────────────

const EDGE_COLORS: Record<string, string> = {
  exploits: '#ef4444',
  lateral_move: '#f59e0b',
  escalates: '#f97316',
  mitigates: '#22c55e',
  exposes: '#a855f7',
  default: '#64748b',
};

// ── Severity colors for minimap ────────────────────────────────────────

const SEVERITY_NODE_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#3b82f6',
  info: '#6b7280',
};

// ── Layout: Dagre-like horizontal layout ──────────────────────────────

function layoutEntities(entities: AttackPathEntity[]): Map<string, { x: number; y: number }> {
  const positions = new Map<string, { x: number; y: number }>();
  const typeOrder = ['threat_actor', 'vulnerability', 'asset', 'control', 'impact'];
  const columns: Record<string, AttackPathEntity[]> = {};

  for (const e of entities) {
    const col = e.type;
    if (!columns[col]) columns[col] = [];
    columns[col].push(e);
  }

  const COL_WIDTH = 280;
  const ROW_HEIGHT = 120;

  typeOrder.forEach((type, colIndex) => {
    const items = columns[type] || [];
    const colX = colIndex * COL_WIDTH;
    items.forEach((item, rowIndex) => {
      const totalHeight = items.length * ROW_HEIGHT;
      const startY = -totalHeight / 2;
      positions.set(item.id, { x: colX, y: startY + rowIndex * ROW_HEIGHT });
    });
  });

  return positions;
}

// ── Component ──────────────────────────────────────────────────────────

function SecurityGraphInner({
  paths,
  selectedPathId,
  onSelectPath,
  onNodeClick,
  className,
}: SecurityGraphProps) {
  const activePath = paths.find((p) => p.id === selectedPathId) || paths[0];
  const [filter, setFilter] = useState<string>('all');

  const filteredPaths = useMemo(() => {
    if (filter === 'all') return paths;
    return paths.filter((p) => p.severity === filter);
  }, [paths, filter]);

  const { initialNodes, initialEdges } = useMemo(() => {
    if (!activePath) return { initialNodes: [] as Node[], initialEdges: [] as Edge[] };

    const positions = layoutEntities(activePath.entities);

    const nodes: Node[] = activePath.entities.map((entity) => ({
      id: entity.id,
      type: entity.type,
      position: positions.get(entity.id) || { x: 0, y: 0 },
      data: {
        label: entity.label,
        severity: entity.severity,
        domain: entity.domain,
        status: entity.status,
        metadata: entity.metadata,
      },
    }));

    const edges: Edge[] = activePath.links.map((link, i) => ({
      id: `edge-${link.source}-${link.target}-${i}`,
      source: link.source,
      target: link.target,
      type: 'smoothstep',
      animated: link.type === 'exploits' || link.type === 'lateral_move',
      label: link.label || link.type,
      labelStyle: { fill: '#94a3b8', fontSize: 10, fontWeight: 500 },
      labelBgStyle: { fill: 'rgba(2, 6, 23, 0.8)', fillOpacity: 0.8 },
      labelBgPadding: [6, 3] as [number, number],
      labelBgBorderRadius: 4,
      style: {
        stroke: EDGE_COLORS[link.type || 'default'] || EDGE_COLORS.default,
        strokeWidth: 2,
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: EDGE_COLORS[link.type || 'default'] || EDGE_COLORS.default,
      },
    }));

    return { initialNodes: nodes, initialEdges: edges };
  }, [activePath]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialEdges, initialNodes, setEdges, setNodes]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (!onNodeClick || !activePath) return;
      const entity = activePath.entities.find((e) => e.id === node.id);
      if (entity) onNodeClick(entity);
    },
    [activePath, onNodeClick]
  );

  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const p of paths) {
      if (p.severity in counts) counts[p.severity as keyof typeof counts]++;
    }
    return counts;
  }, [paths]);

  if (!paths.length) {
    return (
      <div className={clsx('flex items-center justify-center h-96 bg-surface-card rounded-lg border border-border-faint', className)}>
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary-ghost flex items-center justify-center">
            <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h3 className="text-text-main font-semibold mb-1">No Attack Paths Detected</h3>
          <p className="text-text-muted text-sm">Your environment looks secure. We&apos;ll alert you if attack paths are discovered.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Path selector + severity filter */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 px-4 py-3 border-b border-border-faint bg-surface-card">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-text-main whitespace-nowrap">Attack Paths</h3>
          <div className="flex gap-1.5">
            {(['all', 'critical', 'high', 'medium', 'low'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setFilter(sev)}
                className={clsx(
                  'px-2.5 py-1 text-xs font-medium rounded-full transition-colors min-h-[32px]',
                  filter === sev
                    ? sev === 'all'
                      ? 'bg-primary/20 text-primary border border-primary/40'
                      : sev === 'critical'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                        : sev === 'high'
                          ? 'bg-orange-500/20 text-orange-300 border border-orange-500/40'
                          : sev === 'medium'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                            : 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                    : 'bg-surface-hover text-text-muted border border-transparent hover:border-border-muted'
                )}
                aria-pressed={filter === sev}
              >
                {sev === 'all' ? `All (${paths.length})` : `${sev} (${severityCounts[sev]})`}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Path list sidebar */}
        <div className="w-56 border-r border-border-faint overflow-y-auto bg-surface-card hidden lg:block">
          <nav aria-label="Attack paths" className="p-2 space-y-1">
            {filteredPaths.map((path) => (
              <button
                key={path.id}
                onClick={() => onSelectPath?.(path.id)}
                className={clsx(
                  'w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors min-h-[44px]',
                  path.id === activePath?.id
                    ? 'bg-primary/10 border border-primary/30 text-text-main'
                    : 'text-text-muted hover:bg-surface-hover hover:text-text-main border border-transparent'
                )}
                aria-current={path.id === activePath?.id ? 'true' : undefined}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span
                    className={clsx(
                      'w-2 h-2 rounded-full flex-shrink-0',
                      path.severity === 'critical' && 'bg-rose-500',
                      path.severity === 'high' && 'bg-orange-500',
                      path.severity === 'medium' && 'bg-amber-500',
                      path.severity === 'low' && 'bg-blue-500'
                    )}
                  />
                  <span className="truncate font-medium">{path.title}</span>
                </div>
                <span className="text-xs text-text-muted ml-4">
                  {path.entities.length} entities · {path.links.length} links
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Graph canvas */}
        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            proOptions={{ hideAttribution: true }}
            minZoom={0.3}
            maxZoom={2}
          >
            <Background color="rgba(148, 163, 184, 0.08)" gap={24} size={1} />
            <Controls
              className="!bg-surface-card !border-border-faint !rounded-lg !shadow-lg [&>button]:!bg-surface-card [&>button]:!border-border-faint [&>button]:!text-text-muted [&>button:hover]:!bg-surface-hover"
              showInteractive={false}
            />
            <MiniMap
              nodeColor={(node) => SEVERITY_NODE_COLORS[node.data?.severity] || '#475569'}
              maskColor="rgba(2, 6, 23, 0.7)"
              className="!bg-surface-card !border-border-faint !rounded-lg"
            />
            <Panel position="top-right">
              <div className="flex items-center gap-3 bg-surface-card/90 backdrop-blur-sm border border-border-faint rounded-lg px-3 py-2 text-xs text-text-muted">
                <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-rose-500 rounded" />exploits</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-amber-500 rounded" />lateral move</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-emerald-500 rounded" />mitigates</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-0.5 bg-purple-500 rounded" />exposes</span>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

export default function SecurityGraph(props: SecurityGraphProps) {
  return (
    <ReactFlowProvider>
      <SecurityGraphInner {...props} />
    </ReactFlowProvider>
  );
}
