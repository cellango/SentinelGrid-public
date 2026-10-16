/**
 * Group Policy Node Component
 * Visual representation of a group-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { GroupPolicyData } from '@/lib/policy/types';

interface GroupPolicyNodeProps {
  data: GroupPolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

export function GroupPolicyNode({ data, selected }: GroupPolicyNodeProps) {
  const groupCount = data.groups?.length || 0;
  const groupNames = data.groups?.map((g) => g.name).join(', ') || 'No groups';

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-teal-500' : 'border-teal-300'
      }`}
      style={{ borderColor: selected ? '#14B8A6' : '#5EEAD4' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-teal-100 flex items-center justify-center flex-shrink-0">
          <span className="text-teal-600 text-lg">👥</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1">
            {groupCount > 0 ? (
              <span className="truncate block">{groupNames}</span>
            ) : (
              <span className="text-text-muted">No groups selected</span>
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

