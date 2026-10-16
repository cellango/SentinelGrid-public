/**
 * Asset Node — represents a cloud resource, server, or endpoint
 */
'use client';

import { Handle, Position } from 'reactflow';
import clsx from 'clsx';

export function AssetNode({ data }: any) {
  return (
    <div className="relative px-4 py-3 rounded-lg border-2 border-cyan-500/50 bg-cyan-500/10 backdrop-blur-sm shadow-lg shadow-cyan-500/5 min-w-[160px]">
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-cyan-400 !border-cyan-600" />
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-md bg-cyan-500/20 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-cyan-300 uppercase tracking-wide">Asset</p>
          <p className="text-sm font-semibold text-text-main truncate">{data.label}</p>
          {data.domain && (
            <p className="text-[10px] text-text-muted mt-0.5">{data.domain}</p>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-cyan-400 !border-cyan-600" />
    </div>
  );
}
