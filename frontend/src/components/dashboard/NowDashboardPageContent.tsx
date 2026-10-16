'use client';

import { useState, useEffect, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { listAlerts } from '@/lib/api/siem';
import Link from 'next/link';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  getOperatorOverview,
  getOperatorOverviewStreamUrl,
  normalizeOperatorOverviewResponse,
  type OperatorOverviewResponse,
} from '@/lib/api/dashboard';
import OnboardingBanner from '@/components/dashboard/OnboardingBanner';
import { PlanTierSelector } from '@/components/PlanTierSelector';
import SecurityPulseTile from '@/app/(dashboard)/dashboard/welcome/components/SecurityPulseTile';
import NowQueuePanel from '@/app/(dashboard)/dashboard/components/NowQueuePanel';
import SensorHealth from '@/app/(dashboard)/dashboard/components/SensorHealth';
import { RecentScansWidget } from '@/app/(dashboard)/dashboard/components/RecentScansWidget';
import RecommendedWorkstreamsPanel from '@/app/(dashboard)/dashboard/components/RecommendedWorkstreamsPanel';
import CoverageActionPanel from '@/app/(dashboard)/dashboard/components/CoverageActionPanel';
import TriageActionsPanel from '@/app/(dashboard)/dashboard/components/TriageActionsPanel';
import AiRiskSummaryPanel from '@/app/(dashboard)/dashboard/components/AiRiskSummaryPanel';
import SecurityGraphPreviewCard from '@/app/(dashboard)/dashboard/components/SecurityGraphPreviewCard';
import HealthBadge from '@/components/ui/HealthBadge';
import { useEventSourceStream } from '@/lib/realtime/useEventSourceStream';

