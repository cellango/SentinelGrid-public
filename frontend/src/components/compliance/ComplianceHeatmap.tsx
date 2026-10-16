/**
 * Compliance Heatmap
 * Visual grid showing compliance status across frameworks and control families.
 * Competitive with Wiz's compliance heatmap.
 */

'use client';

import { useMemo, useState } from 'react';
import clsx from 'clsx';
import type { ComplianceCriterion } from '@/lib/api/compliance';

// ── Types ──────────────────────────────────────────────────────────────

type HeatmapStatus = 'compliant' | 'partial' | 'non_compliant' | 'not_assessed';

interface HeatmapCell {
  id: string;
  title: string;
  status: HeatmapStatus;
  openFindings: number;
  totalFindings: number;
  evidenceItems: number;
  score: number; // 0-100
}

interface HeatmapRow {
  category: string;
  cells: HeatmapCell[];
}

interface ComplianceHeatmapProps {
  criteria: ComplianceCriterion[];
  onCellClick?: (criterion: ComplianceCriterion) => void;
  className?: string;
}

// ── Status colors ─────────────────────────────────────────────────────

const STATUS_COLORS: Record<HeatmapStatus, { bg: string; border: string; text: string; label: string }> = {
  compliant: { bg: 'bg-emerald-500/20', border: 'border-emerald-500/40', text: 'text-emerald-300', label: 'Compliant' },
  partial: { bg: 'bg-amber-500/20', border: 'border-amber-500/40', text: 'text-amber-300', label: 'Partial' },
  non_compliant: { bg: 'bg-rose-500/20', border: 'border-rose-500/40', text: 'text-rose-300', label: 'Non-Compliant' },
  not_assessed: { bg: 'bg-slate-600/20', border: 'border-slate-600/40', text: 'text-slate-400', label: 'Not Assessed' },
};

function getHeatColor(score: number): string {
  if (score >= 90) return 'bg-emerald-500/30 hover:bg-emerald-500/40';
  if (score >= 70) return 'bg-emerald-500/15 hover:bg-emerald-500/25';
  if (score >= 50) return 'bg-amber-500/20 hover:bg-amber-500/30';
  if (score >= 25) return 'bg-orange-500/20 hover:bg-orange-500/30';
  if (score > 0) return 'bg-rose-500/20 hover:bg-rose-500/30';
  return 'bg-slate-700/30 hover:bg-slate-700/40';
}

// ── Group criteria by category prefix ──────────────────────────────────

function groupCriteria(criteria: ComplianceCriterion[]): HeatmapRow[] {
  const groups = new Map<string, ComplianceCriterion[]>();

  for (const c of criteria) {
    // Extract category from criterion ID (e.g., "CC1.1" → "CC1", "A1.1" → "A1")
    const match = c.id.match(/^([A-Z]+\d+)/);
    const category = match ? match[1] : 'Other';
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category)!.push(c);
  }

  return Array.from(groups.entries()).map(([category, items]) => ({
    category,
    cells: items.map((c) => ({
      id: c.id,
      title: c.title,
      status: c.status,
      openFindings: c.open_findings,
      totalFindings: c.total_findings,
      evidenceItems: c.evidence_items,
      score:
        c.total_findings > 0
          ? Math.round(((c.total_findings - c.open_findings) / c.total_findings) * 100)
          : c.status === 'compliant'
            ? 100
            : c.status === 'partial'
              ? 50
              : 0,
    })),
  }));
}

// ── Category labels ────────────────────────────────────────────────────

const CATEGORY_LABELS: Record<string, string> = {
  CC1: 'Control Environment',
  CC2: 'Communication & Information',
  CC3: 'Risk Assessment',
  CC4: 'Monitoring',
  CC5: 'Control Activities',
  CC6: 'Logical & Physical Access',
  CC7: 'System Operations',
  CC8: 'Change Management',
  CC9: 'Risk Mitigation',
  A1: 'Availability',
  C1: 'Confidentiality',
  PI1: 'Processing Integrity',
  P1: 'Privacy',
};

// ── Component ──────────────────────────────────────────────────────────

