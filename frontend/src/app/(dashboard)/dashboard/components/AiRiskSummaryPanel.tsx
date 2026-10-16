'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { AiRiskSummary } from '@/lib/api/dashboard';

interface AiRiskSummaryPanelProps {
  summary?: AiRiskSummary;
  isLoading?: boolean;
}

function statusClasses(status: AiRiskSummary['health_status']) {
  switch (status) {
    case 'critical':
      return 'border-rose-500/40 bg-rose-500/15 text-rose-200';
    case 'warning':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-200';
    default:
      return 'border-sky-500/40 bg-sky-500/15 text-sky-200';
  }
}

function severityClasses(severity?: string | null) {
  switch ((severity || '').toLowerCase()) {
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

export default function AiRiskSummaryPanel({
  summary,
  isLoading = false,
}: AiRiskSummaryPanelProps) {
  if (isLoading) {
    return (
      <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-24 rounded bg-slate-800" />
          <div className="h-6 w-1/2 rounded bg-slate-800" />
          <div className="h-4 w-full rounded bg-slate-800" />
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-20 rounded-xl bg-slate-900/70" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (!summary || summary.health_status === 'inactive') {
    return (
      <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
        <div className="flex flex-col gap-2">
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">AI Risk</p>
          <h2 className="text-xl font-semibold text-text-main">Bring AI runtime risk into the main queue</h2>
          <p className="text-sm text-text-muted">
            No elevated AI findings are active in the main operator workflow yet. Connect AI Shield to
            turn prompt injection, data exposure, and guardrail violations into real alerts and incidents.
          </p>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/onboarding"
            className="inline-flex min-h-[42px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110"
          >
            Open onboarding
          </Link>
          <Link
            href="/dashboard/compliance/ai-activity"
            className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
          >
            Review AI activity
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">AI Risk</p>
          <h2 className="mt-1 text-xl font-semibold text-text-main">AI runtime risk in the operator plane</h2>
          <p className="mt-2 max-w-2xl text-sm text-text-muted">{summary.summary}</p>
        </div>
        <span
          className={clsx(
            'inline-flex w-fit rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
            statusClasses(summary.health_status)
          )}
        >
          {summary.health_status}
        </span>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Open AI alerts</div>
          <div className="mt-2 text-2xl font-semibold text-text-main">{summary.open_alerts}</div>
          <div className="mt-1 text-xs text-text-muted">Risky AI findings in the last {summary.lookback_days} days</div>
        </div>
        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Active incidents</div>
          <div className="mt-2 text-2xl font-semibold text-text-main">{summary.active_incidents}</div>
          <div className="mt-1 text-xs text-text-muted">AI cases already promoted into incident workflow</div>
        </div>
        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Affected apps</div>
          <div className="mt-2 text-2xl font-semibold text-text-main">{summary.affected_apps}</div>
          <div className="mt-1 text-xs text-text-muted">AI apps with elevated runtime risk</div>
        </div>
        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Affected users</div>
          <div className="mt-2 text-2xl font-semibold text-text-main">{summary.affected_users}</div>
          <div className="mt-1 text-xs text-text-muted">Distinct actors tied to risky AI paths</div>
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.25fr),minmax(280px,0.95fr)]">
        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-text-muted">Priority pattern mix</p>
              <h3 className="mt-2 text-lg font-semibold text-text-main">Where AI risk is concentrating</h3>
            </div>
            {summary.top_risk ? (
              <span
                className={clsx(
                  'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                  severityClasses(summary.top_risk.severity)
                )}
              >
                {summary.top_risk.severity}
              </span>
            ) : null}
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-[rgba(148,163,184,0.14)] bg-slate-950/45 p-3">
              <div className="text-xs uppercase tracking-[0.12em] text-text-muted">Prompt injection</div>
              <div className="mt-2 text-xl font-semibold text-text-main">{summary.prompt_injection_alerts}</div>
            </div>
            <div className="rounded-lg border border-[rgba(148,163,184,0.14)] bg-slate-950/45 p-3">
              <div className="text-xs uppercase tracking-[0.12em] text-text-muted">Data exposure</div>
              <div className="mt-2 text-xl font-semibold text-text-main">{summary.data_exposure_alerts}</div>
            </div>
            <div className="rounded-lg border border-[rgba(148,163,184,0.14)] bg-slate-950/45 p-3">
              <div className="text-xs uppercase tracking-[0.12em] text-text-muted">Policy violations</div>
              <div className="mt-2 text-xl font-semibold text-text-main">{summary.policy_violation_alerts}</div>
            </div>
          </div>

          {summary.top_risk ? (
            <div className="mt-4 rounded-xl border border-primary/15 bg-slate-950/50 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-primary">Top AI case</p>
              <h4 className="mt-2 text-base font-semibold text-text-main">{summary.top_risk.title}</h4>
              <p className="mt-2 text-sm text-text-muted">{summary.top_risk.summary}</p>
              <Link
                href={summary.top_risk.href}
                className="mt-4 inline-flex min-h-[40px] items-center justify-center rounded-lg border border-primary/30 px-4 py-2 text-sm text-text-main hover:border-primary/50"
              >
                Open {summary.top_risk.item_type}
              </Link>
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
            <p className="text-xs uppercase tracking-[0.14em] text-text-muted">Impacted apps</p>
            <div className="mt-4 space-y-3">
              {summary.top_applications.length === 0 ? (
                <p className="text-sm text-text-muted">No high-signal AI applications yet.</p>
              ) : (
                summary.top_applications.map((app) => (
                  <div
                    key={app.app_id}
                    className="rounded-lg border border-[rgba(148,163,184,0.14)] bg-slate-950/45 p-3"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-text-main">{app.label}</p>
                        <p className="mt-1 text-xs text-text-muted">
                          {app.active_incidents} incident{app.active_incidents === 1 ? '' : 's'} · {app.open_alerts} open alert{app.open_alerts === 1 ? '' : 's'}
                        </p>
                      </div>
                      <span
                        className={clsx(
                          'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                          severityClasses(app.highest_severity)
                        )}
                      >
                        {app.highest_severity}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
            <p className="text-xs uppercase tracking-[0.14em] text-text-muted">Priority actions</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {summary.priority_actions.map((action) => (
                <Link
                  key={action.href + action.label}
                  href={action.href}
                  className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                >
                  {action.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