export default function NowDashboardPageContent() {
  const { isAuthenticated } = useAuth();
  const [tenantId, setTenantId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTenantId = localStorage.getItem('tenant_id');
      setTenantId(storedTenantId);
    }
  }, []);

  const operatorOverviewQueryKey = useMemo(
    () => ['operator-overview', tenantId],
    [tenantId]
  );

  const operatorOverviewStream = useEventSourceStream<OperatorOverviewResponse>({
    url: tenantId ? getOperatorOverviewStreamUrl(tenantId) : null,
    enabled: isAuthenticated && !!tenantId,
    onSnapshot: (payload) => {
      if (!tenantId) {
        return;
      }
      const normalized = normalizeOperatorOverviewResponse(payload);
      queryClient.setQueryData(operatorOverviewQueryKey, normalized);
      queryClient.setQueryData(['now-queue', tenantId], normalized.now_queue);
      queryClient.setQueryData(['posture-score-dashboard', tenantId], normalized.posture_score);
      queryClient.setQueryData(['dashboard-recommendations', tenantId], normalized.recommendations);
      queryClient.setQueryData(['ai-risk-summary', tenantId], normalized.ai_risk_summary);
      queryClient.setQueryData(['source-health'], normalized.source_health);
    },
  });

  const { data: alerts, isLoading: alertsLoading } = useQuery({
    queryKey: ['alerts-recent', tenantId],
    queryFn: () => listAlerts({ limit: 5, offset: 0 }),
    enabled: isAuthenticated && !!tenantId,
  });

  const {
    data: operatorOverview,
    isLoading: operatorOverviewLoading,
    error: operatorOverviewError,
  } = useQuery({
    queryKey: operatorOverviewQueryKey,
    queryFn: () => getOperatorOverview(tenantId!),
    enabled: isAuthenticated && !!tenantId,
    staleTime: 30 * 1000,
    refetchInterval:
      operatorOverviewStream.status === 'error' || operatorOverviewStream.status === 'unsupported'
        ? 60 * 1000
        : false,
  });

  const postureScore = operatorOverview?.posture_score;
  const sourceHealth = operatorOverview?.source_health;
  const nowQueue = operatorOverview?.now_queue;
  const recommendations = operatorOverview?.recommendations;
  const aiRiskSummary = operatorOverview?.ai_risk_summary;
  const nowQueueLoading = operatorOverviewLoading;
  const nowQueueError = operatorOverviewError;
  const recommendationsLoading = operatorOverviewLoading && !recommendations;
  const aiRiskSummaryLoading = operatorOverviewLoading && !aiRiskSummary;

  const securityPulse = useMemo(() => {
    const defaultSecurityPulse = {
      overall_score: 0,
      breakdown: {
        identity: 0,
        cloud: 0,
        endpoint: 0,
        detection: 0,
      },
      breakdown_explanations: {
        identity: 'Connect an identity provider to start scoring.',
        cloud: 'Connect AWS or Azure to start scoring.',
        endpoint: 'Deploy endpoint agents to start scoring.',
        detection: 'Scores populate as connectors report findings.',
      },
      trend: {
        change: 0,
        period: 'last 7 days',
      },
      placeholder: true,
    };

    const domainVal = (domain: string) =>
      postureScore?.domain_scores?.[domain]?.score_adjusted ??
      postureScore?.domain_scores?.[domain]?.score ??
      0;

    if (postureScore) {
      return {
        overall_score: postureScore.overall_score,
        breakdown: {
          identity: domainVal('identity'),
          cloud: domainVal('cloud'),
          endpoint: domainVal('endpoint'),
          detection: domainVal('app'),
        },
        breakdown_explanations: defaultSecurityPulse.breakdown_explanations,
        trend: {
          change: 0,
          period: 'last 7 days',
        },
      };
    }

    return defaultSecurityPulse;
  }, [postureScore]);

  const postureCoverageDetails = postureScore?.coverage_details;
  const postureLastUpdated = postureScore?.last_computed_at;
  const postureStale =
    postureLastUpdated && Date.now() - new Date(postureLastUpdated).getTime() > 10 * 60 * 1000;

  return (
    <div className="p-4 sm:p-6">
      <OnboardingBanner />
      <PlanTierSelector />

      <div className="mb-6">
        <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Security Operations</p>
        <h1 className="mt-1 text-3xl font-bold text-text-main">Now</h1>
        <p className="mt-2 text-text-muted">
          One prioritized queue for incidents, detections, identity, cloud, endpoint, and AI work.
        </p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-text-muted" aria-live="polite" aria-atomic="true">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Log collection" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="Detection engine" status={sourceHealth?.siem_agent} />
          <HealthBadge label="Search index" status={sourceHealth?.opensearch} />
          <HealthBadge label="Endpoint sensors" status={sourceHealth?.wazuh} />
          <HealthBadge label="Behavior analysis" status={sourceHealth?.openedr} />
          <HealthBadge label="Threat hunting" status={sourceHealth?.velociraptor} />
        </div>
      </div>

      <div className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1.65fr),minmax(320px,0.95fr)]">
        <NowQueuePanel
          queue={nowQueue}
          isLoading={nowQueueLoading}
          error={nowQueueError instanceof Error ? nowQueueError.message : null}
        />
        <div className="space-y-6">
          <div className="rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/15 to-secondary/10 p-5 shadow-lg shadow-primary/10 backdrop-blur-md">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1">
                <p className="text-[11px] uppercase tracking-wide text-primary">Platform context</p>
                <h3 className="text-lg font-semibold text-text-main">Score, coverage, and top risks</h3>
                <p className="text-sm text-text-muted">
                  Use posture, scan, and health views to validate and close the items that rise into the Now queue.
                </p>
              </div>
              <Link
                href="/dashboard/posture"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-slate-950 shadow-sm shadow-primary/30 transition-colors hover:brightness-110"
              >
                View posture
              </Link>
            </div>
          </div>

          <AiRiskSummaryPanel
            summary={aiRiskSummary}
            isLoading={aiRiskSummaryLoading}
          />
          <SecurityGraphPreviewCard queue={nowQueue} isLoading={nowQueueLoading} />
          <SecurityPulseTile
            securityPulse={securityPulse}
            lastUpdated={postureLastUpdated}
            stale={!!postureStale}
            coverageDetails={postureCoverageDetails}
          />
          <SensorHealth health={sourceHealth} />
          <RecentScansWidget />
        </div>
      </div>

      <div className="mb-4">
        <h2 className="text-xl font-semibold text-text-main">Drive outcomes</h2>
        <p className="text-sm text-text-muted">
          Guided fixes and coverage moves backed by the same entity and evidence model as the queue.
        </p>
      </div>

      <div className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1.45fr),minmax(320px,0.95fr)]">
        <RecommendedWorkstreamsPanel
          recommendations={recommendations}
          isLoading={recommendationsLoading}
        />
        <CoverageActionPanel postureScore={postureScore} sourceHealth={sourceHealth} />
      </div>

      <div className="mb-4">
        <h2 className="text-xl font-semibold text-text-main">Keep the queue moving</h2>
        <p className="text-sm text-text-muted">
          Recent detections that still need triage, ownership, or a playbook run before they stall.
        </p>
      </div>

      <TriageActionsPanel alerts={alerts?.alerts} isLoading={alertsLoading} />
    </div>
  );
}
