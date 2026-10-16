/**
 * Role Policy Node Component
 * Visual representation of a role-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { RolePolicyData } from '@/lib/policy/types';

interface RolePolicyNodeProps {
  data: RolePolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

export function RolePolicyNode({ data, selected }: RolePolicyNodeProps) {
  const roleCount = data.roles?.length || 0;
  const roleNames = data.roles?.map((r) => r.name).join(', ') || 'No roles';

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-blue-500' : 'border-blue-300'
      }`}
      style={{ borderColor: selected ? '#3B82F6' : '#93C5FD' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
          <span className="text-blue-600 text-lg">👤</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1">
            {roleCount > 0 ? (
              <span className="truncate block">{roleNames}</span>
            ) : (
              <span className="text-text-muted">No roles selected</span>
            )}
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

