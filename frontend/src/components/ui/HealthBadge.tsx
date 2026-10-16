'use client';

import { clsx } from 'clsx';

interface HealthBadgeProps {
  label: string;
  status?: string;
  className?: string;
}

/**
 * Shared health badge component replacing 12+ duplicate healthBadge() functions.
 * Displays service health status (healthy, degraded, unreachable, unknown).
 */
export default function HealthBadge({ label, status, className }: HealthBadgeProps) {
  const state = (status || 'unknown').toLowerCase();
  const isHealthy = state.includes('healthy');
  const isDegraded = state.includes('degraded');
  const isDown = state.includes('unreachable');

  const color = isHealthy
    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200'
    : isDegraded
      ? 'bg-amber-500/10 border-amber-500/40 text-amber-200'
      : isDown
        ? 'bg-rose-500/10 border-rose-500/40 text-rose-200'
        : 'bg-slate-700/60 border-slate-600 text-text-muted';

  return (
    <span
      className={clsx('inline-flex items-center px-2 py-1 rounded-full text-[11px] border', color, className)}
      title={`${label}: ${status || 'unknown'}`}
      role="status"
    >
      {label}: {status || 'unknown'}
    </span>
  );
}
