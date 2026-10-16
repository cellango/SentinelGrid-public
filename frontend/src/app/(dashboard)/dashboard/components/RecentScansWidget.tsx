import useSWR from 'swr';
import { apiClient } from '@/lib/api/client';

type Scan = {
  id: string;
  scanner_id?: string;
  scan_type?: string;
  target_ref?: string;
  status: string;
  updated_at?: string;
  artifact_url?: string;
  artifact_signed_url?: string;
};

const fetcher = async (limit: number) => {
  // Use apiClient so auth headers (Bearer, tenant) are injected
  const res = await apiClient.get<Scan[]>('/orchestrator/scans/status', { params: { limit } });
  return res.data;
};

function statusBadge(status: string) {
  if (status === 'completed') return 'bg-emerald-500/20 text-emerald-200';
  if (status === 'running') return 'bg-amber-500/20 text-amber-200';
  if (status === 'failed') return 'bg-rose-500/20 text-rose-200';
  return 'bg-slate-700 text-slate-200';
}

export function RecentScansWidget() {
  // Hit the gateway proxy so we respect auth/tenant filtering
  const { data, error, isLoading } = useSWR<Scan[]>('scans-status-5', () => fetcher(5), {
    refreshInterval: 10000,
  });

  return (
    <div className="rounded-lg border border-slate-800/60 bg-slate-900/60 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-100">Recent Scans</p>
          <p className="text-xs text-slate-400">Across cloud, git, and app targets</p>
        </div>
        <a href="/dashboard/scans" className="text-xs text-primary hover:underline">
          View all
        </a>
      </div>

      {error && (
        <p className="text-xs text-amber-300">
          {error.message?.includes('429') ? 'Throttled. Retry shortly.' : 'Unable to load scans.'}
        </p>
      )}
      {isLoading && !data && <p className="text-xs text-slate-400">Loading…</p>}
      {data && data.length === 0 && <p className="text-xs text-slate-400">No scans yet.</p>}

      {data && data.length > 0 && (
        <div className="space-y-2">
          {data.map((scan) => (
            <div key={scan.id} className="flex items-center justify-between rounded-md border border-slate-800/60 bg-slate-900/80 px-3 py-2">
              <div className="flex flex-col">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-1 rounded-full text-[10px] ${statusBadge(scan.status)}`}>{scan.status}</span>
                  <span className="text-xs text-slate-300">{scan.scan_type || scan.scanner_id || 'auto'}</span>
                </div>
                <span className="text-xs text-slate-400">{scan.target_ref || 'No target provided'}</span>
              </div>
              <div className="flex flex-col items-end text-right">
                <span className="text-[11px] text-slate-400">
                  {scan.updated_at ? new Date(scan.updated_at).toLocaleTimeString() : '—'}
                </span>
                {(scan.artifact_signed_url || scan.artifact_url) && (
                  <a
                    href={scan.artifact_signed_url || scan.artifact_url}
                    className="text-[11px] text-primary hover:underline"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Artifact
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
