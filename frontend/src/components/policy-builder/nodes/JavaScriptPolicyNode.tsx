/**
 * JavaScript Policy Node Component
 * Visual representation of a JavaScript-based policy node
 */

'use client';

import { Handle, Position } from 'reactflow';
import { JavaScriptPolicyData } from '@/lib/policy/types';

interface JavaScriptPolicyNodeProps {
  data: JavaScriptPolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

export function JavaScriptPolicyNode({ data, selected }: JavaScriptPolicyNodeProps) {
  const codeLength = data.code?.length || 0;
  const hasCode = codeLength > 0;

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[180px] ${
        selected ? 'border-yellow-500' : 'border-yellow-300'
      }`}
      style={{ borderColor: selected ? '#EAB308' : '#FDE047' }}
    >
      <Handle type="target" position={Position.Top} className="w-3 h-3" />
      
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 rounded-lg bg-yellow-100 flex items-center justify-center flex-shrink-0">
          <span className="text-yellow-600 text-lg">💻</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-text-main">{data.label}</div>
          <div className="text-xs text-text-muted mt-1">
            {hasCode ? (
              <span className="text-green-600">{codeLength} characters</span>
            ) : (
              <span className="text-text-muted">No code defined</span>
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

