/**
 * Control Node — represents a security control / mitigation
 */
'use client';

import { Handle, Position } from 'reactflow';

export function ControlNode({ data }: any) {
  return (
    <div className="relative px-4 py-3 rounded-lg border-2 border-emerald-500/60 bg-emerald-500/10 backdrop-blur-sm shadow-lg shadow-emerald-500/10 min-w-[160px]">
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-emerald-400 !border-emerald-600" />
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-md bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-emerald-300 uppercase tracking-wide">Control</p>
          <p className="text-sm font-semibold text-text-main truncate">{data.label}</p>
          {data.status && (
            <p className="text-[10px] text-emerald-400/80 mt-0.5">{data.status}</p>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-emerald-400 !border-emerald-600" />
    </div>
  );
}
