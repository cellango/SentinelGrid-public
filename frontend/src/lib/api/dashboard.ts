/**
 * Dashboard API Client
 * Handles all dashboard-related API calls
 */

import { apiClient } from './client';
import type { SourceHealth } from './siem';
import type {
  CanonicalEntityRef,
  CanonicalEvidenceRef,
  CanonicalStoryDomain,
  CanonicalStorySummary,
} from '@/lib/security/story';
import {
  normalizeStoryContext,
  summarizeStoryContext,
} from '@/lib/security/story';

// ============================================================================
// Type Definitions
// ============================================================================

export interface SecurityPulse {
  overall_score: number; // 0-100
  breakdown: {
    identity: number;
    cloud: number;
    endpoint: number;
    detection: number;
  };
  breakdown_explanations: {
    identity: string;
    cloud: string;
    endpoint: string;
    detection: string;
  };
  trend?: {
    change: number;
    period: string;
  };
}

export interface OpenIncident {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  risk_level: string;
  affected_count: number;
  description?: string;
  ai_summary?: string;
  ai_proposed_fixes?: string[];
  quick_actions?: {
    label: string;
    action: string;
    endpoint?: string;
  }[];
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
  story_domains?: CanonicalStoryDomain[];
  story_summary?: CanonicalStorySummary;
  created_at: string;
}

export interface CloudPostureSnapshot {
  cloud_accounts_connected: number;
  critical_misconfigs: number;
  high_misconfigs: number;
  medium_misconfigs: number;
  low_misconfigs: number;
  total_issues: number;
  biggest_risk: {
    title: string;
    description: string;
    severity: string;
  };
  posture_score: number;
}

export interface AiRiskSummary {
  health_status: 'critical' | 'warning' | 'inactive';
  summary: string;
  lookback_days: number;
  open_alerts: number;
  active_incidents: number;
  affected_apps: number;
  affected_users: number;
  prompt_injection_alerts: number;
  data_exposure_alerts: number;
  policy_violation_alerts: number;
  severity_breakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  top_applications: Array<{
    app_id: string;
    label: string;
    open_alerts: number;
    active_incidents: number;
    highest_severity: 'critical' | 'high' | 'medium' | 'low';
  }>;
  top_risk?: {
    item_type: 'incident' | 'alert';
    id: string;
    title: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    summary: string;
    href: string;
  } | null;
  priority_actions: Array<{
    label: string;
    href: string;
  }>;
}

export interface PeopleAccessSnapshot {
  users_total: number;
  users_admins: number;
  mfa_coverage_percent: number;
  mfa_missing_count: number;
  dormant_accounts_count: number;
  fast_win?: {
    title: string;
    description: string;
    action: string;
  };
}

export interface DashboardHealth {
  log_usage: {
    current_gb_per_day: number;
    limit_gb_per_day: number;
    percentage_used: number;
  };
  agents: {
    online: number;
    total: number;
    percentage_online: number;
  };
  integrations: {
    aws: 'connected' | 'partial' | 'disconnected';
    idp: 'connected' | 'partial' | 'disconnected';
    endpoint: 'connected' | 'partial' | 'disconnected';
  };
  health_status: 'healthy' | 'degraded' | 'critical';
}

export interface Recommendation {
  id: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  description: string;
  estimated_time_minutes: number;
  finding_class?: string;
  remediation?: {
    class_id: string;
    title: string;
    owner: string;
    why_now: string;
    success_criteria: string;
    steps: {
      title: string;
      description: string;
    }[];
  };
  actions: {
    label: string;
    type: 'fix_now' | 'open_ticket' | 'dismiss' | 'view_details';
    endpoint?: string;
    playbook_id?: string;
  }[];
  category: string;
}

export interface FirstValueFinding {
  id: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  eyebrow: string;
  title: string;
  description: string;
  href: string;
  cta_label: string;
  category: string;
}

export interface DashboardSnapshot {
  tenant_id: string;
  generated_at: string;
  security_pulse: SecurityPulse;
  open_incidents: OpenIncident[];
  cloud_posture: CloudPostureSnapshot;
  ai_risk?: AiRiskSummary;
  people_access: PeopleAccessSnapshot;
  health: DashboardHealth;
  recommendations: Recommendation[];
  first_value?: {
    findings: FirstValueFinding[];
  };
}

export interface NowQueueItem {
  id: string;
  item_type: 'incident' | 'alert' | 'recommendation';
  priority: 'critical' | 'high' | 'medium' | 'low';
  title: string;
  summary: string;
  why_now: string;
  status?: string;
  owner?: string;
  source_label: string;
  href: string;
  action_label: string;
  action_href: string;
  updated_at?: string | null;
  estimated_time_minutes?: number;
  domains: CanonicalStoryDomain[];
  entities: CanonicalEntityRef[];
  evidence: CanonicalEvidenceRef[];
  story_summary?: CanonicalStorySummary;
  sla?: string | number | null;
}

export interface NowQueueSummary {
  total_items: number;
  urgent_items: number;
  incidents: number;
  alerts: number;
  recommendations: number;
  domains: Array<{
    domain: CanonicalStoryDomain;
    count: number;
  }>;
}

export interface NowQueueResponse {
  tenant_id: string;
  generated_at: string;
  items: NowQueueItem[];
  summary: NowQueueSummary;
}

