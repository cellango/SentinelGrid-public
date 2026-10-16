'use client';

import Link from 'next/link';
import type { NowQueueResponse } from '@/lib/api/dashboard';
import {
  buildAttackPathsFromStory,
  buildQueueItemGraphHref,
} from '@/lib/security/graph-context';

interface SecurityGraphPreviewCardProps {
  queue?: NowQueueResponse;
  isLoading?: boolean;
}

export default function SecurityGraphPreviewCard({
  queue,
  isLoading = false,
}: SecurityGraphPreviewCardProps) {
  const focusItem =
    queue?.items.find(
      (item) =>
        (item.item_type === 'alert' || item.item_type === 'incident') &&
        ((item.entities || []).length > 0 || (item.evidence || []).length > 0)
    ) || queue?.items[0];

  const previewPaths = focusItem
    ? buildAttackPathsFromStory({
        title: focusItem.title,
        severity: focusItem.priority,
        summary: focusItem.summary,
        domains: focusItem.domains,
        entities: focusItem.entities,
        evidence: focusItem.evidence,
      })
    : [];
  const previewPath = previewPaths[0] || null;
  const previewNodes = previewPath?.entities.filter((entity) => entity.type !== 'control').slice(0, 5) || [];
  const hasLivePreview = Boolean(focusItem && previewPath);
  const graphHref = hasLivePreview ? buildQueueItemGraphHref(focusItem) : '/dashboard';
  const graphLabel = hasLivePreview ? 'Open graph' : 'Open queue';

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-surface-card-border bg-surface-card p-5">
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-24 rounded bg-slate-800" />
          <div className="h-5 w-2/3 rounded bg-slate-800" />
          <div className="h-20 rounded-xl bg-slate-900/70" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-surface-card-border bg-surface-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Security Graph</p>
          <h2 className="mt-1 text-lg font-semibold text-text-main">Current blast radius</h2>
          <p className="mt-2 text-sm text-text-muted">
            Move from the top queue item into its attack-path context without leaving the dashboard.
          </p>
        </div>
        <Link
          href={graphHref}
          className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-primary/30 px-3 py-2 text-sm font-medium text-text-main hover:border-primary/50"
        >
          {graphLabel}
        </Link>
      </div>

      {!focusItem || !previewPath ? (
        <div className="mt-5 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4 text-sm text-text-muted">
          No live attack-path context is available yet. Open the queue from a real alert or incident once linked entities and evidence exist.
        </div>
      ) : (
        <div className="mt-5 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-primary">
              {focusItem.priority}
            </span>
            <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
              {focusItem.item_type}
            </span>
          </div>

          <h3 className="mt-3 text-base font-semibold text-text-main">{previewPath.title}</h3>
          <p className="mt-2 text-sm text-text-muted">{focusItem.summary}</p>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {previewNodes.map((entity, index) => (
              <div key={entity.id} className="flex items-center gap-2">
                <span className="rounded-full border border-[rgba(148,163,184,0.18)] bg-slate-950/45 px-3 py-1.5 text-xs text-text-main">
                  {entity.label}
                </span>
                {index < previewNodes.length - 1 && (
                  <span className="text-xs text-text-muted">→</span>
                )}
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-wrap gap-2 text-xs text-text-muted">
            <span>{previewPath.entities.length} graph node{previewPath.entities.length === 1 ? '' : 's'}</span>
            <span>•</span>
            <span>{focusItem.entities.length} linked entit{focusItem.entities.length === 1 ? 'y' : 'ies'}</span>
            <span>•</span>
            <span>{focusItem.evidence.length} evidence item{focusItem.evidence.length === 1 ? '' : 's'}</span>
          </div>
        </div>
      )}
    </div>
  );
}
