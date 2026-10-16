'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { loadSampleLogs, searchLogsSimple, type LogEvent } from '@/lib/api/siem';
import { toast } from 'react-hot-toast';

type LogGroup = {
  key: string;
  label: string;
  query: string;
  hint?: string;
};

const LOG_GROUPS: LogGroup[] = [
  { key: 'all', label: 'All', query: '*' },
  { key: 'identity', label: 'Identity/Auth', query: 'event.category:authentication OR identity:*', hint: 'Keycloak/SSO/MFA' },
  { key: 'endpoint', label: 'Endpoint/EDR', query: 'event.category:(process OR file) OR host.id:*', hint: 'Processes, files, EDR detections' },
  { key: 'network', label: 'Network/Flow', query: 'event.category:network OR network:*', hint: 'Flow logs, firewall, proxy' },
  { key: 'cloud', label: 'Cloud Audit', query: 'cloud.provider:* OR event.category:iam', hint: 'CloudTrail/activity logs' },
  { key: 'application', label: 'Application/API', query: 'event.category:application OR api:* OR http.*', hint: 'App/API gateway' },
  { key: 'email', label: 'Email/Messaging', query: 'event.category:(email OR message)', hint: 'Mail gateway, collaboration' },
  { key: 'git', label: 'Code/Config', query: 'repo:* OR git:* OR finding:*', hint: 'Git pushes, findings' },
];

type EdrFilter = { key: string; label: string; clause?: string; hint?: string };

const EDR_FILTERS: EdrFilter[] = [
  { key: 'all', label: 'All telemetry', clause: undefined },
  { key: 'wazuh', label: 'Baseline sensor', clause: 'edr_source:"sentinelguard-wazuh"' },
  { key: 'openedr', label: 'Behavioral telemetry', clause: 'edr_source:"sentinelguard-openedr"' },
  { key: 'velociraptor', label: 'Hunt/collections', clause: 'edr_source:"sentinelguard-velociraptor"' },
  { key: 'sidecar', label: 'Sidecar events only', clause: 'sidecar_enabled:true' },
];

const EDR_SOURCE_LABELS: Record<string, string> = {
  'sentinelguard-wazuh': 'Baseline sensor',
  'sentinelguard-openedr': 'Behavioral telemetry',
  'sentinelguard-velociraptor': 'Hunt/collections',
};