export interface OperatorOverviewResponse {
  tenant_id: string;
  generated_at: string;
  posture_score: PostureScore;
  now_queue: NowQueueResponse;
  recommendations: Recommendation[];
  ai_risk_summary: AiRiskSummary;
  source_health: SourceHealth;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get comprehensive dashboard snapshot
 */
export async function getDashboardSnapshot(tenantId: string): Promise<DashboardSnapshot> {
  const response = await apiClient.get<DashboardSnapshot>(
    `/orchestrator/tenant/${tenantId}/dashboard-snapshot`
  );
  return response.data;
}

export interface PostureScore {
  overall_score: number;
  domain_scores: Record<
    string,
    {
      score?: number;
      score_adjusted?: number;
      coverage?: number;
      risk?: number;
      open?: number;
      counts?: Record<string, number>;
    }
  >;
  top_risks: {
    id?: string;
    title: string;
    severity: string;
    domain: string;
    exposed?: boolean;
    criticality?: string | null;
    data_classification?: string | null;
  }[];
  last_computed_at?: string;
  coverage?: Record<string, number>;
  coverage_details?: Record<string, { scanned: number; total: number }>;
  incident_penalty?: number;
}

export async function getPostureScore(tenantId: string): Promise<PostureScore> {
  const response = await apiClient.get<PostureScore>(
    `/orchestrator/tenant/${tenantId}/posture-score`
  );
  return response.data;
}

/**
 * Get IAM/People & Access snapshot
 */
export async function getPeopleAccessSnapshot(tenantId: string): Promise<PeopleAccessSnapshot> {
  const response = await apiClient.get<PeopleAccessSnapshot>(
    `/iam/dashboard-snapshot`
  );
  return response.data;
}

/**
 * Get cloud posture snapshot
 */
export async function getCloudPostureSnapshot(tenantId: string): Promise<CloudPostureSnapshot> {
  const response = await apiClient.get<CloudPostureSnapshot>(
    `/posture/dashboard-snapshot`
  );
  return response.data;
}

export async function getAiRiskSummary(tenantId: string): Promise<AiRiskSummary> {
  const response = await apiClient.get<AiRiskSummary>(
    `/orchestrator/tenant/${tenantId}/ai-risk-summary`
  );
  return response.data;
}

/**
 * Get open incidents with actions
 */
export async function getOpenIncidents(tenantId: string): Promise<OpenIncident[]> {
  const response = await apiClient.get<{ items: OpenIncident[] }>(
    `/incidents/open-with-actions`
  );
  return (response.data.items || []).map((incident: any) => {
    const storyContext = normalizeStoryContext({
      rawPayload: incident.raw_payload,
      entities: incident.entities,
      evidence: incident.evidence,
      storyDomains: incident.story_domains,
    });
    const storySummary = incident.story_summary || summarizeStoryContext(storyContext);
    return {
      ...incident,
      entities: storyContext.entities,
      evidence: storyContext.evidence,
      story_domains: storyContext.story_domains,
      story_summary: storySummary,
      affected_count: incident.affected_count || Math.max(storySummary.entity_count, 1),
      description: incident.description || storySummary.detail,
    };
  });
}

/**
 * Get dashboard health and usage stats
 */
export async function getDashboardHealth(tenantId: string): Promise<DashboardHealth> {
  const response = await apiClient.get<DashboardHealth>(
    `/orchestrator/tenant/${tenantId}/dashboard-health`
  );
  return response.data;
}

/**
 * Get AI-generated recommendations
 */
export async function getRecommendations(tenantId: string): Promise<Recommendation[]> {
  const response = await apiClient.get<{ recommendations: Recommendation[] }>(
    `/orchestrator/tenant/${tenantId}/recommendations`
  );
  return response.data.recommendations;
}

export function normalizeNowQueueResponse(data: NowQueueResponse): NowQueueResponse {
  return {
    ...data,
    items: (data.items || []).map((item: any) => ({
      ...item,
      story_summary:
        item.story_summary ||
        summarizeStoryContext({
          entities: item.entities,
          evidence: item.evidence,
          story_domains: item.domains,
        }),
    })),
  };
}

export function normalizeOperatorOverviewResponse(
  data: OperatorOverviewResponse
): OperatorOverviewResponse {
  return {
    ...data,
    now_queue: normalizeNowQueueResponse(data.now_queue),
  };
}

export async function getNowQueue(tenantId: string): Promise<NowQueueResponse> {
  const response = await apiClient.get<NowQueueResponse>(
    `/orchestrator/tenant/${tenantId}/now-queue`
  );
  return normalizeNowQueueResponse(response.data);
}

export async function getOperatorOverview(tenantId: string): Promise<OperatorOverviewResponse> {
  const response = await apiClient.get<OperatorOverviewResponse>(
    `/orchestrator/tenant/${tenantId}/operator-overview`
  );
  return normalizeOperatorOverviewResponse(response.data);
}

export function getNowQueueStreamUrl(tenantId: string): string {
  return `/api/v1/orchestrator/tenant/${tenantId}/now-queue/stream`;
}

export function getOperatorOverviewStreamUrl(tenantId: string): string {
  return `/api/v1/orchestrator/tenant/${tenantId}/operator-overview/stream`;
}
