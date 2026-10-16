import React from 'react';
import { SourceHealth } from '@/lib/api/siem';

type Props = {
  health?: SourceHealth;
};

const STATUS_LABELS: Record<string, string> = {
  wazuh: 'Baseline sensor',
  openedr: 'Behavioral telemetry',
  velociraptor: 'Hunt/collections',
};

function badge(label: string, status?: string) {
  const state = (status || 'unknown').toLowerCase();
  const isHealthy = state.includes('healthy') || state === 'ok';
  const isDegraded = state.includes('degraded') || state.includes('warn');
  const isDown = state.includes('unreachable') || state.includes('error') || state.includes('fail');
  const color = isHealthy
    ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-200'
    : isDegraded
      ? 'bg-amber-500/10 border-amber-500/40 text-amber-200'
      : isDown
        ? 'bg-rose-500/10 border-rose-500/40 text-rose-200'
        : 'bg-slate-700/60 border-slate-600 text-text-muted';
  return (
    <span className={`px-2 py-1 rounded-full text-[11px] border ${color}`} title={`${label}: ${status || 'unknown'}`}>
      {label}: {status || 'unknown'}
    </span>
  );
}

export default function SensorHealth({ health }: Props) {
  const edrStatuses: Array<{ key: keyof SourceHealth; label: string }> = [
    { key: 'wazuh', label: STATUS_LABELS.wazuh },
    { key: 'openedr', label: STATUS_LABELS.openedr },
    { key: 'velociraptor', label: STATUS_LABELS.velociraptor },
  ];

  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-sm uppercase tracking-wide text-text-muted">Endpoint telemetry</p>
          <h3 className="text-lg font-semibold text-text-main">Sensor health</h3>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {!health && (
          <>
            {[1, 2, 3, 4].map((i) => (
              <span key={i} className="h-6 w-28 animate-pulse rounded-full bg-slate-700/50" />
            ))}
          </>
        )}
        {health && <span className="px-2 py-1 rounded-full text-[11px] border bg-emerald-500/10 border-emerald-500/40 text-emerald-200" title="AI gateway / model guardrail status">
          AI active
        </span>}
        {health && edrStatuses.map(({ key, label }) => (
          <React.Fragment key={key}>
            {badge(label, health?.[key])}
          </React.Fragment>
        ))}
        {health && badge('Ingestion', health?.ingestion_service)}
        {health && badge('SIEM Agent', health?.siem_agent)}
        {health && badge('OpenSearch', health?.opensearch)}
      </div>
    </div>
  );
}