export default function ComplianceHeatmap({ criteria, onCellClick, className }: ComplianceHeatmapProps) {
  const [hoveredCell, setHoveredCell] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'heatmap' | 'list'>('heatmap');

  const rows = useMemo(() => groupCriteria(criteria), [criteria]);

  const stats = useMemo(() => {
    const total = criteria.length;
    const compliant = criteria.filter((c) => c.status === 'compliant').length;
    const partial = criteria.filter((c) => c.status === 'partial').length;
    const nonCompliant = criteria.filter((c) => c.status === 'non_compliant').length;
    const notAssessed = criteria.filter((c) => c.status === 'not_assessed').length;
    return { total, compliant, partial, nonCompliant, notAssessed };
  }, [criteria]);

  if (!criteria.length) {
    return (
      <div className={clsx('p-8 text-center bg-surface-card rounded-lg border border-border-faint', className)}>
        <p className="text-text-muted text-sm">No compliance criteria loaded. Connect a compliance framework to see your heatmap.</p>
      </div>
    );
  }

  return (
    <div className={clsx('bg-surface-card rounded-lg border border-border-faint overflow-hidden', className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-border-faint flex flex-col sm:flex-row sm:items-center gap-3">
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-text-main">Compliance Heatmap</h3>
          <p className="text-xs text-text-muted mt-0.5">SOC 2 Type II — {stats.total} criteria</p>
        </div>

        {/* Summary pills */}
        <div className="flex items-center gap-2 flex-wrap">
          {Object.entries(STATUS_COLORS).map(([status, style]) => {
            const count =
              status === 'compliant' ? stats.compliant
              : status === 'partial' ? stats.partial
              : status === 'non_compliant' ? stats.nonCompliant
              : stats.notAssessed;
            return (
              <span
                key={status}
                className={clsx('inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs border', style.bg, style.border, style.text)}
              >
                <span className={clsx('w-1.5 h-1.5 rounded-full', style.bg.replace('/20', ''))} />
                {count} {style.label}
              </span>
            );
          })}
        </div>

        {/* View toggle */}
        <div className="flex items-center rounded-lg border border-border-faint overflow-hidden">
          <button
            onClick={() => setViewMode('heatmap')}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium transition-colors min-h-[32px]',
              viewMode === 'heatmap' ? 'bg-primary/15 text-primary' : 'text-text-muted hover:text-text-main'
            )}
            aria-pressed={viewMode === 'heatmap'}
          >
            Grid
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium transition-colors min-h-[32px]',
              viewMode === 'list' ? 'bg-primary/15 text-primary' : 'text-text-muted hover:text-text-main'
            )}
            aria-pressed={viewMode === 'list'}
          >
            List
          </button>
        </div>
      </div>

      {/* Heatmap grid */}
      {viewMode === 'heatmap' ? (
        <div className="p-4 overflow-x-auto">
          <div className="space-y-2 min-w-[600px]">
            {rows.map((row) => (
              <div key={row.category} className="flex items-start gap-3">
                <div className="w-28 flex-shrink-0 pt-1.5">
                  <p className="text-xs font-semibold text-text-main">{row.category}</p>
                  <p className="text-[10px] text-text-muted leading-tight">
                    {CATEGORY_LABELS[row.category] || ''}
                  </p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {row.cells.map((cell) => {
                    const criterion = criteria.find((c) => c.id === cell.id);
                    return (
                      <button
                        key={cell.id}
                        onClick={() => criterion && onCellClick?.(criterion)}
                        onMouseEnter={() => setHoveredCell(cell.id)}
                        onMouseLeave={() => setHoveredCell(null)}
                        className={clsx(
                          'relative w-10 h-10 rounded-md border border-border-faint transition-all duration-150 flex items-center justify-center text-[10px] font-medium min-h-[44px] min-w-[44px]',
                          getHeatColor(cell.score),
                          hoveredCell === cell.id && 'ring-2 ring-primary/50 scale-110 z-10'
                        )}
                        title={`${cell.id}: ${cell.title} (${cell.status})`}
                        aria-label={`${cell.id}: ${cell.title}, ${STATUS_COLORS[cell.status].label}, ${cell.openFindings} open findings`}
                      >
                        {cell.id.replace(/^[A-Z]+/, '')}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* List view */
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <caption className="sr-only">Compliance criteria status</caption>
            <thead>
              <tr className="border-b border-border-faint">
                <th scope="col" className="text-left text-xs font-medium text-text-muted px-4 py-2">Control</th>
                <th scope="col" className="text-left text-xs font-medium text-text-muted px-4 py-2">Title</th>
                <th scope="col" className="text-center text-xs font-medium text-text-muted px-4 py-2">Status</th>
                <th scope="col" className="text-center text-xs font-medium text-text-muted px-4 py-2">Findings</th>
                <th scope="col" className="text-center text-xs font-medium text-text-muted px-4 py-2">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {criteria.map((c) => {
                const style = STATUS_COLORS[c.status];
                return (
                  <tr
                    key={c.id}
                    onClick={() => onCellClick?.(c)}
                    className="border-b border-border-faint hover:bg-surface-hover cursor-pointer transition-colors"
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onCellClick?.(c); } }}
                  >
                    <td className="px-4 py-2.5 font-mono text-xs text-text-main">{c.id}</td>
                    <td className="px-4 py-2.5 text-text-main">{c.title}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-xs border', style.bg, style.border, style.text)}>
                        {style.label}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center tabular-nums">
                      <span className="text-text-muted">{c.open_findings}</span>
                      <span className="text-text-muted/50"> / {c.total_findings}</span>
                    </td>
                    <td className="px-4 py-2.5 text-center tabular-nums text-text-muted">{c.evidence_items}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Tooltip */}
      {hoveredCell && viewMode === 'heatmap' && (() => {
        const cell = rows.flatMap((r) => r.cells).find((c) => c.id === hoveredCell);
        if (!cell) return null;
        const style = STATUS_COLORS[cell.status];
        return (
          <div className="fixed z-50 pointer-events-none" style={{ bottom: 80, right: 24 }}>
            <div className="bg-surface-card border border-border-faint rounded-lg px-3 py-2 shadow-xl text-xs min-w-[200px]">
              <p className="font-semibold text-text-main">{cell.id}: {cell.title}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className={clsx('px-1.5 py-0.5 rounded text-[10px] border', style.bg, style.border, style.text)}>
                  {style.label}
                </span>
                <span className="text-text-muted">{cell.openFindings} open / {cell.totalFindings} total findings</span>
              </div>
              <p className="text-text-muted mt-1">{cell.evidenceItems} evidence items</p>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
