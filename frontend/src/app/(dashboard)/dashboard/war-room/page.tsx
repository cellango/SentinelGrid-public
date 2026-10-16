/**
 * War Room Page
 * Unified priority queue for all security items requiring attention.
 */

'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import EmptyState from '@/components/ui/EmptyState';
import SlideOverPanel from '@/components/ui/SlideOverPanel';
import WarRoomQueue from '@/components/war-room/WarRoomQueue';
import {
  getNowQueue,
  getNowQueueStreamUrl,
  normalizeNowQueueResponse,
  type NowQueueItem,
  type NowQueueResponse,
} from '@/lib/api/dashboard';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useEventSourceStream } from '@/lib/realtime/useEventSourceStream';

export default function WarRoomPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { tenantId } = useAuth();
  const [selectedItem, setSelectedItem] = useState<NowQueueItem | null>(null);

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

  const { data } = useQuery<NowQueueResponse>({
    queryKey: ['now-queue', tenantId],
    queryFn: () => getNowQueue(tenantId!),
    enabled: !!tenantId,
    retry: false,
    refetchInterval:
      nowQueueStream.status === 'error' || nowQueueStream.status === 'unsupported'
        ? 60 * 1000
        : false,
  });

  const items = data?.items || [];
  const summary = data?.summary;

  return (
    <div className="px-6 py-6 max-w-5xl mx-auto">
      <Breadcrumbs />
      <div className="mt-2 mb-6">
        <h1 className="text-xl font-bold text-text-main">War Room</h1>
        <p className="text-sm text-text-muted mt-0.5">
          Your single prioritized queue — address the most urgent items first.
        </p>
      </div>

      {items.length > 0 ? (
        <WarRoomQueue
          items={items}
          summary={summary}
          onItemClick={(item) => setSelectedItem(item)}
          onActionClick={(item) => router.push(item.action_href)}
        />
      ) : (
        <div className="rounded-2xl border border-border-faint bg-surface-card p-6">
          <EmptyState
            variant="no-data"
            title="No live queue items yet"
            description="War Room only shows real incidents, alerts, and recommendations from connected systems. It no longer backfills demo queue items when tenant data is empty."
            action={{
              label: 'Finish setup',
              onClick: () => router.push('/dashboard/welcome'),
            }}
            secondaryAction={{
              label: 'Review alert queue',
              onClick: () => router.push('/dashboard/alerts'),
            }}
          />
        </div>
      )}

      <SlideOverPanel
        open={!!selectedItem}
        onClose={() => setSelectedItem(null)}
        title={selectedItem?.title || ''}
        subtitle={selectedItem ? `${selectedItem.priority.toUpperCase()} ${selectedItem.item_type}` : ''}
        width="lg"
        footer={
          selectedItem && (
            <div className="flex items-center justify-between">
              <button
                onClick={() => router.push(selectedItem.href)}
                className="px-4 py-2 text-sm font-medium text-text-main bg-surface-hover border border-border-faint rounded-lg hover:bg-surface-input transition-colors min-h-[44px]"
              >
                Open Full View
              </button>
              <button
                onClick={() => router.push(selectedItem.action_href)}
                className="px-4 py-2 text-sm font-medium text-slate-950 bg-primary rounded-lg hover:brightness-110 transition-all min-h-[44px]"
              >
                {selectedItem.action_label || 'Take Action'}
              </button>
            </div>
          )
        }
      >
        {selectedItem && (
          <div className="space-y-6">
            <div>
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Summary</h4>
              <p className="text-sm text-text-main">{selectedItem.summary}</p>
            </div>

            {selectedItem.why_now && (
              <div className="p-3 rounded-lg bg-primary/5 border border-primary/20">
                <h4 className="text-xs font-semibold text-primary mb-1 flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Why Now
                </h4>
                <p className="text-sm text-text-main">{selectedItem.why_now}</p>
              </div>
            )}

            <div>
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Details</h4>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-text-muted">Type</dt>
                  <dd className="text-text-main capitalize">{selectedItem.item_type}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-text-muted">Priority</dt>
                  <dd className="text-text-main capitalize">{selectedItem.priority}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-text-muted">Source</dt>
                  <dd className="text-text-main">{selectedItem.source_label}</dd>
                </div>
                {selectedItem.owner && (
                  <div className="flex justify-between">
                    <dt className="text-text-muted">Owner</dt>
                    <dd className="text-text-main">{selectedItem.owner}</dd>
                  </div>
                )}
                {selectedItem.estimated_time_minutes && (
                  <div className="flex justify-between">
                    <dt className="text-text-muted">Est. Time</dt>
                    <dd className="text-text-main">{selectedItem.estimated_time_minutes} minutes</dd>
                  </div>
                )}
                {selectedItem.domains.length > 0 && (
                  <div className="flex justify-between">
                    <dt className="text-text-muted">Domains</dt>
                    <dd className="flex gap-1.5">
                      {selectedItem.domains.map((domain) => (
                        <span key={domain} className="px-2 py-0.5 text-[10px] rounded-full bg-surface-hover text-text-main border border-border-faint capitalize">
                          {domain}
                        </span>
                      ))}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        )}
      </SlideOverPanel>
    </div>
  );
}
