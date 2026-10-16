/**
 * Enhanced Stats Cards Component
 * Displays key metrics with trend indicators
 */

'use client';

import { SecuritySnapshot } from '@/lib/api/orchestrator';

interface EnhancedStatsCardsProps {
  snapshot: SecuritySnapshot;
}

export default function EnhancedStatsCards({ snapshot }: EnhancedStatsCardsProps) {
  const { summary, alerts_by_severity, alerts_by_status } = snapshot;

  const stats = [
    {
      label: 'Total Alerts',
      value: summary.alerts_count,
      subtitle: `${alerts_by_status.open || 0} open`,
      color: 'text-primary',
      trend: null, // Would calculate from previous period
    },
    {
      label: 'Events Processed',
      value: summary.events_count.toLocaleString(),
      subtitle: 'Last 24 hours',
      color: 'text-primary',
      trend: null,
    },
    {
      label: 'Critical Alerts',
      value: alerts_by_severity.critical || 0,
      subtitle: 'Requires immediate attention',
      color: 'text-red-500',
      trend: null,
    },
    {
      label: 'Active Users',
      value: summary.users_active,
      subtitle: `of ${summary.users_total} total`,
      color: 'text-primary',
      trend: null,
    },
  ];

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, idx) => (
        <div
          key={idx}
          className="bg-surface-card rounded-xl border border-surface-card-border p-6"
        >
          <h3 className="text-sm font-medium text-text-muted mb-2">{stat.label}</h3>
          <p className={`text-3xl font-bold ${stat.color} mb-1`}>{stat.value}</p>
          <p className="text-xs text-text-muted">{stat.subtitle}</p>
          {stat.trend && (
            <div className="mt-2 flex items-center gap-1 text-xs">
              {stat.trend > 0 ? (
                <>
                  <span className="text-red-500">↑</span>
                  <span className="text-red-500">{stat.trend}%</span>
                </>
              ) : (
                <>
                  <span className="text-green-500">↓</span>
                  <span className="text-green-500">{Math.abs(stat.trend)}%</span>
                </>
              )}
              <span className="text-text-muted">vs previous period</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

