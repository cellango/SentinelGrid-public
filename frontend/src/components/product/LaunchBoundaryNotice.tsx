'use client';

import Link from 'next/link';

import EmptyState from '@/components/ui/EmptyState';

type NoticeAction = {
  label: string;
  href: string;
};

interface LaunchBoundaryNoticeProps {
  eyebrow?: string;
  title: string;
  description: string;
  bullets?: string[];
  primaryAction?: NoticeAction;
  secondaryAction?: NoticeAction;
}

export default function LaunchBoundaryNotice({
  eyebrow = 'Launch boundary',
  title,
  description,
  bullets = [],
  primaryAction,
  secondaryAction,
}: LaunchBoundaryNoticeProps) {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="rounded-2xl border border-border-faint bg-surface-card p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">{eyebrow}</p>
        <div className="mt-4">
          <EmptyState
            variant="coming-soon"
            title={title}
            description={description}
            compact
          />
        </div>

        {bullets.length > 0 && (
          <div className="mt-6 rounded-xl border border-border-faint bg-surface-hover/60 p-4">
            <h2 className="text-sm font-semibold text-text-main">Current status</h2>
            <ul className="mt-3 space-y-2 text-sm text-text-muted">
              {bullets.map((bullet) => (
                <li key={bullet} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary" aria-hidden="true" />
                  <span>{bullet}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {(primaryAction || secondaryAction) && (
          <div className="mt-6 flex flex-wrap gap-3">
            {primaryAction && (
              <Link
                href={primaryAction.href}
                className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-950 transition hover:brightness-110"
              >
                {primaryAction.label}
              </Link>
            )}
            {secondaryAction && (
              <Link
                href={secondaryAction.href}
                className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-border-faint px-4 py-2 text-sm font-medium text-text-main transition hover:border-primary/40"
              >
                {secondaryAction.label}
              </Link>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
