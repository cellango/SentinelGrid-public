/**
 * Action Node Component
 */

'use client';

import { Handle, Position } from 'reactflow';

export function ActionNode({ data }: any) {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-blue-50 border-2 border-blue-500 dark:bg-blue-900/20 dark:border-blue-400">
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-blue-500" />
      <div className="flex items-center gap-2">
        <span className="text-xl">⚙️</span>
        <div>
          <div className="font-bold text-blue-700 dark:text-blue-400">{data.label}</div>
          <div className="text-xs text-blue-600 dark:text-blue-300">
            {data.action_type || 'action'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-blue-500" />
    </div>
  );
}

