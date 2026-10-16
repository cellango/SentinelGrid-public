/**
 * Trigger Node Component
 */

'use client';

import { Handle, Position } from 'reactflow';

export function TriggerNode({ data }: any) {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-red-50 border-2 border-red-500 dark:bg-red-900/20 dark:border-red-400">
      <div className="flex items-center gap-2">
        <span className="text-xl">🔔</span>
        <div>
          <div className="font-bold text-red-700 dark:text-red-400">{data.label}</div>
          <div className="text-xs text-red-600 dark:text-red-300">{data.trigger_type || 'manual'}</div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-red-500" />
    </div>
  );
}

