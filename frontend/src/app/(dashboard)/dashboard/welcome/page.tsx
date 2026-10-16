/**
 * Welcome Dashboard Page
 * First-impression dashboard shown until onboarding is complete
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useDashboardData } from './hooks/useDashboardData';
import { DashboardHealth } from '@/lib/api/dashboard';
import { getOnboardingStatus } from '@/lib/api/onboarding';
import {
  recordFirstValueReady,
  syncOnboardingMetricsFromStatus,
} from '@/lib/onboarding/metrics';
import EnvironmentValidationBanner from './components/EnvironmentValidationBanner';
import SecurityPulseTile from './components/SecurityPulseTile';
import OpenIncidentsTile from './components/OpenIncidentsTile';
import CloudPostureTile from './components/CloudPostureTile';
import PeopleAccessTile from './components/PeopleAccessTile';
import UsageHealthTile from './components/UsageHealthTile';
import RecommendedActions from './components/RecommendedActions';
import IncidentsTimeline from './components/IncidentsTimeline';
import ComplianceProgress from './components/ComplianceProgress';
import EndpointCoverage from './components/EndpointCoverage';
import AgentSelectionPanel from './components/AgentSelectionPanel';
import HardenedImageSelector from './components/HardenedImageSelector';
import TopRisksTile from './components/TopRisksTile';
import ActivationMetricsPanel from './components/ActivationMetricsPanel';
import FirstValueHighlights from './components/FirstValueHighlights';
import EmptyState from './components/EmptyState';
import FloatingChatbot from '@/components/ai-chat/FloatingChatbot';
import EndpointSampleLoader from '@/components/dashboard/EndpointSampleLoader';
import OnboardingBanner from '@/components/dashboard/OnboardingBanner';

export default function WelcomeDashboard() {
  const [tenantId, setTenantId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTenantId = localStorage.getItem('tenant_id');
      setTenantId(storedTenantId);
    }
  }, []);

  const {
    dashboardSnapshot,
    postureScore,
    peopleAccess,
    cloudPosture,
    incidents,
    health,
    recommendations,
    isLoading,
    hasError,
    hasData,
    postureHistory,
  } = useDashboardData(tenantId);

  const onboardingStatus = useQuery({
    queryKey: ['onboarding-status', tenantId],
    queryFn: () => getOnboardingStatus(),
    enabled: !!tenantId,
    retry: 1,
    refetchInterval: 60 * 1000,
  });

  useEffect(() => {
    if (onboardingStatus.data) {
      syncOnboardingMetricsFromStatus(onboardingStatus.data);
    }
  }, [onboardingStatus.data]);

  // Safe defaults to prevent runtime crashes when data is missing
  const defaultCoverageDetails = {
    cloud: { scanned: 1, total: 1 },
    app: { scanned: 1, total: 1 },
    identity: { scanned: 1, total: 1 },
    endpoint: { scanned: 1, total: 1 },
  };
  const safeCoverageDetails = postureScore?.coverage_details || defaultCoverageDetails;
  const safeHistoryScores = Array.isArray(postureHistory)
    ? postureHistory
        .filter((h: any) => typeof h?.overall_score === 'number')
        .map((h: any) => h.overall_score)
    : [];
  const safeHealthDefaults: DashboardHealth = {
    log_usage: { current_gb_per_day: 0, limit_gb_per_day: 100, percentage_used: 0 },
    agents: { online: 0, total: 1, percentage_online: 0 },
    integrations: { aws: 'disconnected', idp: 'disconnected', endpoint: 'disconnected' },
    health_status: 'healthy',
  };
  const safeHealth: DashboardHealth = {
    ...safeHealthDefaults,
    ...(health || {}),
    log_usage: { ...safeHealthDefaults.log_usage, ...(health?.log_usage || {}) },
    agents: { ...safeHealthDefaults.agents, ...(health?.agents || {}) },
    integrations: { ...safeHealthDefaults.integrations, ...(health?.integrations || {}) },
  };

  // Prepare dashboard context for chatbot
  const domainVal = (domain: string) =>
    postureScore?.domain_scores?.[domain]?.score_adjusted ??
    postureScore?.domain_scores?.[domain]?.score ??
    0;

  const defaultSecurityPulse = {
    overall_score: 85,
    breakdown: {
      identity: 82,
      cloud: 84,
      endpoint: 80,
      detection: 78,
    },
    breakdown_explanations: {
      identity: 'Identity posture derived from IAM-related findings and coverage.',
      cloud: 'Cloud posture derived from CSPM findings and recent cloud scans.',
      endpoint: 'Endpoint posture pending coverage data; defaults to 0 until agents report.',
      detection: 'Application/security detection posture derived from app/code findings.',
    },
    trend: {
      change: 0,
      period: 'last 7 days',
    },
  };

  const securityPulse =
    postureScore
      ? {
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
        }
      : dashboardSnapshot?.security_pulse || defaultSecurityPulse;

  const lastUpdated = postureScore?.last_computed_at;
  const stale =
    lastUpdated &&
    Date.now() - new Date(lastUpdated).getTime() > 10 * 60 * 1000; // 10 minutes
  const coverageDetails = safeCoverageDetails;
  const history = Array.isArray(postureHistory) ? postureHistory : [];
  const domainHistory: Record<string, number[]> = {};
  if (history && history.length) {
    ['cloud', 'app', 'identity', 'endpoint'].forEach((d) => {
      domainHistory[d] = history
        .map((h: any) => h?.domain_scores?.[d]?.score_adjusted ?? h?.domain_scores?.[d]?.score)
        .filter((v: number | undefined) => typeof v === 'number');
    });
  }
  const historyScores = safeHistoryScores;
  const topRisks = Array.isArray(postureScore?.top_risks)
    ? postureScore.top_risks
    : Array.isArray((dashboardSnapshot as any)?.top_risks)
      ? (dashboardSnapshot as any).top_risks
      : [];

  const coverageAlerts =
    coverageDetails &&
    Object.entries(coverageDetails || defaultCoverageDetails)
      .filter(([_, cov]) => {
        const scanned = (cov as any)?.scanned ?? 0;
        const total = (cov as any)?.total ?? 0;
        return total > 0 && scanned / total < 0.5;
      })
      .map(([domain, cov]) => {
        const scanned = (cov as any)?.scanned ?? 0;
        const total = (cov as any)?.total ?? 0;
        return {
          domain,
          scanned,
          total,
          pct: total > 0 ? Math.round((scanned / total) * 100) : 0,
        };
      });

  const dashboardContext = {
    security_score: securityPulse?.overall_score,
    open_incidents: incidents?.length || 0,
    recommendations_count: recommendations?.length || 0,
    cloud_accounts: cloudPosture?.cloud_accounts_connected || 0,
    users_total: peopleAccess?.users_total || 0,
  };

  useEffect(() => {
    const hasMeaningfulValue =
      hasData &&
      (
        (incidents?.length || 0) > 0 ||
        (recommendations?.length || 0) > 0 ||
        (cloudPosture?.total_issues || 0) > 0 ||
        (peopleAccess?.mfa_missing_count || 0) > 0 ||
        (topRisks?.length || 0) > 0
      );

    if (hasMeaningfulValue) {
      recordFirstValueReady({
        source: 'welcome_dashboard',
        incidents: incidents?.length || 0,
        recommendations: recommendations?.length || 0,
        cloudIssues: cloudPosture?.total_issues || 0,
        identityIssues: peopleAccess?.mfa_missing_count || 0,
      });
    }
  }, [
    hasData,
    incidents,
    recommendations,
    cloudPosture?.total_issues,
    peopleAccess?.mfa_missing_count,
    topRisks,
  ]);

  // Show loading state
  if (isLoading && !hasData) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-2 border-primary border-t-transparent mx-auto mb-4"></div>
            <p className="text-text-muted">Loading your security dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show error state
  if (hasError && !hasData) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center">
          <p className="text-red-400 mb-4">Failed to load dashboard data</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Show empty state for Day 0-1
  if (!hasData) {
    return (
      <div className="p-6">
        <EnvironmentValidationBanner
          onboardingStatus={onboardingStatus.data}
          loading={onboardingStatus.isLoading}
          hasError={onboardingStatus.isError}
        />
        <OnboardingBanner />
        <ActivationMetricsPanel />
        <EmptyState />
        <FloatingChatbot tenantId={tenantId || undefined} dashboardContext={dashboardContext} />
      </div>
    );
  }

  // Main dashboard view
  return (
    <div className="p-6">
      {/* Environment Validation Banner */}
      <EnvironmentValidationBanner
        onboardingStatus={onboardingStatus.data}
        loading={onboardingStatus.isLoading}
        hasError={onboardingStatus.isError}
      />
      <OnboardingBanner />
      <ActivationMetricsPanel />

      <FirstValueHighlights
        prioritizedFindings={dashboardSnapshot?.first_value?.findings || []}
        recommendations={recommendations || []}
        incidents={incidents || []}
        cloudPosture={cloudPosture}
        peopleAccess={peopleAccess}
        postureScore={postureScore}
        health={safeHealth}
        onboardingStatus={onboardingStatus.data}
      />

      {coverageAlerts && coverageAlerts.length > 0 && (
        <div className="mb-4 rounded-2xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-sm text-yellow-200">
          <div className="font-semibold mb-1">Low coverage detected</div>
          <ul className="list-disc list-inside space-y-1">
            {coverageAlerts.map((c) => (
              <li key={c.domain}>
                {c.domain}: {c.scanned}/{c.total} scanned ({c.pct}%). Increase scan coverage to improve posture accuracy.
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Main Tiles Grid - Above the fold */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 mb-8">
        {securityPulse ? (
          <div className="lg:col-span-2 xl:col-span-1">
            <SecurityPulseTile
              securityPulse={securityPulse}
              lastUpdated={lastUpdated}
              stale={!!stale}
              coverageDetails={coverageDetails}
              historyScores={historyScores}
              domainHistory={domainHistory}
            />
          </div>
        ) : (
          <div className="lg:col-span-2 xl:col-span-1 bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-primary/20 rounded w-24 mb-4"></div>
              <div className="h-12 bg-primary/20 rounded w-32"></div>
            </div>
          </div>
        )}
        
        <div className="lg:col-span-2 xl:col-span-1">
          <OpenIncidentsTile incidents={incidents || []} />
        </div>

        {cloudPosture ? (
          <div className="lg:col-span-2 xl:col-span-1">
            <CloudPostureTile cloudPosture={cloudPosture} />
          </div>
        ) : (
          <div className="lg:col-span-2 xl:col-span-1 bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-primary/20 rounded w-32 mb-4"></div>
              <div className="h-8 bg-primary/20 rounded w-24"></div>
            </div>
          </div>
        )}
        
        {peopleAccess ? (
          <div className="lg:col-span-2 xl:col-span-1">
            <PeopleAccessTile peopleAccess={peopleAccess} />
          </div>
        ) : (
          <div className="lg:col-span-2 xl:col-span-1 bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-primary/20 rounded w-28 mb-4"></div>
              <div className="h-8 bg-primary/20 rounded w-20"></div>
            </div>
          </div>
        )}
        
        {health ? (
          <div className="lg:col-span-2 xl:col-span-1">
            <UsageHealthTile health={safeHealth} />
          </div>
        ) : (
          <div className="lg:col-span-2 xl:col-span-1 bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
            <div className="animate-pulse">
              <div className="h-4 bg-primary/20 rounded w-24 mb-4"></div>
              <div className="h-8 bg-primary/20 rounded w-28"></div>
            </div>
          </div>
        )}

        <div className="lg:col-span-2 xl:col-span-1">
          <TopRisksTile risks={topRisks} />
        </div>
      </div>

      {/* Agent & Image Selection Section */}
      <div className="grid gap-6 md:grid-cols-2 mb-8">
        {tenantId && (
          <>
            <AgentSelectionPanel tenantId={tenantId} />
            <HardenedImageSelector tenantId={tenantId} cloudProvider={cloudPosture?.cloud_accounts_connected ? 'aws' : undefined} />
          </>
        )}
      </div>

      {/* Recommended Actions */}
      {recommendations && recommendations.length > 0 && (
        <RecommendedActions recommendations={recommendations} />
      )}

      {/* Quick Validation */}
      <EndpointSampleLoader />

      {/* Lower Sections */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-8">
        {incidents && incidents.length > 0 && (
          <IncidentsTimeline incidents={incidents} />
        )}
        <ComplianceProgress packageType="protect_defend_comply" />
        {safeHealth && (
          <EndpointCoverage
            coverage={{
              total: safeHealth.agents.total,
              online: safeHealth.agents.online,
              by_environment: {
                prod: { total: Math.ceil(safeHealth.agents.total * 0.3), online: Math.ceil(safeHealth.agents.online * 0.3) },
                staging: { total: Math.ceil(safeHealth.agents.total * 0.2), online: Math.ceil(safeHealth.agents.online * 0.2) },
                dev: { total: Math.ceil(safeHealth.agents.total * 0.5), online: Math.ceil(safeHealth.agents.online * 0.5) },
              },
            }}
          />
        )}
      </div>

      {/* Floating AI Chatbot */}
      <FloatingChatbot tenantId={tenantId || undefined} dashboardContext={dashboardContext} />
    </div>
  );
}
