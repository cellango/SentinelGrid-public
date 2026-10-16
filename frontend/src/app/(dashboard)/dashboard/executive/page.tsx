/**
 * Executive Dashboard (CISO/Executive View)
 * Focus: Risk scores, compliance status, trends, high-level metrics
 */

'use client';

import { useState, useEffect } from 'react';
import { useSecuritySnapshot } from '../hooks/useSecuritySnapshot';
import SecuritySnapshotPanel from '../components/SecuritySnapshotPanel';
import AIInsightsWidget from '../components/AIInsightsWidget';
import EnhancedStatsCards from '../components/EnhancedStatsCards';
import ActivityTimeline from '../components/ActivityTimeline';
import { useQuery } from '@tanstack/react-query';
import { getSourceHealth, SourceHealth } from '@/lib/api/siem';
import Link from 'next/link';
import HealthBadge from '@/components/ui/HealthBadge';

export default function ExecutiveDashboard() {
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [needsAuth, setNeedsAuth] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTenantId = localStorage.getItem('tenant_id');
      setTenantId(storedTenantId);
    }
  }, []);

  const {
    data: snapshot,
    isLoading: snapshotLoading,
    error: snapshotError,
  } = useSecuritySnapshot(tenantId);
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
        <h1 className="text-2xl font-bold text-text-main mb-2">Executive Dashboard</h1>
        <p className="text-text-muted">High-level security posture and risk overview</p>
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

      {snapshotLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
        </div>
      ) : snapshotError ? (
        <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-6 text-red-400">
          Failed to load security snapshot. Please try again later.
        </div>
      ) : snapshot ? (
        <>
          {/* Top: Security Posture & Key Metrics */}
          <div className="mb-8">
            <SecuritySnapshotPanel snapshot={snapshot as any} />
          </div>

          {/* Stats Cards */}
          <div className="mb-8">
            <EnhancedStatsCards snapshot={snapshot as any} />
          </div>

          {/* Main Content: AI Insights and Timeline */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div>
              <AIInsightsWidget snapshot={snapshot as any} />
            </div>
            <div>
              <ActivityTimeline snapshot={snapshot as any} />
            </div>
          </div>
        </>
      ) : (
        <div className="text-text-muted">No data available. Please configure your security integrations.</div>
      )}
    </div>
  );
}
