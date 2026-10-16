/**
 * Playbook Node Palette Component
 * Draggable source for playbook nodes
 */

'use client';

'use client';

import { useState, useCallback } from 'react';

interface NodePaletteItem {
  id: string;
  label: string;
  type: string;
  icon: string;
  description: string;
  color: string;
  category: 'triggers' | 'actions' | 'observables' | 'analyzers' | 'decisions' | 'terminals';
}

const nodeTypes: NodePaletteItem[] = [
  // Triggers
  {
    id: 'alert-trigger',
    label: 'Alert Trigger',
    type: 'trigger',
    icon: '🔔',
    description: 'Playbook starts when alert matches criteria',
    color: '#EF4444',
    category: 'triggers',
  },
  {
    id: 'incident-trigger',
    label: 'Incident Trigger',
    type: 'trigger',
    icon: '🚨',
    description: 'Playbook starts when incident created/updated',
    color: '#F97316',
    category: 'triggers',
  },
  {
    id: 'manual-trigger',
    label: 'Manual Trigger',
    type: 'trigger',
    icon: '👆',
    description: 'User-initiated execution',
    color: '#8B5CF6',
    category: 'triggers',
  },
  {
    id: 'scheduled-trigger',
    label: 'Scheduled Trigger',
    type: 'trigger',
    icon: '⏰',
    description: 'Time-based execution (cron)',
    color: '#06B6D4',
    category: 'triggers',
  },
  // Actions
  {
    id: 'iam-action',
    label: 'IAM Action',
    type: 'action',
    icon: '🔐',
    description: 'IAM operations (disable user, reset password, etc.)',
    color: '#3B82F6',
    category: 'actions',
  },
  {
    id: 'email-action',
    label: 'Email Action',
    type: 'action',
    icon: '📧',
    description: 'Email operations (search, delete, quarantine)',
    color: '#10B981',
    category: 'actions',
  },
  {
    id: 'ticket-action',
    label: 'Ticket Action',
    type: 'action',
    icon: '🎫',
    description: 'Create or update tickets',
    color: '#F59E0B',
    category: 'actions',
  },
  {
    id: 'notification-action',
    label: 'Notification',
    type: 'action',
    icon: '📢',
    description: 'Send notifications (email, Slack, SMS)',
    color: '#EC4899',
    category: 'actions',
  },
  // Observables
  {
    id: 'extract-observable',
    label: 'Extract Observable',
    type: 'observable',
    icon: '🔍',
    description: 'Extract IOCs (IP, Domain, Hash, etc.)',
    color: '#6366F1',
    category: 'observables',
  },
  // Analyzers
  {
    id: 'run-analyzer',
    label: 'Run Analyzer',
    type: 'analyzer',
    icon: '🔬',
    description: 'Execute TheHive analyzer on observable',
    color: '#14B8A6',
    category: 'analyzers',
  },
  // Decisions
  {
    id: 'condition',
    label: 'Condition',
    type: 'decision',
    icon: '❓',
    description: 'If/Then logic based on previous outputs',
    color: '#EAB308',
    category: 'decisions',
  },
  // Terminals
  {
    id: 'success',
    label: 'Success',
    type: 'terminal',
    icon: '✅',
    description: 'Playbook completed successfully',
    color: '#22C55E',
    category: 'terminals',
  },
  {
    id: 'failure',
    label: 'Failure',
    type: 'terminal',
    icon: '❌',
    description: 'Playbook failed',
    color: '#EF4444',
    category: 'terminals',
  },
  {
    id: 'escalation',
    label: 'Escalation',
    type: 'terminal',
    icon: '⚠️',
    description: 'Requires manual intervention',
    color: '#F59E0B',
    category: 'terminals',
  },
];

const categories: { id: string; label: string }[] = [
  { id: 'triggers', label: 'Triggers' },
  { id: 'actions', label: 'Actions' },
  { id: 'observables', label: 'Observables' },
  { id: 'analyzers', label: 'Analyzers' },
  { id: 'decisions', label: 'Decisions' },
  { id: 'terminals', label: 'Terminals' },
];

export function PlaybookNodePalette() {
  const [selectedCategory, setSelectedCategory] = useState<string>('triggers');

  const filteredNodes = nodeTypes.filter((node) => node.category === selectedCategory);

  const onDragStart = useCallback((event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <div className="p-4 space-y-4">
      <h3 className="text-sm font-semibold text-text-main mb-3">Node Palette</h3>
      
      {/* Category tabs */}
      <div className="flex flex-wrap gap-1 mb-4">
        {categories.map((category) => (
          <button
            key={category.id}
            onClick={() => setSelectedCategory(category.id)}
            className={`px-2 py-1 text-xs rounded ${
              selectedCategory === category.id
                ? 'bg-blue-600 text-white'
                : 'bg-bg-alt text-text-muted hover:bg-surface-hover dark:bg-bg-alt dark:text-text-muted dark:hover:bg-bg-alt'
            }`}
          >
            {category.label}
          </button>
        ))}
      </div>

      {/* Node list */}
      <div className="space-y-2">
        {filteredNodes.map((node) => (
          <div
            key={node.id}
            draggable
            onDragStart={(e) => onDragStart(e, node.type)}
            className="p-3 border border-surface-card-border dark:border-surface-card-border rounded-lg cursor-move hover:shadow-md transition-shadow bg-surface-card"
          >
            <div className="flex items-start gap-2">
              <span className="text-xl">{node.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-text-main">
                  {node.label}
                </div>
                <div className="text-xs text-text-muted dark:text-text-muted mt-1">
                  {node.description}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

