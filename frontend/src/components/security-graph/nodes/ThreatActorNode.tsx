/**
 * Threat Actor Node — represents an attacker, bot, or malicious entity
 */
'use client';

import { Handle, Position } from 'reactflow';

export function ThreatActorNode({ data }: any) {
  return (
    <div className="relative px-4 py-3 rounded-lg border-2 border-red-600/60 bg-red-600/10 backdrop-blur-sm shadow-lg shadow-red-500/10 min-w-[160px]">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-md bg-red-600/20 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium text-red-400 uppercase tracking-wide">Threat Actor</p>
          <p className="text-sm font-semibold text-text-main truncate">{data.label}</p>
          {data.status && (
            <p className="text-[10px] text-text-muted mt-0.5">{data.status}</p>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-red-400 !border-red-600" />
    </div>
  );
}
