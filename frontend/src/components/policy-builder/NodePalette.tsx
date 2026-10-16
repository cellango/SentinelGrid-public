/**
 * Node Palette Component
 * Draggable source for policy nodes
 */

'use client';

import { useCallback, useState } from 'react';
import { NodePaletteItem } from '@/lib/policy/types';

const nodeTypes: NodePaletteItem[] = [
  {
    id: 'role-policy',
    label: 'Role Policy',
    type: 'role',
    icon: '👤',
    description: 'Grant access based on user roles',
    color: '#3B82F6',
  },
  {
    id: 'time-policy',
    label: 'Time Policy',
    type: 'time',
    icon: '⏰',
    description: 'Restrict access by time/day',
    color: '#F59E0B',
  },
  {
    id: 'ip-policy',
    label: 'IP Policy',
    type: 'ip',
    icon: '🌐',
    description: 'Restrict access by IP address',
    color: '#10B981',
  },
  {
    id: 'group-policy',
    label: 'Group Policy',
    type: 'group',
    icon: '👥',
    description: 'Grant access to group members',
    color: '#14B8A6',
  },
  {
    id: 'client-policy',
    label: 'Client Policy',
    type: 'client',
    icon: '🖥️',
    description: 'Restrict by client application',
    color: '#6366F1',
  },
  {
    id: 'user-policy',
    label: 'User Policy',
    type: 'user',
    icon: '👨‍💼',
    description: 'Grant access to specific users',
    color: '#EC4899',
  },
  {
    id: 'js-policy',
    label: 'JavaScript Policy',
    type: 'js',
    icon: '💻',
    description: 'Custom logic via JavaScript',
    color: '#EAB308',
  },
  {
    id: 'and-gate',
    label: 'AND Gate',
    type: 'aggregate',
    icon: '∧',
    description: 'All inputs must be true',
    color: '#8B5CF6',
    gateType: 'AND',
  },
  {
    id: 'or-gate',
    label: 'OR Gate',
    type: 'aggregate',
    icon: '∨',
    description: 'Any input can be true',
    color: '#8B5CF6',
    gateType: 'OR',
  },
  {
    id: 'not-gate',
    label: 'NOT Gate',
    type: 'aggregate',
    icon: '¬',
    description: 'Invert the input',
    color: '#8B5CF6',
    gateType: 'NOT',
  },
];

interface NodePaletteProps {
  onNodeDragStart?: (nodeType: NodePaletteItem, event: React.DragEvent) => void;
  readonly?: boolean;
}

export function NodePalette({ onNodeDragStart, readonly = false }: NodePaletteProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const handleDragStart = useCallback(
    (nodeType: NodePaletteItem, event: React.DragEvent) => {
      if (readonly) {
        event.preventDefault();
        return;
      }
      event.dataTransfer.setData('application/reactflow', JSON.stringify(nodeType));
      event.dataTransfer.effectAllowed = 'move';
      onNodeDragStart?.(nodeType, event);
    },
    [onNodeDragStart, readonly]
  );

  const filteredNodeTypes = nodeTypes.filter((nodeType) => {
    const query = searchQuery.trim().toLowerCase();
    if (!query) return true;
    return (
      nodeType.label.toLowerCase().includes(query) ||
      nodeType.description.toLowerCase().includes(query)
    );
  });

  return (
    <div className="w-64 bg-surface-card border-r border-surface-card-border h-full overflow-y-auto">
      <div className="p-4 border-b border-surface-card-border">
        <h3 className="text-sm font-semibold text-text-main mb-2">Policy Components</h3>
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          className="w-full px-3 py-2 text-sm border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {readonly && (
          <p className="mt-2 text-xs text-text-muted">
            Preview mode: drag-and-drop editing is disabled until you open an editable tenant policy.
          </p>
        )}
      </div>

      <div className="p-2 space-y-1">
        {filteredNodeTypes.map((nodeType) => (
          <div
            key={nodeType.id}
            draggable={!readonly}
            onDragStart={(e) => handleDragStart(nodeType, e)}
            className={`flex items-center gap-3 p-3 rounded-lg border border-surface-card-border transition-colors ${
              readonly
                ? 'cursor-not-allowed opacity-60'
                : 'cursor-grab hover:bg-blue-50 hover:border-blue-300 active:cursor-grabbing'
            }`}
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
              style={{ backgroundColor: `${nodeType.color}20`, color: nodeType.color }}
            >
              {nodeType.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-text-main">{nodeType.label}</div>
              <div className="text-xs text-text-muted truncate">{nodeType.description}</div>
            </div>
          </div>
        ))}
        {filteredNodeTypes.length === 0 && (
          <div className="px-3 py-4 text-xs text-text-muted">No policy components match that search.</div>
        )}
      </div>

    </div>
  );
}
