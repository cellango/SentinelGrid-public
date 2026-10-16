'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import {
  ChevronDownIcon,
  ChevronUpIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import {
  getNowQueue,
  getNowQueueStreamUrl,
  normalizeNowQueueResponse,
  type NowQueueResponse,
  type NowQueueItem,
} from '@/lib/api/dashboard';
import AITransparencyPanel from '@/components/ai/AITransparencyPanel';
import { formatStoryDomainLabel } from '@/lib/security/story';
import { useAuth } from '@/lib/providers/AuthProvider';
import { recordAIFeedback } from '@/lib/api/ai-feedback';
import { useEventSourceStream } from '@/lib/realtime/useEventSourceStream';

interface NowQueueDockProps {
  tenantId?: string;
}

type DockState = 'expanded' | 'collapsed';

const STORAGE_KEY = 'sg_now_queue_dock_state';
const MOBILE_MEDIA_QUERY = '(max-width: 1023px)';

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

export default function NowQueueDock({ tenantId }: NowQueueDockProps) {
  const pathname = usePathname();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [isCompactViewport, setIsCompactViewport] = useState(false);
  const [dockState, setDockState] = useState<DockState>('collapsed');
  const [ready, setReady] = useState(false);

  const nowQueueStream = useEventSourceStream<NowQueueResponse>({
    url: tenantId ? getNowQueueStreamUrl(tenantId) : null,
    enabled: !!tenantId,
    onSnapshot: (payload) => {
      if (!tenantId) {
        return;
      }
      queryClient.setQueryData(['now-queue', tenantId], normalizeNowQueueResponse(payload));
    },
  });

  const {
    data: queue,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['now-queue', tenantId],
    queryFn: () => getNowQueue(tenantId!),
    enabled: !!tenantId,
    refetchInterval:
      nowQueueStream.status === 'error' || nowQueueStream.status === 'unsupported'
        ? 60 * 1000
        : false,
  });

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQuery = window.matchMedia(MOBILE_MEDIA_QUERY);
    const syncViewport = () => setIsCompactViewport(mediaQuery.matches);
    syncViewport();

    const storedState = window.localStorage.getItem(STORAGE_KEY) as DockState | null;
    setDockState(storedState || (mediaQuery.matches ? 'expanded' : 'collapsed'));
    setReady(true);

    mediaQuery.addEventListener('change', syncViewport);
    return () => mediaQuery.removeEventListener('change', syncViewport);
  }, []);

  useEffect(() => {
    if (!ready || typeof window === 'undefined') {
      return;
    }

    window.localStorage.setItem(STORAGE_KEY, dockState);
  }, [dockState, ready]);

  const topItems = useMemo(() => (queue?.items || []).slice(0, 4), [queue?.items]);
  const urgentCount = queue?.summary?.urgent_items || 0;
  const totalCount = queue?.summary?.total_items || 0;
  const dominantDomains = (queue?.summary?.domains || []).slice(0, 2);
  const primaryItem = topItems[0];
  const isExpanded = dockState === 'expanded';

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
        queue_surface: 'shell_now_queue_dock',
        item_priority: item.priority,
        action_label: item.action_label,
        source_label: item.source_label,
        status: item.status || null,
        owner: item.owner || null,
        domains: item.domains,
      },
    });
  };

  if (!ready || !tenantId || pathname === '/dashboard') {
    return null;
  }

  return (
    <div
      className={clsx(
        'fixed inset-x-4 z-40 transition-all duration-200 ease-out lg:inset-x-auto lg:right-6',
        isCompactViewport ? 'bottom-24' : 'bottom-24',
        isExpanded ? 'lg:w-[420px]' : 'lg:w-[360px]'
      )}
      aria-live="polite"
      aria-atomic="true"
    >
      <div
        className={clsx(
          'overflow-hidden rounded-2xl border border-border-strong bg-surface-card shadow-2xl shadow-black/25 backdrop-blur-md',
          isExpanded ? 'max-h-[68vh]' : ''
        )}
      >
        <div className="border-b border-border-faint px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                  Now Queue
                </p>
                {urgentCount > 0 && (
                  <span className="rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold text-primary">
                    {urgentCount} urgent
                  </span>
                )}
              </div>
              <p className="mt-1 text-sm text-text-main">
                {isLoading
                  ? 'Loading operator priorities…'
                  : primaryItem
                    ? primaryItem.title
                    : 'No active queue items right now.'}
              </p>
              <p className="mt-1 text-xs text-text-muted">
                {isLoading
                  ? 'Refreshing incidents, alerts, and recommendations.'
                  : error
                    ? 'Queue refresh failed. You can still open the full dashboard.'
                    : primaryItem
                      ? `${totalCount} item${totalCount === 1 ? '' : 's'} across incidents, alerts, and recommendations.`
                      : 'Connect more data sources to start prioritizing work automatically.'}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Link
                href="/dashboard"
                className="inline-flex min-h-[40px] items-center rounded-lg border border-border-faint px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
              >
                Full queue
              </Link>
              <button
                type="button"
                onClick={() => setDockState(isExpanded ? 'collapsed' : 'expanded')}
                className="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-lg border border-border-faint text-text-main transition-colors hover:border-primary"
                aria-controls="now-queue-dock-body"
                aria-expanded={isExpanded}
                aria-label={isExpanded ? 'Collapse Now queue widget' : 'Expand Now queue widget'}
              >
                {isExpanded ? (
                  <ChevronDownIcon className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <ChevronUpIcon className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {!isExpanded && !isLoading && dominantDomains.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {dominantDomains.map((domain) => (
                <span
                  key={domain.domain}
                  className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] text-primary"
                >
                  {formatStoryDomainLabel(domain.domain)} {domain.count}
                </span>
              ))}
            </div>
          )}
        </div>

        {isExpanded && (
          <div
            id="now-queue-dock-body"
            className="max-h-[calc(68vh-84px)] overflow-y-auto px-4 py-4"
          >
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, index) => (
                  <div
                    key={index}
                    className="animate-pulse rounded-xl border border-border-faint bg-surface-hover p-4"
                  >
                    <div className="h-3 w-24 rounded bg-surface-card-border" />
                    <div className="mt-3 h-4 w-2/3 rounded bg-surface-card-border" />
                    <div className="mt-2 h-3 w-full rounded bg-surface-card-border" />
                  </div>
                ))}
              </div>
            ) : error ? (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
                Failed to load the Now queue. {error instanceof Error ? error.message : 'Try again from the full dashboard.'}
              </div>
            ) : topItems.length === 0 ? (
              <div className="rounded-xl border border-border-faint bg-surface-hover p-4 text-sm text-text-muted">
                No active queue items yet. Open the full dashboard to connect more data sources and review setup progress.
              </div>
            ) : (
              <div className="space-y-3">
                {topItems.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-xl border border-border-faint bg-surface-hover p-4"
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={clsx(
                          'rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em]',
                          priorityClasses(item.priority)
                        )}
                      >
                        {item.priority}
                      </span>
                      <span className="rounded-full border border-border-faint px-2.5 py-1 text-[10px] uppercase tracking-[0.12em] text-text-muted">
                        {itemTypeLabel(item.item_type)}
                      </span>
                      {(item.domains || []).slice(0, 2).map((domain) => (
                        <span
                          key={`${item.id}-${domain}`}
                          className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[10px] text-primary"
                        >
                          {formatStoryDomainLabel(domain)}
                        </span>
                      ))}
                    </div>

                    <div className="mt-3">
                      <p className="text-sm font-semibold text-text-main">{item.title}</p>
                      <p className="mt-1 text-xs text-text-main">{item.summary}</p>
                    </div>

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

                    <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-text-muted">
                      {item.status && <span>Status: {item.status.replace(/_/g, ' ')}</span>}
                      {item.owner && <span>Owner: {item.owner}</span>}
                      {item.estimated_time_minutes && <span>~{item.estimated_time_minutes} min</span>}
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Link
                        href={item.action_href}
                        className="inline-flex min-h-[38px] items-center justify-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-slate-950 transition-all hover:brightness-110"
                      >
                        {item.action_label}
                      </Link>
                      {item.href !== item.action_href && (
                        <Link
                          href={item.href}
                          className="inline-flex min-h-[38px] items-center justify-center rounded-lg border border-border-faint px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
                        >
                          Open details
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {queue?.summary && topItems.length > 0 && (
              <div className="mt-4 rounded-xl border border-primary/20 bg-primary/10 p-4">
                <div className="flex items-start gap-3">
                  <ExclamationTriangleIcon className="mt-0.5 h-4 w-4 text-primary" aria-hidden="true" />
                  <div>
                    <p className="text-sm font-medium text-text-main">
                      {queue.summary.urgent_items} urgent item{queue.summary.urgent_items === 1 ? '' : 's'} need attention first.
                    </p>
                    <p className="mt-1 text-xs text-text-muted">
                      Use the full queue for broader triage, domain coverage, and the complete recommendation list.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
