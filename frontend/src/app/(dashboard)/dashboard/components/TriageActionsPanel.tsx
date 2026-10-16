'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { Alert } from '@/lib/api/siem';
import StorySummaryInline from '@/components/operator/StorySummaryInline';

interface TriageActionsPanelProps {
  alerts?: Alert[];
  isLoading?: boolean;
}

function severityClasses(severity: Alert['severity']) {
  switch (severity) {
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

function statusLabel(status: Alert['status']) {
  return status.replace(/_/g, ' ');
}

function primaryAlertAction(alert: Alert) {
  const playbookId = alert.recommended_playbook_id || alert.recommended_playbook;
  if (playbookId) {
    return {
      href: `/dashboard/playbooks?playbook_id=${encodeURIComponent(playbookId)}`,
      label: 'Run playbook',
    };
  }

  return {
    href: `/dashboard/alerts/${encodeURIComponent(alert.id)}`,
    label: alert.status === 'investigating' ? 'Continue triage' : 'Triage alert',
  };
}

export default function TriageActionsPanel({
  alerts = [],
  isLoading = false,
}: TriageActionsPanelProps) {
  const items = alerts.slice(0, 5);

  return (
    <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Triage</p>
          <h2 className="mt-1 text-xl font-semibold text-text-main">Keep detections moving</h2>
          <p className="mt-2 max-w-2xl text-sm text-text-muted">
            Recent alerts that still need triage, ownership, or a playbook run before they stall.
          </p>
        </div>
        <Link
          href="/dashboard/alerts"
          className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
        >
          View all alerts
        </Link>
      </div>

      <div className="mt-6 space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="animate-pulse rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5"
            >
              <div className="h-4 w-24 rounded bg-slate-800" />
              <div className="mt-3 h-5 w-2/3 rounded bg-slate-800" />
              <div className="mt-2 h-4 w-full rounded bg-slate-800" />
              <div className="mt-2 h-4 w-4/5 rounded bg-slate-800" />
            </div>
          ))
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5 text-sm text-text-muted">
            No recent detections need action right now. As new detections arrive, triage candidates will land here.
          </div>
        ) : (
          items.map((alert) => {
            const action = primaryAlertAction(alert);

            return (
              <div
                key={alert.id}
                className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5"
              >
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={clsx(
                          'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                          severityClasses(alert.severity)
                        )}
                      >
                        {alert.severity}
                      </span>
                      <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
                        {statusLabel(alert.status)}
                      </span>
                      {alert.category && (
                        <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] text-primary">
                          {alert.category}
                        </span>
                      )}
                    </div>

                    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
                      <h3 className="text-lg font-semibold text-text-main">{alert.title}</h3>
                      {alert.assigned_to && (
                        <span className="text-xs text-text-muted">Owner: {alert.assigned_to}</span>
                      )}
                      {alert.updated_at && (
                        <span className="text-xs text-text-muted">
                          Updated {new Date(alert.updated_at).toLocaleString()}
                        </span>
                      )}
                    </div>

                    {alert.description && (
                      <p className="mt-2 text-sm text-text-main">{alert.description}</p>
                    )}

                    <StorySummaryInline
                      summary={alert.story_summary}
                      domains={alert.story_domains}
                      className="mt-3"
                    />

                    <div className="mt-3 flex flex-wrap gap-2">
                      {alert.recommended_playbook && (
                        <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                          Playbook: {alert.recommended_playbook}
                        </span>
                      )}
                      {alert.mitre_tactic && (
                        <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                          Tactic: {alert.mitre_tactic}
                        </span>
                      )}
                      {alert.control_gap && (
                        <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                          Control: {alert.control_gap}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 lg:min-w-[180px] lg:items-end">
                    <Link
                      href={action.href}
                      className="inline-flex min-h-[42px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110"
                    >
                      {action.label}
                    </Link>
                    <Link
                      href={`/dashboard/alerts/${encodeURIComponent(alert.id)}`}
                      className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                    >
                      Open alert
                    </Link>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
