/**
 * Aggregate Node Component
 * Visual representation of AND/OR/NOT gates
 */

'use client';

import { Handle, Position } from 'reactflow';
import { AggregatePolicyData } from '@/lib/policy/types';

interface AggregateNodeProps {
  data: AggregatePolicyData & { label: string; selected?: boolean };
  selected?: boolean;
}

const GATE_SYMBOLS: Record<string, string> = {
  AND: '∧',
  OR: '∨',
  NOT: '¬',
};

const GATE_NAMES: Record<string, string> = {
  AND: 'AND',
  OR: 'OR',
  NOT: 'NOT',
};

export function AggregateNode({ data, selected }: AggregateNodeProps) {
  const { gateType } = data;
  const symbol = GATE_SYMBOLS[gateType] || gateType;
  const name = GATE_NAMES[gateType] || gateType;

  // NOT gates only have one input
  const isNOT = gateType === 'NOT';

  return (
    <div
      className={`px-4 py-3 bg-surface-card border-2 rounded-lg shadow-sm min-w-[120px] ${
        selected ? 'border-purple-500' : 'border-purple-300'
      }`}
      style={{ borderColor: selected ? '#8B5CF6' : '#C4B5FD' }}
    >
      {!isNOT && <Handle type="target" position={Position.Top} className="w-3 h-3" />}
      {isNOT && <Handle type="target" position={Position.Left} className="w-3 h-3" />}
      
      <div className="flex flex-col items-center">
        <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center mb-1">
          <span className="text-purple-600 text-2xl font-bold">{symbol}</span>
        </div>
        <div className="font-medium text-sm text-text-main">{name}</div>
        {data.decisionStrategy && data.gateType === 'AND' && (
          <div className="text-xs text-text-muted mt-0.5 capitalize">
            {data.decisionStrategy.toLowerCase()}
          </div>
        )}
        {data.logic === 'NEGATIVE' && (
          <div className="mt-1">
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
              Deny
            </span>
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3" />
    </div>
  );
}

