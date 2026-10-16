'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { NowQueueResponse, NowQueueItem } from '@/lib/api/dashboard';
import { formatStoryDomainLabel } from '@/lib/security/story';
import AITransparencyPanel from '@/components/ai/AITransparencyPanel';
import StorySummaryInline from '@/components/operator/StorySummaryInline';
import { useAuth } from '@/lib/providers/AuthProvider';
import { recordAIFeedback } from '@/lib/api/ai-feedback';

interface NowQueuePanelProps {
  queue?: NowQueueResponse;
  isLoading?: boolean;
  error?: string | null;
}

function priorityClasses(priority: NowQueueItem['priority']) {
  switch (priority) {
    case 'critical':
      return 'border-red-500/30 bg-red-500/15 text-red-200';
    case 'high':
      return 'border-orange-500/30 bg-orange-500/15 text-orange-200';
    case 'medium':
      return 'border-amber-500/30 bg-amber-500/15 text-amber-200';
    default:
      return 'border-sky-500/30 bg-sky-500/15 text-sky-200';
  }
}

function itemTypeLabel(itemType: NowQueueItem['item_type']) {
  if (itemType === 'incident') return 'Incident';
  if (itemType === 'alert') return 'Alert';
  return 'Recommendation';
}

export default function NowQueuePanel({ queue, isLoading, error }: NowQueuePanelProps) {
  const { tenantId, user } = useAuth();
  const items = queue?.items || [];
  const summary = queue?.summary;

  const handleQueueFeedback = async (item: NowQueueItem) => {
    if (!tenantId) {
      throw new Error('Tenant context is unavailable for AI feedback.');
    }

    await recordAIFeedback({
      tenantId,
      actorUserId: user?.id,
      actorEmail: user?.email,
      actorRoles: user?.roles,
      action:
        item.item_type === 'recommendation'
          ? 'ai_recommendation_disagreed'
          : 'ai_priority_disagreed',
      resourceType: item.item_type,
      resourceId: item.id,
      resourceName: item.title,
      metadata: {
        queue_surface: 'dashboard_now_queue',
        item_priority: item.priority,
        action_label: item.action_label,
        source_label: item.source_label,
        status: item.status || null,
        owner: item.owner || null,
        domains: item.domains,
      },
    });
  };

  return (
    <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Now</p>
          <h2 className="mt-1 text-2xl font-semibold text-text-main">One operator queue</h2>
          <p className="mt-2 max-w-2xl text-sm text-text-muted">
            Prioritized work across incidents, detections, identity, cloud, endpoint, and AI.
          </p>
        </div>
        {queue?.generated_at && (
          <div className="text-xs text-text-muted">
            Updated {new Date(queue.generated_at).toLocaleString()}
          </div>
        )}
      </div>

      {summary && (
        <div className="mt-5 grid gap-3 md:grid-cols-4" aria-live="polite" aria-atomic="true">
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.5)] p-4">
            <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Urgent</div>
            <div className="mt-2 text-2xl font-semibold text-text-main">{summary.urgent_items}</div>
            <div className="mt-1 text-xs text-text-muted">Critical and high-priority items</div>
          </div>
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.5)] p-4">
            <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Incidents</div>
            <div className="mt-2 text-2xl font-semibold text-text-main">{summary.incidents}</div>
            <div className="mt-1 text-xs text-text-muted">Active incident stories</div>
          </div>
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.5)] p-4">
            <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Alerts</div>
            <div className="mt-2 text-2xl font-semibold text-text-main">{summary.alerts}</div>
            <div className="mt-1 text-xs text-text-muted">Untriaged or active detections</div>
          </div>
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.5)] p-4">
            <div className="text-xs uppercase tracking-[0.14em] text-text-muted">Coverage</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(summary.domains || []).slice(0, 3).map((domainItem) => (
                <span
                  key={domainItem.domain}
                  className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] text-primary"
                >
                  {formatStoryDomainLabel(domainItem.domain)} {domainItem.count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 space-y-3">
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              <div
                key={index}
                className="animate-pulse rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5"
              >
                <div className="h-4 w-32 rounded bg-slate-800" />
                <div className="mt-3 h-5 w-3/4 rounded bg-slate-800" />
                <div className="mt-2 h-4 w-full rounded bg-slate-800" />
                <div className="mt-2 h-4 w-2/3 rounded bg-slate-800" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
            Failed to load the Now queue. {error}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-6 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
              <svg className="h-6 w-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-text-main">Queue is clear</p>
            <p className="mt-1 text-sm text-text-muted">
              Connect identity, cloud, and endpoint data to start prioritizing operator work.
            </p>
            <a href="/dashboard/posture" className="mt-3 inline-flex items-center gap-1 text-sm text-primary hover:underline">
              Review coverage gaps
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
            </a>
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5"
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={clsx(
                        'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                        priorityClasses(item.priority)
                      )}
                    >
                      {item.priority}
                    </span>
                    <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
                      {itemTypeLabel(item.item_type)}
                    </span>
                    {(item.domains || []).map((domain) => (
                      <span
                        key={`${item.id}-${domain}`}
                        className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] text-primary"
                      >
                        {formatStoryDomainLabel(domain)}
                      </span>
                    ))}
                  </div>

                  <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
                    <h3 className="text-lg font-semibold text-text-main">{item.title}</h3>
                    {item.status && (
                      <span className="text-xs text-text-muted">Status: {item.status.replace(/_/g, ' ')}</span>
                    )}
                    {item.owner && <span className="text-xs text-text-muted">Owner: {item.owner}</span>}
                    {item.updated_at && (
                      <span className="text-xs text-text-muted">
                        Updated {new Date(item.updated_at).toLocaleString()}
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm text-text-main">{item.summary}</p>

                  <AITransparencyPanel
                    embedded
                    compact
                    className="mt-3"
                    eyebrow="AI priority context"
                    title={
                      item.item_type === 'recommendation'
                        ? 'Why SentinelGrid suggested this next step'
                        : 'Why this item is in the operator queue'
                    }
                    summary={`Recommended action: ${item.action_label}`}
                    why={item.why_now}
                    disagreeLabel={
                      item.item_type === 'recommendation'
                        ? 'Disagree with recommendation'
                        : 'Disagree with priority'
                    }
                    onDisagree={() => handleQueueFeedback(item)}
                  />

                  <StorySummaryInline
                    summary={item.story_summary}
                    domains={item.domains}
                    className="mt-3"
                  />

                  <div className="mt-3 flex flex-wrap gap-2">
                    {(item.entities || []).slice(0, 3).map((entity) => (
                      <span
                        key={`${item.id}-${entity.type}-${entity.id}`}
                        className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted"
                      >
                        {entity.label}
                      </span>
                    ))}
                    {(item.evidence || []).length > 0 && (
                      <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                        {(item.evidence || []).length} evidence item{(item.evidence || []).length === 1 ? '' : 's'}
                      </span>
                    )}
                    {item.estimated_time_minutes && (
                      <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                        ~{item.estimated_time_minutes} min
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2 lg:min-w-[180px] lg:items-end">
                  <Link
                    href={item.action_href}
                    className="inline-flex min-h-[42px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110"
                  >
                    {item.action_label}
                  </Link>
                  {item.href !== item.action_href && (
                    <Link
                      href={item.href}
                      className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                    >
                      Open details
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
