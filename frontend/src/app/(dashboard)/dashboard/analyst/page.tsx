/**
 * Analyst Dashboard (SOC Analyst View)
 * Focus: Active alerts, playbooks, investigations, triage tools
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSecuritySnapshot } from '../hooks/useSecuritySnapshot';
import { listAlerts, getSourceHealth, SourceHealth } from '@/lib/api/siem';
import Link from 'next/link';
import TopFindingsWidget from '../components/TopFindingsWidget';
import HealthBadge from '@/components/ui/HealthBadge';

export default function AnalystDashboard() {
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTenantId = localStorage.getItem('tenant_id');
      setTenantId(storedTenantId);
    }
  }, []);

  const { data: snapshot } = useSecuritySnapshot(tenantId);

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts-active'],
    queryFn: () => listAlerts({ limit: 20, offset: 0, status: 'open' }),
  });
  const { data: sourceHealth, error: sourceHealthError } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  useEffect(() => {
    if (sourceHealthError) {
      const err: any = sourceHealthError;
      const status = err?.response?.status || err?.status;
      if (status === 401 || status === 403) setNeedsAuth(true);
    }
  }, [sourceHealthError]);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main mb-2">Analyst Dashboard</h1>
        <p className="text-text-muted">Active alerts, investigations, and triage tools</p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-muted">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
          <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
          {needsAuth && (
            <Link href="/login" className="underline text-primary">
              Session expired? Sign in again.
            </Link>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-6 md:grid-cols-3 mb-8">
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <h2 className="text-lg font-semibold mb-2 text-text-main">My Alerts</h2>
          <p className="text-3xl font-bold text-primary">
            {alerts?.alerts?.filter((a) => a.status === 'open').length || 0}
          </p>
          <p className="text-sm text-text-muted mt-2">Assigned to me</p>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <h2 className="text-lg font-semibold mb-2 text-text-main">Pending Triage</h2>
          <p className="text-3xl font-bold text-orange-500">
            {alerts?.alerts?.filter((a) => a.status === 'open').length || 0}
          </p>
          <p className="text-sm text-text-muted mt-2">Awaiting analysis</p>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <h2 className="text-lg font-semibold mb-2 text-text-main">Resolved Today</h2>
          <p className="text-3xl font-bold text-green-500">12</p>
          <p className="text-sm text-text-muted mt-2">Last 24 hours</p>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-3 mb-8">
        {/* Top Findings */}
        {snapshot && (
          <div className="lg:col-span-2">
            <TopFindingsWidget snapshot={snapshot as any} />
          </div>
        )}

        {/* Quick Actions */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <h2 className="text-xl font-semibold mb-4 text-text-main">Quick Actions</h2>
          <div className="space-y-2">
            <Link
              href="/dashboard/alerts?status=open"
              className="block px-4 py-2 rounded-lg border border-surface-card hover:border-primary/30 text-text-main transition-colors"
            >
              View Open Alerts
            </Link>
            <Link
              href="/dashboard/playbooks"
              className="block px-4 py-2 rounded-lg border border-surface-card hover:border-primary/30 text-text-main transition-colors"
            >
              Browse Playbooks
            </Link>
            <Link
              href="/dashboard/incidents"
              className="block px-4 py-2 rounded-lg border border-surface-card hover:border-primary/30 text-text-main transition-colors"
            >
              Active Incidents
            </Link>
            <Link
              href="/dashboard/chat"
              className="block px-4 py-2 rounded-lg border border-surface-card hover:border-primary/30 text-text-main transition-colors"
            >
              SOC Copilot
            </Link>
          </div>
        </div>
      </div>

      {/* Active Alerts List */}
      <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-text-main">Active Alerts</h2>
          <Link
            href="/dashboard/alerts?status=open"
            className="text-sm text-primary hover:text-primary/80"
          >
            View all
          </Link>
        </div>
        {alertsLoading ? (
          <p className="text-text-muted">Loading alerts...</p>
        ) : alerts?.alerts && alerts.alerts.length > 0 ? (
          <div className="space-y-3">
            {alerts.alerts.map((alert) => (
              <Link
                key={alert.id}
                href={`/dashboard/alerts/${alert.id}`}
                className="block p-3 rounded-lg border border-surface-card hover:border-primary/30 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-text-main">{alert.title}</span>
                  <span
                    className={`px-2 py-0.5 text-xs font-semibold rounded ${
                      alert.severity === 'critical'
                        ? 'bg-red-500/20 text-red-500'
                        : alert.severity === 'high'
                        ? 'bg-orange-500/20 text-orange-500'
                        : 'bg-yellow-500/20 text-yellow-500'
                    }`}
                  >
                    {alert.severity}
                  </span>
                </div>
                <p className="text-xs text-text-muted line-clamp-2">{alert.description}</p>
                <div className="mt-2 flex items-center gap-4 text-xs text-text-muted">
                  <span>Created: {new Date(alert.created_at).toLocaleString()}</span>
                  {alert.status && <span>Status: {alert.status}</span>}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-text-muted">No active alerts</p>
        )}
      </div>
    </div>
  );
}
