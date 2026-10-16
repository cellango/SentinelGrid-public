/**
 * Dashboard Data Hook
 * Fetches all dashboard data in parallel
 */

import { useQuery } from '@tanstack/react-query';
import {
  getDashboardSnapshot,
  getPeopleAccessSnapshot,
  getCloudPostureSnapshot,
  getOpenIncidents,
  getDashboardHealth,
  getRecommendations,
  getPostureScore,
  type DashboardSnapshot,
  type PeopleAccessSnapshot,
  type CloudPostureSnapshot,
  type DashboardHealth,
  type Recommendation,
  type OpenIncident,
  type PostureScore,
} from '@/lib/api/dashboard';
import { apiClient } from '@/lib/api/client';

function hasMeaningfulCloudPosture(data?: CloudPostureSnapshot) {
  if (!data) return false;
  return (
    data.cloud_accounts_connected > 0 ||
    data.total_issues > 0 ||
    data.critical_misconfigs > 0 ||
    (data.biggest_risk?.title || '').length > 0
  );
}

function hasMeaningfulPeopleAccess(data?: PeopleAccessSnapshot) {
  if (!data) return false;
  return data.users_total > 0 || data.mfa_missing_count > 0 || data.users_admins > 0;
}

function hasMeaningfulHealth(data?: DashboardHealth) {
  if (!data) return false;
  return (
    data.agents.total > 0 ||
    data.agents.online > 0 ||
    data.integrations.aws !== 'disconnected' ||
    data.integrations.idp !== 'disconnected' ||
    data.integrations.endpoint !== 'disconnected'
  );
}

export function useDashboardData(tenantId: string | null) {
  // Fetch all dashboard data in parallel
  const dashboardSnapshot = useQuery<DashboardSnapshot>({
    queryKey: ['dashboard-snapshot', tenantId],
    queryFn: () => getDashboardSnapshot(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000,
  });

  const peopleAccess = useQuery<PeopleAccessSnapshot>({
    queryKey: ['people-access-snapshot', tenantId],
    queryFn: () => getPeopleAccessSnapshot(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000,
  });

  const cloudPosture = useQuery<CloudPostureSnapshot>({
    queryKey: ['cloud-posture-snapshot', tenantId],
    queryFn: () => getCloudPostureSnapshot(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000,
  });

  const postureScore = useQuery<PostureScore>({
    queryKey: ['posture-score', tenantId],
    queryFn: () => getPostureScore(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000,
  });

  const postureHistory = useQuery<{ items: any[] }>({
    queryKey: ['posture-score-history', tenantId],
    queryFn: async () => {
      const res = await apiClient.get<{ items: any[] }>(
        `/orchestrator/tenant/${tenantId}/posture-score/history?limit=14`
      );
      return res.data;
    },
    enabled: !!tenantId,
    refetchInterval: 10 * 60 * 1000,
  });

  const incidents = useQuery<OpenIncident[]>({
    queryKey: ['open-incidents', tenantId],
    queryFn: () => getOpenIncidents(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes
  });

  const health = useQuery<DashboardHealth>({
    queryKey: ['dashboard-health', tenantId],
    queryFn: () => getDashboardHealth(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000,
  });

  const recommendations = useQuery<Recommendation[]>({
    queryKey: ['recommendations', tenantId],
    queryFn: () => getRecommendations(tenantId!),
    enabled: !!tenantId,
    refetchInterval: 10 * 60 * 1000, // Refetch every 10 minutes
  });

  const isLoading =
    dashboardSnapshot.isLoading ||
    postureScore.isLoading ||
    peopleAccess.isLoading ||
    cloudPosture.isLoading ||
    incidents.isLoading ||
    health.isLoading ||
    recommendations.isLoading;

  const hasError =
    dashboardSnapshot.isError ||
    postureScore.isError ||
    peopleAccess.isError ||
    cloudPosture.isError ||
    incidents.isError ||
    health.isError ||
    recommendations.isError;

  // Determine if we have any data (for empty state)
  const hasData =
    dashboardSnapshot.data ||
    postureScore.data ||
    peopleAccess.data ||
    cloudPosture.data ||
    (incidents.data && incidents.data.length > 0) ||
    health.data ||
    (recommendations.data && recommendations.data.length > 0);

  const resolvedCloudPosture = hasMeaningfulCloudPosture(cloudPosture.data)
    ? cloudPosture.data
    : dashboardSnapshot.data?.cloud_posture;
  const resolvedPeopleAccess = hasMeaningfulPeopleAccess(peopleAccess.data)
    ? peopleAccess.data
    : dashboardSnapshot.data?.people_access;
  const resolvedHealth = hasMeaningfulHealth(health.data)
    ? health.data
    : dashboardSnapshot.data?.health;
  const resolvedRecommendations =
    recommendations.data && recommendations.data.length > 0
      ? recommendations.data
      : dashboardSnapshot.data?.recommendations || [];
  const resolvedIncidents =
    incidents.data && incidents.data.length > 0
      ? incidents.data
      : dashboardSnapshot.data?.open_incidents || [];

  return {
    // Individual data
    dashboardSnapshot: dashboardSnapshot.data,
    postureScore: postureScore.data,
    peopleAccess: resolvedPeopleAccess,
    cloudPosture: resolvedCloudPosture,
    incidents: resolvedIncidents,
    health: resolvedHealth,
    recommendations: resolvedRecommendations,

    // Loading states
    isLoading,
    hasError,
    hasData,
    postureHistory: postureHistory.data?.items || [],

    // Refetch function
    refetch: () => {
      dashboardSnapshot.refetch();
      postureScore.refetch();
      postureHistory.refetch();
      peopleAccess.refetch();
      cloudPosture.refetch();
      incidents.refetch();
      health.refetch();
      recommendations.refetch();
    },
  };
}
