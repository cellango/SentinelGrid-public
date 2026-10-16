/**
 * Observable Node Component
 */

'use client';

import { Handle, Position } from 'reactflow';

export function ObservableNode({ data }: any) {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-purple-50 border-2 border-purple-500 dark:bg-purple-900/20 dark:border-purple-400">
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-purple-500" />
      <div className="flex items-center gap-2">
        <span className="text-xl">🔍</span>
        <div>
          <div className="font-bold text-purple-700 dark:text-purple-400">{data.label}</div>
          <div className="text-xs text-purple-600 dark:text-purple-300">
            {data.data_type || 'observable'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-purple-500" />
    </div>
  );
}

