'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { listDetectionRules, DetectionRule } from '@/lib/api/detection-rules';
import { getSourceHealth, SourceHealth } from '@/lib/api/siem';
import HealthBadge from '@/components/ui/HealthBadge';

const sourceInfo = (indexPattern?: string) => {
  const pat = (indexPattern || '').toLowerCase();
  if (pat.includes('-ai-')) return { label: 'AI telemetry', color: 'bg-indigo-500/10 border-indigo-500/40 text-indigo-200' };
  if (pat.includes('-auth-')) return { label: 'Identity/Auth', color: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200' };
  if (pat.includes('-endpoint-')) return { label: 'Endpoint', color: 'bg-orange-500/10 border-orange-500/40 text-orange-200' };
  if (pat.includes('-network-')) return { label: 'Network/Flow', color: 'bg-blue-500/10 border-blue-500/40 text-blue-200' };
  if (pat.includes('-cloud-')) return { label: 'Cloud', color: 'bg-cyan-500/10 border-cyan-500/40 text-cyan-200' };
  return { label: 'Unknown source', color: 'bg-slate-700/60 border-slate-600 text-text-muted' };
};

export default function RuleHealthDashboard() {
  const { data: rules, isLoading } = useQuery<DetectionRule[]>({
    queryKey: ['detection-rules'],
    queryFn: () => listDetectionRules(),
  });
  const { data: sourceHealth, error: sourceHealthError } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  const stats = useMemo(() => {
    const total = rules?.length || 0;
    const enabled = (rules || []).filter((r) => r.deployment?.is_enabled !== false).length;
    const disabled = total - enabled;
    const unmapped = (rules || []).filter((r) => !(r as any).mapping?.playbook_key).length;
    const missingDest = (rules || []).filter((r) => !r.deployment?.destination_id).length;
    return { total, enabled, disabled, unmapped, missingDest };
  }, [rules]);

  if (isLoading || !rules) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-bg-alt rounded w-1/3 mb-6"></div>
          <div className="grid grid-cols-4 gap-4 mb-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-bg-alt rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/dashboard/siem/detection-rules"
          className="text-sm text-primary hover:underline mb-2 inline-block"
        >
          ← Back to Detection Rules
        </Link>
        <h1 className="text-3xl font-bold text-text-main mb-1">
          Rule Health & Readiness
        </h1>
        <p className="text-text-muted">
          Spot gaps: disabled rules, missing playbooks, missing destinations, and source coverage.
        </p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-muted">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
          <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
          {sourceHealthError && (
            <Link href="/login" className="text-primary underline">
              Session expired? Sign in again.
            </Link>
          )}
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="text-text-muted text-sm mb-1">Total Rules</div>
          <div className="text-3xl font-bold text-text-main">{stats.total}</div>
          <div className="text-sm text-green-500 mt-1">{stats.enabled} enabled</div>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="text-text-muted text-sm mb-1">Disabled</div>
          <div className="text-3xl font-bold text-text-main">{stats.disabled}</div>
          <div className="text-sm text-text-muted mt-1">Not running monitors</div>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="text-text-muted text-sm mb-1">Missing playbook mapping</div>
          <div className="text-3xl font-bold text-text-main">{stats.unmapped}</div>
          <div className="text-sm text-text-muted mt-1">Map to playbooks for response</div>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="text-text-muted text-sm mb-1">Missing destination</div>
          <div className="text-3xl font-bold text-text-main">{stats.missingDest}</div>
          <div className="text-sm text-text-muted mt-1">Set destination_id before deploy</div>
        </div>
      </div>

      {/* Readiness table */}
      <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
        <h2 className="text-xl font-semibold text-text-main mb-4">Readiness by Rule</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left">
            <thead className="text-text-muted">
              <tr>
                <th className="py-2 pr-4">Rule</th>
                <th className="py-2 pr-4">Source</th>
                <th className="py-2 pr-4">Version</th>
                <th className="py-2 pr-4">Playbook</th>
                <th className="py-2 pr-4">Destination</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {(rules || []).map((r) => {
                const ver = r.versions?.[0];
                const src = sourceInfo(ver?.index_pattern);
                const hasDest = !!r.deployment?.destination_id;
                const mapped = (r as any).mapping?.playbook_key;
                return (
                  <tr key={r.id} className="border-t border-[rgba(15,23,42,0.6)]">
                    <td className="py-2 pr-4">
                      <Link href={`/dashboard/siem/detection-rules/${r.id}`} className="text-primary hover:underline">
                        {r.rule_key}
                      </Link>
                      <div className="text-text-muted">{r.name}</div>
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`px-2 py-1 text-[11px] rounded-full border ${src.color}`}>
                        {src.label}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-text-muted">
                      {r.current_version}
                    </td>
                    <td className="py-2 pr-4">
                      {mapped ? (
                        <Link href={`/dashboard/playbooks?search=${encodeURIComponent(mapped)}`} className="text-primary hover:underline">
                          {mapped}
                        </Link>
                      ) : (
                        <span className="text-text-muted">None</span>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      {hasDest ? (
                        <span className="text-emerald-300 text-xs px-2 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30">
                          set
                        </span>
                      ) : (
                        <span className="text-yellow-300 text-xs px-2 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/30">
                          missing
                        </span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-text-muted">
                      {r.deployment?.is_enabled === false ? 'Disabled' : 'Enabled'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
