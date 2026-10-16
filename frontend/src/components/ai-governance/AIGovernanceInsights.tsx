'use client';

import clsx from 'clsx';
import type {
  AIGovernanceAppInventoryEntry,
  AIGovernanceSummary,
} from '@/lib/api/reports';

const RISK_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  critical: { bg: 'bg-rose-500/15', text: 'text-rose-300', border: 'border-rose-500/40' },
  high: { bg: 'bg-orange-500/15', text: 'text-orange-300', border: 'border-orange-500/40' },
  medium: { bg: 'bg-amber-500/15', text: 'text-amber-300', border: 'border-amber-500/40' },
  low: { bg: 'bg-blue-500/15', text: 'text-blue-300', border: 'border-blue-500/40' },
};

const GOVERNANCE_STATE_STYLES: Record<string, string> = {
  needs_review: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
  guardrail_watch: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
  monitored: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
  unclassified: 'bg-fuchsia-500/15 text-fuchsia-300 border border-fuchsia-500/30',
};

function humanizeState(value: string) {
  return value.replace(/_/g, ' ');
}

type GovernanceStateFilter =
  | 'all'
  | 'needs_review'
  | 'guardrail_watch'
  | 'monitored'
  | 'unclassified';

interface AIGovernanceInsightsProps {
  data: AIGovernanceSummary;
  filteredApps: AIGovernanceAppInventoryEntry[];
  lookbackDays: number;
  maxTrendRequests: number;
  stateFilter: GovernanceStateFilter;
  setStateFilter: (value: GovernanceStateFilter) => void;
}

