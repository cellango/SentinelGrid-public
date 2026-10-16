/**
 * War Room — Unified Priority Queue
 * Single prioritized queue combining incidents, alerts, and recommendations.
 * Competitive with Wiz's single priority queue concept.
 */

'use client';

import { useState, useMemo } from 'react';
import clsx from 'clsx';
import type { NowQueueItem, NowQueueSummary } from '@/lib/api/dashboard';
import AgentBadge from '@/components/ui/AgentBadge';
import type { AgentId } from '@/components/ui/AgentBadge';

interface WarRoomQueueProps {
  items: NowQueueItem[];
  summary?: NowQueueSummary;
  onItemClick?: (item: NowQueueItem) => void;
  onActionClick?: (item: NowQueueItem) => void;
  className?: string;
}

// ── Severity styling ───────────────────────────────────────────────────

const PRIORITY_STYLES: Record<string, { dot: string; bg: string; border: string; text: string; pulse?: boolean }> = {
  critical: { dot: 'bg-rose-500', bg: 'bg-rose-500/5', border: 'border-l-rose-500', text: 'text-rose-300', pulse: true },
  high: { dot: 'bg-orange-500', bg: 'bg-orange-500/5', border: 'border-l-orange-500', text: 'text-orange-300' },
  medium: { dot: 'bg-amber-500', bg: 'bg-amber-500/5', border: 'border-l-amber-500', text: 'text-amber-300' },
  low: { dot: 'bg-blue-500', bg: 'bg-blue-500/5', border: 'border-l-blue-500', text: 'text-blue-300' },
};

const TYPE_ICONS: Record<string, { icon: string; label: string }> = {
  incident: {
    icon: 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z',
    label: 'Incident',
  },
  alert: {
    icon: 'M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0',
    label: 'Alert',
  },
  recommendation: {
    icon: 'M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18',
    label: 'Recommendation',
  },
};

// ── Guess agent from source label ─────────────────────────────────────

function guessAgent(item: NowQueueItem): AgentId | null {
  const source = (item.source_label || '').toLowerCase();
  if (source.includes('siem') || source.includes('detection')) return 'siem_agent';
  if (source.includes('iam') || source.includes('identity')) return 'iam_agent';
  if (source.includes('compliance')) return 'compliance_agent';
  if (source.includes('cloud') || source.includes('posture')) return 'cloud_posture_agent';
  if (source.includes('incident')) return 'incident_agent';
  if (source.includes('ai') || source.includes('shield')) return 'ai_shield_agent';
  if (item.item_type === 'recommendation') return 'orchestrator';
  return null;
}

// ── Component ──────────────────────────────────────────────────────────