function formatTimestamp(ts: string) {
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

function eventLabel(log: LogEvent) {
  const cat = log.event?.category;
  const type = log.event?.type;
  const action = log.event?.action;
  const catStr = Array.isArray(cat) ? cat.join(', ') : cat;
  const typeStr = Array.isArray(type) ? type.join(', ') : type;
  return action || typeStr || catStr || 'event';
}

export default function LogManagementPage() {
  const [search, setSearch] = useState('*');
  const [group, setGroup] = useState<LogGroup>(LOG_GROUPS[0]);
  const [edrFilter, setEdrFilter] = useState<EdrFilter>(EDR_FILTERS[0]);

  const query = useMemo(() => {
    const parts = [group.query];
    if (search && search.trim() !== '' && search.trim() !== '*') {
      parts.push(`(${search})`);
    }
    if (edrFilter.clause) {
      parts.push(edrFilter.clause);
    }
    return parts.filter(Boolean).join(' AND ');
  }, [group, search, edrFilter]);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['logs', query],
    queryFn: () => searchLogsSimple({ q: query, limit: 100, offset: 0 }),
  });

  const hits = data?.hits || [];

  const handleLoadSamples = async () => {
    try {
      await loadSampleLogs('auth');
      await loadSampleLogs('endpoint');
      await loadSampleLogs('network');
      await loadSampleLogs('cloud');
      toast.success('Sample logs ingested');
      refetch();
    } catch (e: any) {
      toast.error(e?.message || 'Failed to load sample logs');
    }
  };

  return (
    <div className="min-h-[60vh] px-6 py-8">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <p className="text-sm uppercase tracking-wide text-text-muted">Log Management</p>
          <h1 className="text-2xl font-semibold text-text-main">Explore logs</h1>
          <p className="text-sm text-text-muted">Filter by category and search across OpenSearch-backed logs.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleLoadSamples}
            className="px-3 py-2 rounded-lg border border-slate-700 text-sm text-text-main hover:border-primary/70"
          >
            Load sample logs
          </button>
          <button
            onClick={() => refetch()}
            className="px-3 py-2 rounded-lg bg-primary text-white text-sm hover:bg-primary/80 disabled:opacity-60"
            disabled={isFetching}
          >
            {isFetching ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-4 mb-4">
        <div className="flex flex-wrap gap-2 mb-3 items-center">
          <span className="text-xs uppercase tracking-wide text-text-muted pr-2">Categories</span>
          {LOG_GROUPS.map((g) => (
            <button
              key={g.key}
              onClick={() => setGroup(g)}
              className={`px-3 py-1.5 rounded-full text-sm border ${
                group.key === g.key
                  ? 'bg-primary text-white border-primary'
                  : 'bg-slate-800 text-text-muted border-slate-700 hover:border-primary/50 hover:text-text-main'
              }`}
              title={g.hint}
            >
              {g.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 mb-3 items-center">
          <span className="text-xs uppercase tracking-wide text-text-muted pr-2">Endpoint telemetry</span>
          {EDR_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setEdrFilter(f)}
              className={`px-3 py-1.5 rounded-full text-sm border ${
                edrFilter.key === f.key
                  ? 'bg-primary text-white border-primary'
                  : 'bg-slate-800 text-text-muted border-slate-700 hover:border-primary/50 hover:text-text-main'
              }`}
              title={f.hint}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <input
            className="w-full px-3 py-2 rounded-lg bg-slate-900 text-text-main border border-slate-700 focus:outline-none focus:ring-1 focus:ring-primary/70 focus:border-primary/50"
            placeholder="Search logs (e.g., user.email:admin OR destination.ip:203.0.113.10 OR edr_source:sentinelguard-openedr)"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && refetch()}
          />
          <button
            onClick={() => refetch()}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm hover:bg-primary/80 disabled:opacity-60"
            disabled={isFetching}
          >
            Search
          </button>
        </div>
      </div>

      <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-4">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-sm text-text-muted">Results</p>
            <h3 className="text-lg font-semibold text-text-main">
              {isLoading ? 'Loading…' : `${hits.length} log${hits.length === 1 ? '' : 's'}`}
            </h3>
          </div>
          {data?.took && <span className="text-xs text-text-muted">took {data.took} ms</span>}
        </div>

        {isLoading ? (
          <div className="py-12 text-center text-text-muted">Loading logs…</div>
        ) : hits.length === 0 ? (
          <div className="py-12 text-center text-text-muted">No logs found. Try another filter or load sample logs.</div>
        ) : (
          <div className="space-y-3">
            {hits.map((log, idx) => (
              <div
                key={log.id || idx}
                className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 flex flex-col gap-2"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-sm flex-wrap">
                    <span className="px-2 py-1 rounded-full text-[11px] bg-slate-800 text-text-muted border border-slate-700">
                      {eventLabel(log)}
                    </span>
                    {log.event?.outcome && (
                      <span
                        className={`px-2 py-1 rounded-full text-[11px] border ${
                          log.event.outcome === 'success'
                            ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200'
                            : 'bg-amber-500/10 border-amber-500/40 text-amber-200'
                        }`}
                      >
                        {log.event.outcome}
                      </span>
                    )}
                    {log.edr_source && (
                      <span className="px-2 py-1 rounded-full text-[11px] border border-slate-700 bg-slate-800 text-text-muted">
                        {EDR_SOURCE_LABELS[log.edr_source] || log.edr_source}
                      </span>
                    )}
                    {log.sidecar_enabled !== undefined && (
                      <span className="px-2 py-1 rounded-full text-[11px] border border-slate-700 bg-slate-800 text-text-muted">
                        sidecar {log.sidecar_enabled ? 'on' : 'off'}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-text-muted">{formatTimestamp((log as any)['@timestamp'] as string)}</div>
                </div>
                <div className="grid md:grid-cols-4 gap-3 text-sm text-text-muted">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-text-muted">Category</div>
                    <div className="text-text-main">
                      {(Array.isArray(log.event?.category) ? log.event?.category?.join(', ') : log.event?.category) ||
                        log.event_type ||
                        '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-text-muted">Action</div>
                    <div className="text-text-main">
                      {log.event?.action || log.action || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-text-muted">User</div>
                    <div className="text-text-main">
                      {log.user?.email || log.user?.name || log.user?.id || '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wide text-text-muted">Source</div>
                    <div className="text-text-main">
                      {log.source?.ip || log.source?.address || log.host?.hostname || '—'}
                    </div>
                  </div>
                </div>
                <details className="text-xs text-text-muted">
                  <summary className="cursor-pointer text-text-main">View raw</summary>
                  <pre className="mt-2 max-h-60 overflow-auto rounded bg-slate-950/80 p-3 text-xs text-slate-200 border border-slate-800">
                    {JSON.stringify(log, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
