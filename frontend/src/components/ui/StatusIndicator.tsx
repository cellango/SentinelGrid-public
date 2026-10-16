'use client';

import { clsx } from 'clsx';

export type StatusType =
  | 'open' | 'in_progress' | 'resolved' | 'closed'
  | 'pending' | 'approved' | 'denied' | 'rejected'
  | 'expired' | 'revoked' | 'cancelled'
  | 'running' | 'completed' | 'executed' | 'failed'
  | 'new' | 'acknowledged';

interface StatusIndicatorProps {
  status: string;
  className?: string;
  /** Show border around badge (default: true) */
  bordered?: boolean;
  /** Render as a dot indicator instead of a pill (default: false) */
  dot?: boolean;
}

const statusConfig: Record<string, { bg: string; text: string; border: string; dot: string }> = {
  // Workflow states
  open: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-400' },
  new: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-400' },
  acknowledged: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', border: 'border-cyan-500/30', dot: 'bg-cyan-400' },
  in_progress: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30', dot: 'bg-yellow-400' },
  running: { bg: 'bg-blue-500/20', text: 'text-blue-400', border: 'border-blue-500/30', dot: 'bg-blue-400' },
  pending: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/30', dot: 'bg-amber-400' },

  // Success states
  resolved: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-400' },
  completed: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-400' },
  executed: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-400' },
  approved: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30', dot: 'bg-green-400' },

  // Failure states
  failed: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-400' },
  denied: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-400' },
  rejected: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30', dot: 'bg-red-400' },

  // Neutral / terminal states
  closed: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30', dot: 'bg-slate-400' },
  expired: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30', dot: 'bg-slate-400' },
  revoked: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30', dot: 'bg-slate-400' },
  cancelled: { bg: 'bg-slate-500/20', text: 'text-slate-400', border: 'border-slate-500/30', dot: 'bg-slate-400' },
};

const fallback = statusConfig.open;

export function getStatusClasses(status: string): string {
  const config = statusConfig[status.toLowerCase()] || fallback;
  return `${config.bg} ${config.text} ${config.border}`;
}

export default function StatusIndicator({ status, className, bordered = true, dot = false }: StatusIndicatorProps) {
  const config = statusConfig[status.toLowerCase()] || fallback;
  const label = status.replace(/_/g, ' ');

  if (dot) {
    return (
      <span className={clsx('inline-flex items-center gap-1.5 text-xs', config.text, className)}>
        <span className={clsx('w-2 h-2 rounded-full', config.dot)} aria-hidden="true" />
        <span className="capitalize">{label}</span>
      </span>
    );
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full capitalize',
        config.bg,
        config.text,
        bordered && `border ${config.border}`,
        className
      )}
    >
      {label}
    </span>
  );
}
