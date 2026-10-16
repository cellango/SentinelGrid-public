/**
 * Client Policy Node Component
 * Visual representation of a client-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { ClientPolicyData } from '@/lib/policy/types';

interface ClientPolicyNodeProps {
  data: ClientPolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

export function ClientPolicyNode({ data, selected }: ClientPolicyNodeProps) {
  const clientCount = data.clients?.length || 0;
  const firstClient = data.clients?.[0] || 'No clients';
  const moreClients = clientCount > 1 ? ` +${clientCount - 1} more` : '';

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-indigo-500' : 'border-indigo-300'
      }`}
      style={{ borderColor: selected ? '#6366F1' : '#A5B4FC' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center flex-shrink-0">
          <span className="text-indigo-600 text-lg">🖥️</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1">
            <span className="truncate block">
              {firstClient}
              {moreClients && <span className="text-text-muted">{moreClients}</span>}
            </span>
          </div>
          {data.logic === 'NEGATIVE' && (
            <div className="mt-1">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                Deny
              </span>
            </div>
          )}
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
}

