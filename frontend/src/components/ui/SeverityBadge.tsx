'use client';

import { clsx } from 'clsx';

export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low' | 'info';

interface SeverityBadgeProps {
  severity: string;
  className?: string;
  /** Show border around badge (default: true) */
  bordered?: boolean;
}

const severityConfig: Record<SeverityLevel, { bg: string; text: string; border: string }> = {
  critical: {
    bg: 'bg-red-500/20',
    text: 'text-red-400',
    border: 'border-red-500/30',
  },
  high: {
    bg: 'bg-orange-500/20',
    text: 'text-orange-400',
    border: 'border-orange-500/30',
  },
  medium: {
    bg: 'bg-yellow-500/20',
    text: 'text-yellow-400',
    border: 'border-yellow-500/30',
  },
  low: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-400',
    border: 'border-blue-500/30',
  },
  info: {
    bg: 'bg-slate-500/20',
    text: 'text-slate-400',
    border: 'border-slate-500/30',
  },
};

const fallback = severityConfig.info;

export function getSeverityClasses(severity: string): string {
  const config = severityConfig[severity.toLowerCase() as SeverityLevel] || fallback;
  return `${config.bg} ${config.text} ${config.border}`;
}

export default function SeverityBadge({ severity, className, bordered = true }: SeverityBadgeProps) {
  const config = severityConfig[severity.toLowerCase() as SeverityLevel] || fallback;

  return (
    <span
      className={clsx(
        'inline-flex items-center px-2 py-1 text-xs font-semibold rounded-full',
        config.bg,
        config.text,
        bordered && `border ${config.border}`,
        className
      )}
    >
      {severity.charAt(0).toUpperCase() + severity.slice(1).toLowerCase()}
    </span>
  );
}