export default function WarRoomQueue({
  items,
  summary,
  onItemClick,
  onActionClick,
  className,
}: WarRoomQueueProps) {
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (typeFilter !== 'all' && item.item_type !== typeFilter) return false;
      if (priorityFilter !== 'all' && item.priority !== priorityFilter) return false;
      return true;
    });
  }, [items, typeFilter, priorityFilter]);

  return (
    <div className={clsx('bg-surface-card rounded-lg border border-border-faint overflow-hidden', className)}>
      {/* Header with summary */}
      <div className="px-4 py-3 border-b border-border-faint">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-text-main flex items-center gap-2">
              War Room
              {summary && summary.urgent_items > 0 && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 border border-rose-500/40 text-rose-300 tabular-nums">
                  {summary.urgent_items} urgent
                </span>
              )}
            </h3>
            <p className="text-xs text-text-muted mt-0.5">
              Unified priority queue — {items.length} items requiring attention
            </p>
          </div>
        </div>

        {/* Summary counters */}
        {summary && (
          <div className="flex items-center gap-3 mb-3">
            {[
              { label: 'Incidents', count: summary.incidents, color: 'text-rose-300' },
              { label: 'Alerts', count: summary.alerts, color: 'text-amber-300' },
              { label: 'Actions', count: summary.recommendations, color: 'text-primary' },
            ].map((s) => (
              <span key={s.label} className="text-xs">
                <span className={clsx('font-semibold tabular-nums', s.color)}>{s.count}</span>
                <span className="text-text-muted ml-1">{s.label}</span>
              </span>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-2 flex-wrap">
          {['all', 'incident', 'alert', 'recommendation'].map((type) => (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={clsx(
                'px-2.5 py-1 text-xs font-medium rounded-full transition-colors min-h-[32px]',
                typeFilter === type
                  ? 'bg-primary/15 text-primary border border-primary/30'
                  : 'text-text-muted hover:text-text-main border border-transparent hover:border-border-muted'
              )}
              aria-pressed={typeFilter === type}
            >
              {type === 'all' ? 'All' : type.charAt(0).toUpperCase() + type.slice(1) + 's'}
            </button>
          ))}
          <span className="w-px h-4 bg-border-faint mx-1" aria-hidden="true" />
          {['all', 'critical', 'high', 'medium', 'low'].map((p) => (
            <button
              key={p}
              onClick={() => setPriorityFilter(p)}
              className={clsx(
                'px-2 py-1 text-xs rounded-full transition-colors min-h-[32px]',
                priorityFilter === p
                  ? p === 'all'
                    ? 'bg-slate-500/15 text-text-main border border-slate-500/30'
                    : clsx(PRIORITY_STYLES[p]?.bg, PRIORITY_STYLES[p]?.text, 'border', PRIORITY_STYLES[p]?.border.replace('border-l-', 'border-'))
                  : 'text-text-muted hover:text-text-main border border-transparent'
              )}
              aria-pressed={priorityFilter === p}
            >
              {p === 'all' ? 'All' : p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Queue items */}
      <div className="divide-y divide-border-faint max-h-[600px] overflow-y-auto">
        {filteredItems.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <p className="text-sm text-text-muted">No items match your filters</p>
          </div>
        ) : (
          filteredItems.map((item) => {
            const pStyle = PRIORITY_STYLES[item.priority] || PRIORITY_STYLES.low;
            const typeInfo = TYPE_ICONS[item.item_type] || TYPE_ICONS.alert;
            const agent = guessAgent(item);

            return (
              <div
                key={item.id}
                className={clsx(
                  'group flex items-start gap-3 px-4 py-3 border-l-3 cursor-pointer transition-colors hover:bg-surface-hover',
                  pStyle.border
                )}
                onClick={() => onItemClick?.(item)}
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onItemClick?.(item); } }}
                role="button"
                aria-label={`${item.priority} ${item.item_type}: ${item.title}`}
              >
                {/* Priority dot + type icon */}
                <div className="flex flex-col items-center gap-1.5 pt-0.5 flex-shrink-0">
                  <span className={clsx('w-2.5 h-2.5 rounded-full', pStyle.dot, pStyle.pulse && 'animate-pulse')} />
                  <svg className="w-4 h-4 text-text-muted" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" d={typeInfo.icon} />
                  </svg>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h4 className="text-sm font-medium text-text-main truncate">{item.title}</h4>
                    {agent && <AgentBadge agentId={agent} variant="inline" />}
                  </div>
                  <p className="text-xs text-text-muted line-clamp-2">{item.summary}</p>
                  {item.why_now && (
                    <p className="text-[11px] text-primary/80 mt-1 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {item.why_now}
                    </p>
                  )}
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="text-[10px] text-text-muted">{item.source_label}</span>
                    {item.owner && <span className="text-[10px] text-text-muted">· {item.owner}</span>}
                    {item.estimated_time_minutes && (
                      <span className="text-[10px] text-text-muted">· ~{item.estimated_time_minutes}m</span>
                    )}
                  </div>
                </div>

                {/* Action button */}
                <button
                  onClick={(e) => { e.stopPropagation(); onActionClick?.(item); }}
                  className="flex-shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors opacity-0 group-hover:opacity-100 min-h-[32px]"
                >
                  {item.action_label || 'Investigate'}
                </button>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
