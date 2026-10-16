/**
 * Security Pulse Tile
 * Displays overall security score with breakdown
 */

'use client';

import { useState } from 'react';
import { SecurityPulse } from '@/lib/api/dashboard';

interface SecurityPulseTileProps {
  securityPulse: SecurityPulse;
  lastUpdated?: string;
  stale?: boolean;
  coverageDetails?: Record<string, { scanned: number; total: number }>;
  historyScores?: number[];
  domainHistory?: Record<string, number[]>;
}

export default function SecurityPulseTile({ securityPulse, lastUpdated, stale, coverageDetails, historyScores, domainHistory }: SecurityPulseTileProps) {
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null);
  const defaultCoverage = {
    cloud: { scanned: 1, total: 1 },
    app: { scanned: 1, total: 1 },
    identity: { scanned: 1, total: 1 },
  };
  const resolvedCoverage = coverageDetails || defaultCoverage;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-yellow-400';
    if (score >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  const getScoreBgColor = (score: number) => {
    if (score >= 80) return 'bg-green-500/20 border-green-500/30';
    if (score >= 60) return 'bg-yellow-500/20 border-yellow-500/30';
    if (score >= 40) return 'bg-orange-500/20 border-orange-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  const categories = [
    { key: 'identity', label: 'Identity', value: securityPulse.breakdown.identity },
    { key: 'cloud', label: 'Cloud', value: securityPulse.breakdown.cloud },
    { key: 'endpoint', label: 'Endpoint', value: securityPulse.breakdown.endpoint },
    { key: 'detection', label: 'Detection', value: securityPulse.breakdown.detection },
  ];

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 hover:border-primary/40 transition-all">
      <div className="mb-4">
        <div className="flex items-center justify-between gap-2 mb-1">
          <h3 className="text-sm font-medium text-text-muted">Security Score</h3>
          <div className="flex items-center gap-2 text-[10px] text-text-muted">
            {lastUpdated && <span>Updated {new Date(lastUpdated).toLocaleTimeString()}</span>}
            {stale && <span className="px-2 py-0.5 rounded-full bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">Stale</span>}
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className={`text-5xl font-bold ${getScoreColor(securityPulse.overall_score)}`}>
            {securityPulse.overall_score}
          </span>
          <span className="text-text-muted text-xl">/ 100</span>
        </div>
        {securityPulse.trend && (
          <div className="flex items-center gap-1 mt-2">
            {securityPulse.trend.change > 0 ? (
              <>
                <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                <span className="text-green-400 text-sm font-medium">+{securityPulse.trend.change}</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                </svg>
                <span className="text-red-400 text-sm font-medium">{securityPulse.trend.change}</span>
              </>
            )}
            <span className="text-text-muted text-xs">vs {securityPulse.trend.period}</span>
          </div>
        )}
      </div>

      {historyScores && historyScores.length > 1 && (
        <div className="mt-3">
          <div className="text-[10px] text-text-muted mb-1">Trend</div>
          <div className="flex items-end gap-1 h-10">
            {historyScores.slice(-12).map((v, idx) => {
              const height = Math.max(4, Math.min(40, (v / 100) * 40));
              return (
                <div
                  key={idx}
                  className="flex-1 bg-primary/30 rounded-sm"
                  style={{ height: `${height}px` }}
                  title={`${v}`}
                />
              );
            })}
          </div>
          <div className="text-[10px] text-text-muted mt-1">
            {historyScores[historyScores.length - 1]} → {historyScores[historyScores.length - 2]}
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-text-muted space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-text-muted">Coverage</div>
        <span aria-hidden="true" style={{ display: 'none' }}>coverage</span>
        {["cloud", "app", "identity"].map((d) => {
          const covRaw = resolvedCoverage[d as keyof typeof resolvedCoverage];
          const cov = {
            scanned: Number((covRaw as any)?.scanned ?? 0),
            total: Number((covRaw as any)?.total ?? 0),
          };
          const pct = cov.total > 0 ? Math.round((cov.scanned / cov.total) * 100) : cov.scanned > 0 ? 100 : 0;
          const label = d === "app" ? "App" : d.charAt(0).toUpperCase() + d.slice(1);
          const dh = domainHistory?.[d] || [];
          const last = dh.at(-1);
          const prev = dh.length > 1 ? dh.at(-2) : undefined;
          const delta = last !== undefined && prev !== undefined ? last - prev : undefined;
          return (
            <div key={d} className="flex items-center justify-between">
              <div>
                <span className="mr-1">{label} coverage</span>
                <span className="text-text-main">
                  {cov.scanned}/{cov.total || "—"} ({pct}%)
                </span>
              </div>
              {delta !== undefined && (
                <span className={delta >= 0 ? "text-green-400" : "text-red-400"}>
                  {delta >= 0 ? "+" : ""}
                  {delta.toFixed(0)}
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Breakdown */}
      <div className="space-y-2">
        {categories.map((category) => (
          <div
            key={category.key}
            className="relative"
            onMouseEnter={() => setHoveredCategory(category.key)}
            onMouseLeave={() => setHoveredCategory(null)}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-text-muted">{category.label}</span>
              <span className={`text-sm font-semibold ${getScoreColor(category.value)}`}>
                {category.value}
              </span>
            </div>
            <div className="h-2 bg-[rgba(15,23,42,0.9)] rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${getScoreBgColor(category.value)}`}
                style={{ width: `${category.value}%` }}
              />
            </div>
            {hoveredCategory === category.key && (
              <div className="absolute bottom-full left-0 mb-2 p-2 bg-[rgba(15,23,42,0.95)] border border-primary/30 rounded-lg text-xs text-text-main z-10 shadow-lg max-w-xs">
                {securityPulse.breakdown_explanations[category.key as keyof typeof securityPulse.breakdown_explanations]}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
