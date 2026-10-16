'use client';

import { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { apiClient } from '@/lib/api/client';

const statusOptions = ['queued', 'running', 'completed', 'failed'];
const ticketOptions = ['with_ticket'];

const typePresets: { id: string; label: string; scanners: string[] }[] = [
  { id: 'vuln', label: 'Vulnerability', scanners: ['trivy', 'zap', 'semgrep', 'gitleaks', 'checkov'] },
  { id: 'cloud', label: 'Cloud', scanners: ['cloud', 'prowler'] },
  { id: 'app', label: 'App', scanners: ['app', 'zap', 'dast'] },
  { id: 'git', label: 'Git / Code', scanners: ['git', 'semgrep', 'gitleaks', 'checkov'] },
  { id: 'endpoint', label: 'Endpoint', scanners: ['endpoint', 'edr', 'osquery'] },
];

const fetcher = async (params: Record<string, any>) => {
  try {
    const res = await apiClient.get<Scan[]>('/orchestrator/scans/status', { params });
    return res.data;
  } catch (err: any) {
    const status = err?.response?.status;
    const e: any = new Error(err?.response?.data?.detail || err?.message || 'Failed to fetch scans');
    e.status = status;
    throw e;
  }
};

type Scan = {
  id: string;
  scanner_id?: string;
  scan_type?: string;
  target_ref?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  started_at?: string;
  finished_at?: string;
  summary?: Record<string, any>;
  artifact_url?: string;
  artifact_signed_url?: string;
  has_fix_groups?: boolean;
  ticket_id?: string;
  ticket_status?: string;
};

export default function ScansPage() {
  const [statusFilters, setStatusFilters] = useState<string[]>([]);
  const [typeFilters, setTypeFilters] = useState<string[]>([]);
  const [ticketFilters, setTicketFilters] = useState<string[]>([]);
  const [fixFilters, setFixFilters] = useState<string[]>([]);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');

  // Mild debounce for search input
  useEffect(() => {
    const t = setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => clearTimeout(t);
  }, [searchInput]);

  const scannersFromTypes = useMemo(() => {
    const set = new Set<string>();
    typeFilters.forEach((id) => {
      const preset = typePresets.find((p) => p.id === id);
      preset?.scanners.forEach((s) => set.add(s));
    });
    return Array.from(set);
  }, [typeFilters]);

  const params = useMemo(() => {
    const p: Record<string, any> = { limit: 50 };
    if (statusFilters.length > 0) p.status = statusFilters.join(',');
    if (scannersFromTypes.length > 0) p.scanner = scannersFromTypes.join(',');
    if (search) p.q = search;
    if (ticketFilters.includes('with_ticket')) p.with_ticket = true;
    if (fixFilters.includes('with_fix')) p.with_fix = true;
    return p;
  }, [statusFilters, scannersFromTypes, search, ticketFilters, fixFilters]);

  // Use the new gateway proxy for scan status
  const { data, error } = useSWR<Scan[]>(['scans-status', params], () => fetcher(params), {
    refreshInterval: 10000,
  });

  const toggleStatus = (value: string) => {
    setStatusFilters((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  };

  const toggleType = (value: string) => {
    setTypeFilters((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  };

  const toggleTicket = (value: string) => {
    setTicketFilters((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  };

  const toggleFix = (value: string) => {
    setFixFilters((prev) => (prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]));
  };

  const clearFilters = () => {
    setStatusFilters([]);
    setTypeFilters([]);
    setTicketFilters([]);
    setFixFilters([]);
    setSearchInput('');
    setSearch('');
  };

  const FilterChip = ({
    label,
    active,
    onClick,
  }: {
    label: string;
    active: boolean;
    onClick: () => void;
  }) => (
    <button
      onClick={onClick}
      className={`px-3 py-1 rounded-full text-xs border transition ${
        active
          ? 'bg-cyan-500/20 border-cyan-400 text-cyan-100'
          : 'border-slate-700 text-slate-300 hover:border-slate-500'
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Scans</h1>
          <p className="text-sm text-text-muted">Recent scan runs across cloud, git, and app targets.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 border border-slate-800 rounded-lg p-3 bg-slate-900/40">
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search target (device/app/repo)…"
            className="bg-slate-950/60 border border-slate-800 rounded px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-cyan-400 min-w-[240px]"
          />
          <button
            onClick={clearFilters}
            className="text-xs text-slate-400 hover:text-slate-200 px-2 py-1 border border-slate-700 rounded-full"
          >
            Clear filters
          </button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 mr-1">Status:</span>
          {statusOptions.map((s) => (
            <FilterChip key={s} label={s} active={statusFilters.includes(s)} onClick={() => toggleStatus(s)} />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 mr-1">Type:</span>
          {typePresets.map((t) => (
            <FilterChip key={t.id} label={t.label} active={typeFilters.includes(t.id)} onClick={() => toggleType(t.id)} />
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-slate-400 mr-1">Tickets:</span>
          {ticketOptions.map((t) => (
            <FilterChip key={t} label="Has ticket" active={ticketFilters.includes(t)} onClick={() => toggleTicket(t)} />
          ))}
          <FilterChip label="Has fixes" active={fixFilters.includes('with_fix')} onClick={() => toggleFix('with_fix')} />
        </div>
      </div>

      {error && (
        <div className="rounded border border-amber-500/50 bg-amber-500/10 text-amber-100 text-sm px-3 py-2">
          {error.status === 429 ? 'Rate limit or concurrency limit hit. Please retry shortly.' : 'Failed to load scans.'}
        </div>
      )}
      {!data && !error && <div className="text-sm text-text-muted">Loading scans...</div>}

      {data && data.length === 0 && <div className="text-sm text-text-muted">No scans yet. Trigger a scan to see it here.</div>}

      {data && data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-800/80 bg-slate-900/60">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-900/80">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Scan ID</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Target</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Updated</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Findings</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Artifact</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Fixes</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-300 uppercase tracking-wide">Ticket</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {data.map((scan) => {
                const statusBadge =
                  scan.status === 'completed'
                    ? 'bg-emerald-500/20 text-emerald-300'
                    : scan.status === 'running'
                    ? 'bg-amber-500/20 text-amber-200'
                    : scan.status === 'failed'
                    ? 'bg-rose-500/20 text-rose-200'
                    : 'bg-slate-700 text-slate-200';
                const findings = typeof scan.summary?.findings === 'number' ? scan.summary.findings : null;
                const duration =
                  scan.started_at && scan.finished_at
                    ? Math.max(
                        0,
                        (new Date(scan.finished_at).getTime() - new Date(scan.started_at).getTime()) / 1000
                      )
                    : null;
                return (
                  <tr key={scan.id}>
                    <td className="px-4 py-3 text-sm text-slate-100">
                      <Link href={`/dashboard/scans/${scan.id}`} className="text-primary hover:underline">
                        {`${scan.id.slice(0, 8)}...`}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-200">{scan.scan_type || '—'}</td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs ${statusBadge}`}>{scan.status}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-300">{scan.target_ref || '—'}</td>
                    <td className="px-4 py-3 text-sm text-slate-300">
                      {scan.updated_at ? new Date(scan.updated_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-200">{findings ?? '—'}</td>
                    <td className="px-4 py-3 text-sm">
                      {duration !== null ? `${duration.toFixed(1)}s` : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {scan.artifact_signed_url || scan.artifact_url ? (
                        <a
                          href={scan.artifact_signed_url || scan.artifact_url}
                          className="text-primary hover:underline"
                          target="_blank"
                          rel="noreferrer"
                        >
                          View
                        </a>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {scan.has_fix_groups ? (
                        <Link href={`/dashboard/scans/${scan.id}`} className="text-primary hover:underline text-xs">
                          View fixes
                        </Link>
                      ) : (
                        <span className="text-slate-500 text-xs">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {scan.ticket_id ? (
                        <Link href={`/dashboard/tickets/${scan.ticket_id}`} className="text-primary hover:underline text-xs">
                          {scan.ticket_id} ({scan.ticket_status || 'open'})
                        </Link>
                      ) : (
                        <span className="text-slate-500 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
