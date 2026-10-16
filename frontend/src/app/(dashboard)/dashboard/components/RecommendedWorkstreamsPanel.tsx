'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { Recommendation } from '@/lib/api/dashboard';
import {
  formatRecommendationClass,
  getPrimaryRecommendationAction,
  getRecommendationActionHref,
  getRecommendationHref,
} from '@/lib/dashboard/recommendations';

interface RecommendedWorkstreamsPanelProps {
  recommendations?: Recommendation[];
  isLoading?: boolean;
}

function priorityClasses(priority: Recommendation['priority']) {
  switch (priority) {
    case 'critical':
      return 'border-rose-500/40 bg-rose-500/15 text-rose-200';
    case 'high':
      return 'border-orange-500/40 bg-orange-500/15 text-orange-200';
    case 'medium':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-200';
    default:
      return 'border-sky-500/40 bg-sky-500/15 text-sky-200';
  }
}

export default function RecommendedWorkstreamsPanel({
  recommendations = [],
  isLoading = false,
}: RecommendedWorkstreamsPanelProps) {
  const items = recommendations.slice(0, 3);

  return (
    <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Workstreams</p>
          <h2 className="mt-1 text-xl font-semibold text-text-main">Drive the next outcomes</h2>
          <p className="mt-2 max-w-2xl text-sm text-text-muted">
            Guided fixes and response moves that should reduce the queue fastest this week.
          </p>
        </div>
        <Link
          href="/dashboard/playbooks"
          className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
        >
          Open playbooks
        </Link>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, index) => (
            <div
              key={index}
              className="animate-pulse rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.5)] p-5"
            >
              <div className="h-4 w-20 rounded bg-slate-800" />
              <div className="mt-3 h-5 w-3/4 rounded bg-slate-800" />
              <div className="mt-2 h-4 w-full rounded bg-slate-800" />
              <div className="mt-2 h-4 w-5/6 rounded bg-slate-800" />
              <div className="mt-5 h-10 w-32 rounded bg-slate-800" />
            </div>
          ))
        ) : items.length === 0 ? (
          <div className="xl:col-span-3 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5 text-sm text-text-muted">
            No guided workstreams yet. As telemetry and findings stabilize, SentinelGrid will promote
            the highest-leverage fixes here.
          </div>
        ) : (
          items.map((recommendation) => {
            const primaryAction = getPrimaryRecommendationAction(recommendation);
            const primaryHref = primaryAction ? getRecommendationActionHref(primaryAction) : null;
            const detailHref = getRecommendationHref(recommendation);
            const findingClass = formatRecommendationClass(recommendation.finding_class);

            return (
              <div
                key={recommendation.id}
                className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={clsx(
                        'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                        priorityClasses(recommendation.priority)
                      )}
                    >
                      {recommendation.priority}
                    </span>
                    <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
                      {recommendation.category || 'security'}
                    </span>
                  </div>
                  <span className="text-xs text-text-muted">
                    ~{recommendation.estimated_time_minutes} min
                  </span>
                </div>

                {findingClass && (
                  <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                    {findingClass}
                  </p>
                )}

                <h3 className="mt-2 text-lg font-semibold text-text-main">{recommendation.title}</h3>
                <p className="mt-2 text-sm text-text-muted">{recommendation.description}</p>

                {recommendation.remediation && (
                  <div className="mt-4 rounded-xl border border-primary/10 bg-slate-950/50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                          Guided path
                        </p>
                        <p className="mt-1 text-sm font-semibold text-text-main">
                          {recommendation.remediation.title}
                        </p>
                      </div>
                      <span className="rounded-full border border-primary/20 px-2.5 py-1 text-[11px] text-text-muted">
                        Owner: {recommendation.remediation.owner}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-text-muted">{recommendation.remediation.why_now}</p>
                    {recommendation.remediation.steps[0] && (
                      <div className="mt-3 rounded-lg border border-primary/5 bg-slate-950/60 p-3">
                        <p className="text-sm font-medium text-text-main">
                          Start with: {recommendation.remediation.steps[0].title}
                        </p>
                        <p className="mt-1 text-sm text-text-muted">
                          {recommendation.remediation.steps[0].description}
                        </p>
                      </div>
                    )}
                  </div>
                )}

                <div className="mt-5 flex flex-wrap gap-2">
                  {primaryHref ? (
                    <Link
                      href={primaryHref}
                      className="inline-flex min-h-[42px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110"
                    >
                      {primaryAction?.label || 'Take action'}
                    </Link>
                  ) : null}
                  <Link
                    href={detailHref}
                    className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                  >
                    Open details
                  </Link>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
