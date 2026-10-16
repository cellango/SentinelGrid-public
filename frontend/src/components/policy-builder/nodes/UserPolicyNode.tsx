/**
 * User Policy Node Component
 * Visual representation of a user-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { UserPolicyData } from '@/lib/policy/types';

interface UserPolicyNodeProps {
  data: UserPolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

export function UserPolicyNode({ data, selected }: UserPolicyNodeProps) {
  const userCount = data.users?.length || 0;
  const firstUser = data.users?.[0] || 'No users';
  const moreUsers = userCount > 1 ? ` +${userCount - 1} more` : '';

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-pink-500' : 'border-pink-300'
      }`}
      style={{ borderColor: selected ? '#EC4899' : '#F9A8D4' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-pink-100 flex items-center justify-center flex-shrink-0">
          <span className="text-pink-600 text-lg">👨‍💼</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1">
            <span className="truncate block">
              {firstUser}
              {moreUsers && <span className="text-text-muted">{moreUsers}</span>}
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

