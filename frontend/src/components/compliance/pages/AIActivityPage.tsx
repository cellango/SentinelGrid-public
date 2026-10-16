'use client';

import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline';

export default function AIActivityPage() {
  const [start, setStart] = useState<string>('');
  const [end, setEnd] = useState<string>('');
  const [limit, setLimit] = useState<number>(50);

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['ai-activity', start, end, limit],
    queryFn: () => {
      const params = new URLSearchParams();
      params.append('limit', String(limit));
      if (start) params.append('start_date', start);
      if (end) params.append('end_date', end);
      return fetch(`/api/v1/audit/ai-activity?${params.toString()}`).then((r) => r.json());
    },
  });

  const items = useMemo(() => data?.items || [], [data]);

  const exportCsv = () => {
    if (!items.length) return;
    const rows = items.map((i: any) => ({
      timestamp: i.timestamp,
      action: i.action,
      user: i.user_email || i.user_id || '',
      query: i.query || '',
      model: i.metadata?.model || '',
      latency_ms: i.metadata?.latency_ms || '',
      sources: Array.isArray(i.sources) ? i.sources.length : 0,
    }));
    const header = Object.keys(rows[0] || {});
    const csv = [
      header.join(','),
      ...rows.map((r: Record<string, unknown>) =>
        header.map((h) => JSON.stringify(r[h] ?? '')).join(','),
      ),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'ai-activity.csv');
    link.click();
  };

  return (
    <div className="p-6 space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-text-main">AI Activity</h1>
        <p className="mt-1 text-text-muted">Tenant-scoped AI queries and responses for compliance evidence.</p>
      </div>

      <div className="rounded-lg border border-surface-card-border bg-surface-card p-4 shadow-sm">
        <div className="flex flex-col md:flex-row gap-3 items-start md:items-end">
          <div className="flex-1 space-y-2">
            <label className="text-xs text-text-muted">Start</label>
            <input
              type="datetime-local"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex-1 space-y-2">
            <label className="text-xs text-text-muted">End</label>
            <input
              type="datetime-local"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-text-muted">Limit</label>
            <input
              type="number"
              min={10}
              max={200}
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value, 10))}
              className="w-24 rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => refetch()}
              className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm text-white transition-colors hover:bg-primary/90"
            >
              <FunnelIcon className="h-5 w-5 mr-2" />
              Apply
            </button>
            <button
              onClick={exportCsv}
              disabled={!items.length}
              className="inline-flex items-center rounded-lg border border-border-faint bg-surface-hover px-4 py-2 text-sm text-text-main transition-colors hover:bg-surface-input disabled:opacity-60"
            >
              <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
              Export CSV
            </button>
          </div>
        </div>

        {isLoading && <p className="text-sm text-text-muted">Loading activity…</p>}
        {error && <p className="text-red-600 text-sm">Failed to load activity.</p>}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3" aria-live="polite" aria-atomic="true">
          {items.map((item: any, idx: number) => (
            <div key={idx} className="rounded-lg border border-border-faint bg-surface-hover p-3">
              <div className="mb-1 text-xs text-text-muted">
                {new Date(item.timestamp || item.created_at || Date.now()).toLocaleString()}
              </div>
              <div className="text-sm font-medium text-text-main">
                {item.user_email || item.user_id || 'user'}
              </div>
              <div className="mt-1 text-xs text-text-muted">Query:</div>
              <div className="line-clamp-2 text-sm text-text-main">{item.query || item.prompt || 'N/A'}</div>
              <div className="mt-1 text-xs text-text-muted">Model: {item.metadata?.model || 'n/a'}</div>
              <div className="mt-1 text-xs text-text-muted">Latency: {item.metadata?.latency_ms || 'n/a'} ms</div>
              <div className="mt-2 text-xs text-text-muted">Sources: {item.sources?.length || 0}</div>
            </div>
          ))}
        </div>
        {(!items.length) && !isLoading && (
          <p className="text-sm text-text-muted">No AI activity logged yet.</p>
        )}
      </div>
    </div>
  );
}
