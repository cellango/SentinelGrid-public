/**
 * Top Risks Tile
 * Shows highest-weighted posture risks with domain/severity/exposure flags.
 */

'use client';

import React from 'react';

import Link from 'next/link';

type Risk = {
  id?: string;
  title: string;
  severity: string;
  domain?: string;
  exposed?: boolean;
  criticality?: string | null;
  data_classification?: string | null;
};

interface TopRisksTileProps {
  risks: Risk[];
}

const severityColor = (sev: string) => {
  const s = (sev || '').toLowerCase();
  if (s === 'critical') return 'text-red-400';
  if (s === 'high') return 'text-orange-400';
  if (s === 'medium') return 'text-yellow-400';
  return 'text-text-muted';
};

export default function TopRisksTile({ risks }: TopRisksTileProps) {
  const items = risks?.slice(0, 5) || [];

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 h-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-text-muted">Top Risks</h3>
        <span className="text-[11px] text-text-muted">{items.length} shown</span>
      </div>
      {items.length === 0 ? (
        <p className="text-text-muted text-sm">No risks to show yet.</p>
      ) : (
        <div className="space-y-3">
          {items.map((risk, idx) => (
            <div key={`${risk.title}-${idx}`} className="p-3 rounded-lg border border-slate-800 bg-slate-900/50">
              <div className="flex items-center justify-between gap-2">
                <span className={`text-xs font-semibold ${severityColor(risk.severity)}`}>
                  {risk.severity?.toUpperCase() || 'N/A'}
                </span>
                <div className="text-[11px] text-text-muted flex items-center gap-2">
                  {risk.domain && <span className="px-2 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-primary">{risk.domain}</span>}
                  {risk.exposed && <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-red-400">Exposed</span>}
                  {risk.criticality && <span className="px-2 py-0.5 rounded-full bg-orange-500/10 border border-orange-500/30 text-orange-300">{risk.criticality}</span>}
                  {risk.data_classification && <span className="px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-200">{risk.data_classification}</span>}
                </div>
              </div>
              {risk.id ? (
                <Link href={`/dashboard/scans?findingId=${risk.id}`} className="text-sm text-primary hover:underline mt-1 inline-block">
                  {risk.title}
                </Link>
              ) : (
                <p className="text-sm text-text-main mt-1">{risk.title}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
