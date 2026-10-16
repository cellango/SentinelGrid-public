/**
 * Decision Node Component
 */

'use client';

import { Handle, Position } from 'reactflow';

export function DecisionNode({ data }: any) {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-yellow-50 border-2 border-yellow-500 dark:bg-yellow-900/20 dark:border-yellow-400">
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-yellow-500" />
      <div className="flex items-center gap-2">
        <span className="text-xl">❓</span>
        <div>
          <div className="font-bold text-yellow-700 dark:text-yellow-400">{data.label}</div>
          <div className="text-xs text-yellow-600 dark:text-yellow-300">Condition</div>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        id="true"
        className="w-3 h-3 bg-green-500"
        style={{ top: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Right}
        id="false"
        className="w-3 h-3 bg-red-500"
        style={{ top: '70%' }}
      />
    </div>
  );
}

