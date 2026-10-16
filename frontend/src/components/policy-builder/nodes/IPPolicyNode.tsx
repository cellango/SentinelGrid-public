/**
 * IP Policy Node Component
 * Visual representation of an IP-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { IPPolicyData } from '@/lib/policy/types';

interface IPPolicyNodeProps {
  data: IPPolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

export function IPPolicyNode({ data, selected }: IPPolicyNodeProps) {
  const ipCount = data.ipAddresses?.length || 0;
  const firstIP = data.ipAddresses?.[0] || 'No IPs';
  const moreIPs = ipCount > 1 ? ` +${ipCount - 1} more` : '';

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-green-500' : 'border-green-300'
      }`}
      style={{ borderColor: selected ? '#10B981' : '#6EE7B7' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center flex-shrink-0">
          <span className="text-green-600 text-lg">🌐</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1">
            <span className="truncate block">
              {firstIP}
              {moreIPs && <span className="text-text-muted">{moreIPs}</span>}
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