export default function AIGovernanceInsights({
  data,
  filteredApps,
  lookbackDays,
  maxTrendRequests,
  stateFilter,
  setStateFilter,
}: AIGovernanceInsightsProps) {
  return (
    <>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 mb-6">
        {[
          {
            label: 'Governance Score',
            value: data.overview.governance_score,
            sub: `${data.overview.apps_needing_review} apps need review`,
            color:
              data.overview.governance_score >= 75
                ? 'text-emerald-400'
                : data.overview.governance_score >= 55
                  ? 'text-amber-400'
                  : 'text-rose-400',
          },
          {
            label: `AI Apps (${lookbackDays}d)`,
            value: data.overview.active_apps,
            sub: `${data.overview.unclassified_apps} unclassified`,
            color: 'text-primary',
          },
          {
            label: 'AI Cases',
            value: data.overview.active_ai_incidents,
            sub: `${data.overview.open_ai_alerts} open alerts`,
            color:
              data.overview.active_ai_incidents > 0 ? 'text-rose-400' : 'text-emerald-400',
          },
          {
            label: 'Requests',
            value: data.overview.requests_in_window.toLocaleString(),
            sub: `${data.overview.active_users} active users`,
            color: 'text-text-main',
          },
        ].map((card) => (
          <div key={card.label} className="bg-surface-card border border-border-faint rounded-lg p-4">
            <p className="text-[10px] font-medium text-text-muted uppercase tracking-wider">
              {card.label}
            </p>
            <p className={clsx('text-3xl font-bold tabular-nums mt-1', card.color)}>{card.value}</p>
            <p className="text-xs text-text-muted mt-0.5">{card.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.95fr,1.05fr] mb-6">
        <div className="bg-surface-card border border-border-faint rounded-lg p-4">
          <h3 className="text-sm font-semibold text-text-main mb-3">Risk Distribution</h3>
          <div className="space-y-2.5">
            {(['critical', 'high', 'medium', 'low'] as const).map((level) => {
              const count = data.risk_breakdown[level];
              const total = Math.max(
                data.risk_breakdown.critical +
                  data.risk_breakdown.high +
                  data.risk_breakdown.medium +
                  data.risk_breakdown.low,
                1
              );
              const pct = Math.round((count / total) * 100);
              const style = RISK_STYLES[level];

              return (
                <div key={level} className="flex items-center gap-3">
                  <span className={clsx('w-16 text-xs font-medium capitalize', style.text)}>
                    {level}
                  </span>
                  <div className="flex-1 h-2.5 rounded-full bg-surface-hover overflow-hidden">
                    <div
                      className={clsx('h-full rounded-full', style.bg.replace('/15', '/60'))}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="w-9 text-right text-xs text-text-muted tabular-nums">
                    {count}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-xs text-text-muted">{data.current_risk_summary}</p>
        </div>

        <div className="bg-surface-card border border-border-faint rounded-lg p-4">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-text-main">Top AI Threats</h3>
            <span className="text-xs text-text-muted">Trend vs prior window</span>
          </div>
          <div className="mt-4 space-y-2.5">
            {data.top_threats.map((threat) => (
              <div
                key={threat.type}
                className="flex items-center justify-between rounded-lg border border-border-faint bg-surface-hover p-3"
              >
                <div>
                  <p className="text-sm font-medium text-text-main">{threat.type}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold text-text-main tabular-nums">
                    {threat.count}
                  </span>
                  <span
                    className={clsx(
                      'text-[11px] font-semibold uppercase',
                      threat.trend === 'up'
                        ? 'text-rose-300'
                        : threat.trend === 'down'
                          ? 'text-emerald-300'
                          : 'text-text-muted'
                    )}
                  >
                    {threat.trend}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr] mb-6">
        <div className="bg-surface-card border border-border-faint rounded-lg p-4">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h3 className="text-sm font-semibold text-text-main">AI Usage Trend</h3>
            <span className="text-xs text-text-muted">Requests and policy hits</span>
          </div>
          <div className="space-y-3">
            {data.usage_trend.map((point) => (
              <div key={point.label} className="grid grid-cols-[72px,1fr,auto] items-center gap-3">
                <span className="text-xs text-text-muted">{point.label}</span>
                <div className="rounded-full bg-surface-hover h-2.5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{
                      width: `${Math.max(
                        (point.requests / maxTrendRequests) * 100,
                        point.requests > 0 ? 6 : 0
                      )}%`,
                    }}
                  />
                </div>
                <div className="text-right text-xs text-text-muted tabular-nums">
                  <div>{point.requests} req</div>
                  <div>{point.policy_hits} policy</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-surface-card border border-border-faint rounded-lg p-4">
          <h3 className="text-sm font-semibold text-text-main mb-4">Recent AI Activity</h3>
          <div className="space-y-3">
            {data.recent_activity.length === 0 ? (
              <p className="text-sm text-text-muted">No recent AI activity captured in this window.</p>
            ) : (
              data.recent_activity.map((item) => (
                <div
                  key={`${item.id || item.timestamp}-${item.action}`}
                  className="rounded-lg border border-border-faint bg-surface-hover p-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-text-main">{item.app_label}</p>
                    <span className="text-[11px] text-text-muted">
                      {item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-text-muted">
                    {item.user_label} · {item.action}
                    {item.model ? ` · ${item.model}` : ''}
                    {item.module ? ` · ${item.module}` : ''}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="bg-surface-card border border-border-faint rounded-lg overflow-hidden">
        <div className="border-b border-border-faint px-4 py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-sm font-semibold text-text-main">AI App Governance Inventory</h3>
            <p className="mt-1 text-xs text-text-muted">
              Apps and workflows observed through AI activity plus AI Shield risk context
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {(['all', 'needs_review', 'guardrail_watch', 'monitored', 'unclassified'] as const).map(
              (value) => (
                <button
                  key={value}
                  onClick={() => setStateFilter(value)}
                  className={clsx(
                    'min-h-[32px] rounded-full px-3 py-1.5 text-xs font-medium transition-colors',
                    stateFilter === value
                      ? 'border border-primary/30 bg-primary/15 text-primary'
                      : 'border border-transparent text-text-muted hover:border-border-muted hover:text-text-main'
                  )}
                  aria-pressed={stateFilter === value}
                >
                  {value === 'all' ? 'All' : humanizeState(value)}
                </button>
              )
            )}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-faint">
                <th className="px-4 py-2.5 text-left text-xs font-medium text-text-muted">
                  Application
                </th>
                <th className="px-4 py-2.5 text-center text-xs font-medium text-text-muted">
                  State
                </th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-text-muted">
                  Requests
                </th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-text-muted">
                  Users
                </th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-text-muted">
                  Policy Hits
                </th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-text-muted">
                  Alerts
                </th>
                <th className="px-4 py-2.5 text-right text-xs font-medium text-text-muted">
                  Incidents
                </th>
                <th className="px-4 py-2.5 text-center text-xs font-medium text-text-muted">
                  Risk
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredApps.map((app) => {
                const riskStyle = RISK_STYLES[app.highest_severity];
                return (
                  <tr
                    key={app.app_id}
                    className="border-b border-border-faint hover:bg-surface-hover transition-colors"
                  >
                    <td className="px-4 py-3">
                      <p className="font-medium text-text-main">{app.label}</p>
                      <p className="mt-1 text-xs text-text-muted">
                        {app.models.join(', ') || app.modules.join(', ') || 'No model metadata'}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={clsx(
                          'rounded-full px-2 py-0.5 text-xs font-medium capitalize',
                          GOVERNANCE_STATE_STYLES[app.governance_state]
                        )}
                      >
                        {humanizeState(app.governance_state)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-text-main">
                      {app.requests_in_window.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-text-muted">
                      {app.unique_users}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span
                        className={app.policy_hits > 0 ? 'text-amber-300 font-medium' : 'text-text-muted'}
                      >
                        {app.policy_hits}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span
                        className={app.open_alerts > 0 ? 'text-amber-300 font-medium' : 'text-text-muted'}
                      >
                        {app.open_alerts}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      <span
                        className={
                          app.active_incidents > 0 ? 'text-rose-300 font-medium' : 'text-text-muted'
                        }
                      >
                        {app.active_incidents}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={clsx(
                          'rounded-full border px-2 py-0.5 text-xs font-medium capitalize',
                          riskStyle.bg,
                          riskStyle.text,
                          riskStyle.border
                        )}
                      >
                        {app.highest_severity}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {filteredApps.length === 0 && (
          <div className="px-4 py-6 text-sm text-text-muted">
            No AI apps match this governance filter.
          </div>
        )}
      </div>
    </>
  );
}
