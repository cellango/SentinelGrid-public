/**
 * Analyzer Node Component
 */

'use client';

import { Handle, Position } from 'reactflow';

export function AnalyzerNode({ data }: any) {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-teal-50 border-2 border-teal-500 dark:bg-teal-900/20 dark:border-teal-400">
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-teal-500" />
      <div className="flex items-center gap-2">
        <span className="text-xl">🔬</span>
        <div>
          <div className="font-bold text-teal-700 dark:text-teal-400">{data.label}</div>
          <div className="text-xs text-teal-600 dark:text-teal-300">
            {data.analyzer_id || 'analyzer'}
          </div>
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-teal-500" />
    </div>
  );
}

