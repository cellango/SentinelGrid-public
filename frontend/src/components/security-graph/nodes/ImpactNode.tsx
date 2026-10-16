/**
 * Impact Node — represents the blast radius / business impact
 */
'use client';

import { Handle, Position } from 'reactflow';

export function ImpactNode({ data }: any) {
  return (
    <div className="relative px-4 py-3 rounded-lg border-2 border-purple-500/60 bg-purple-500/10 backdrop-blur-sm shadow-lg shadow-purple-500/10 min-w-[160px]">
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-purple-400 !border-purple-600" />
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-md bg-purple-500/20 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-purple-300 uppercase tracking-wide">Impact</p>
          <p className="text-sm font-semibold text-text-main truncate">{data.label}</p>
          {data.metadata?.blast_radius && (
            <p className="text-[10px] text-text-muted mt-0.5">{String(data.metadata.blast_radius)} affected</p>
          )}
        </div>
      </div>
    </div>
  );
}
