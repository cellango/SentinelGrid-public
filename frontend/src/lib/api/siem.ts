/**
 * SIEM Agent API Client
 * Handles alerts, logs, and search operations
 */

import { apiClient } from './client';
import {
  type CanonicalEntityRef,
  type CanonicalEvidenceRef,
  type CanonicalStoryDomain,
  type CanonicalStorySummary,
  normalizeStoryContext,
  summarizeStoryContext,
} from '@/lib/security/story';

export interface Alert {
  id: string;
  tenant_id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  raw_severity?: string;
  status: 'open' | 'acknowledged' | 'resolved' | 'false_positive' | 'investigating';
  title: string;
  description?: string;
  timestamp?: string;
  detection_time?: string;
  first_seen?: string;
  last_seen?: string;
  source: string; // detection_rule_id, manual, external
  source_ip?: string;
  external_id?: string;
  user_id?: string;
  user_identifier?: string;
  detection_rule_id?: string;
  detection_rule_version_id?: string;
  playbook_version_id?: string;
  asset_id?: string;
  events?: string[];
  count?: number;
  created_at: string;
  updated_at: string;
  nist_controls?: any;
  mitre_tactics?: any;
  mitre_techniques?: any;
  cve_ids?: string[];
  exploit_indicators?: any;
  raw_payload?: any;
  category?: string;
  control_tags?: string[];
  mitre_tactic?: string;
  mitre_technique?: string;
  recommended_playbook?: string;
  recommended_playbook_id?: string;
  recommended_playbook_key?: string;
  control_gap?: 'covered' | 'partial' | 'gap';
  assigned_to?: string;
  due_date?: string | null;
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
  story_domains?: CanonicalStoryDomain[];
  story_summary?: CanonicalStorySummary;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface AlertListParams {
  limit?: number;
  offset?: number;
  status?: string;
  severity?: string;
  sort?: string;
}

export interface Event {
  id: string;
  '@timestamp': string;
  tenant_id: string;
  event_type: string;
  source: {
    name: string;
    type: string;
    ip?: string;
  };
  action?: string;
  outcome?: string;
  user?: {
    id?: string;
    email?: string;
    name?: string;
  };
  host?: {
    hostname?: string;
    ip?: string;
  };
}

export interface LogEvent {
  id?: string;
  '@timestamp': string;
  edr_source?: string;
  sidecar_enabled?: boolean;
  event?: {
    category?: string[] | string;
    type?: string[] | string;
    action?: string;
    outcome?: string;
  };
  sg?: { tenant_id?: string };
  source?: { ip?: string; address?: string; type?: string; name?: string };
  destination?: { ip?: string; port?: number };
  network?: { bytes?: number; transport?: string; direction?: string };
  user?: { id?: string; email?: string; name?: string };
  host?: { hostname?: string; id?: string; ip?: string };
  cloud?: { provider?: string; account?: { id?: string } };
  ai?: Record<string, any>;
  identity?: Record<string, any>;
  [key: string]: any;
}

export interface LogSearchResponse {
  hits: LogEvent[];
  total: number;
  took?: number;
  limit?: number;
  offset?: number;
}

export interface SIEMStats {
  events_count: number;
  alerts_count: number;
  alerts_by_severity: Record<string, number>;
  alerts_by_status: Record<string, number>;
}

export interface LogSearchParams {
  q: string;
  event_type?: string;
  start_time?: string;
  end_time?: string;
  limit?: number;
  offset?: number;
}

export async function searchLogsSimple(params: LogSearchParams): Promise<LogSearchResponse> {
  const response = await apiClient.get('/siem/logs/search/simple', { params });
  const data = response.data || {};
  const hits = data.events || data.hits || data.items || [];
  return {
    hits,
    total: data.total ?? data.events?.length ?? hits.length,
    took: data.took ?? data.took_ms,
    limit: data.limit ?? params.limit,
    offset: data.offset ?? params.offset,
  };
}

export async function searchLogsAdvanced(body: any, params?: { start_time?: string; end_time?: string; limit?: number; offset?: number }): Promise<LogSearchResponse> {
  const response = await apiClient.post('/siem/logs/search', body, { params });
  const data = response.data || {};
  const hits = data.hits || data.items || [];
  return {
    hits,
    total: data.total ?? hits.length,
    took: data.took,
    limit: data.limit ?? params?.limit,
    offset: data.offset ?? params?.offset,
  };
}

export async function loadSampleLogs(source: string = 'auth'): Promise<{ ingested: number; source: string }> {
  const response = await apiClient.post('/siem/ingestion/load-sample', { source });
  return response.data;
}

function normalizeAlert(alert: any): Alert {
  const recommended_playbook =
    alert.recommended_playbook ||
    alert.recommended_playbook_id ||
    alert.recommended_playbook_key ||
    alert?.raw_payload?.recommended_playbook ||
    alert?.raw_payload?.recommended_playbook_id ||
    alert?.raw_payload?.recommended_playbook_key ||
    alert?.raw_payload?.sg?.playbook_id ||
    (Array.isArray(alert?.raw_payload?.recommended_playbooks) ? alert.raw_payload.recommended_playbooks[0] : undefined);
  const recommended_playbook_id =
    alert.recommended_playbook_id ||
    alert?.raw_payload?.recommended_playbook_id ||
    recommended_playbook ||
    alert.recommended_playbook_key;
  const recommended_playbook_key =
    alert.recommended_playbook_key ||
    alert?.raw_payload?.recommended_playbook_key ||
    alert.recommended_playbook_id;
  const detection_rule_id =
    alert.detection_rule_id ||
    alert?.raw_payload?.detection_rule_id ||
    alert?.raw_payload?.sg?.detection_rule_id;
  const detection_rule_version_id =
    alert.detection_rule_version_id ||
    alert?.raw_payload?.detection_rule_version_id ||
    alert?.raw_payload?.sg?.detection_rule_version_id;
  const playbook_version_id =
    alert.playbook_version_id ||
    alert?.raw_payload?.playbook_version_id ||
    alert?.raw_payload?.sg?.playbook_version_id;
  const normalizedRelatedDetections = Array.isArray(alert?.raw_payload?.detections)
    ? alert.raw_payload.detections.map((d: any) => ({
        id: String(d?.id || d),
        title: typeof d === 'object' ? d?.title : undefined,
        severity: typeof d === 'object' ? d?.severity : undefined,
      }))
    : [];
  const storyContext = normalizeStoryContext({
    rawPayload: alert.raw_payload,
    entities: alert.entities,
    evidence: alert.evidence,
    storyDomains: alert.story_domains,
    assetId: alert.asset_id || alert?.raw_payload?.asset_id || alert?.raw_payload?.host?.id || alert?.raw_payload?.host?.hostname,
    userIdentifier: alert.user_identifier || alert.user_id || alert?.raw_payload?.user_identifier || alert?.raw_payload?.user_id,
    detectionRuleId: detection_rule_id,
    detectionRuleVersionId: detection_rule_version_id,
    playbookId: recommended_playbook_id || recommended_playbook || recommended_playbook_key || alert?.raw_payload?.playbook_id,
    playbookVersionId: playbook_version_id,
    relatedDetections: normalizedRelatedDetections,
    cveIds: alert.cve_ids,
  });
  const storySummary = alert.story_summary || summarizeStoryContext(storyContext);

  return {
    ...alert,
    recommended_playbook,
    recommended_playbook_id,
    recommended_playbook_key,
    severity: alert.severity || alert.raw_severity || 'low',
    raw_severity: alert.raw_severity || alert.severity,
    status: alert.status || 'open',
    user_id: alert.user_id || alert.user_identifier || alert?.raw_payload?.user_id || alert?.raw_payload?.user_identifier,
    user_identifier: alert.user_identifier || alert.user_id || alert?.raw_payload?.user_identifier || alert?.raw_payload?.user_id,
    asset_id: alert.asset_id || alert?.raw_payload?.asset_id || alert?.raw_payload?.host?.id || alert?.raw_payload?.host?.hostname,
    detection_time: alert.detection_time || alert.timestamp,
    created_at: alert.created_at || alert.timestamp || new Date().toISOString(),
    updated_at: alert.updated_at || alert.timestamp || new Date().toISOString(),
    detection_rule_id,
    detection_rule_version_id,
    playbook_version_id,
    category:
      alert.category ||
      alert?.raw_payload?.sg?.category ||
      alert?.raw_payload?.category,
    mitre_tactic:
      alert.mitre_tactic ||
      (Array.isArray(alert.mitre_tactics) && (alert.mitre_tactics[0]?.name || alert.mitre_tactics[0])) ||
      alert.mitre_tactics,
    mitre_technique:
      alert.mitre_technique ||
      (Array.isArray(alert.mitre_techniques) && (alert.mitre_techniques[0]?.name || alert.mitre_techniques[0])) ||
      alert.mitre_techniques,
    control_gap: alert.control_gap || alert?.raw_payload?.control_gap || alert?.raw_payload?.gap_status,
    assigned_to: alert.assigned_to || alert?.raw_payload?.assigned_to,
    due_date: alert.due_date || alert?.raw_payload?.due_date || alert?.raw_payload?.sla_due_at || null,
    control_tags:
      alert.control_tags ||
      (Array.isArray(alert.nist_controls)
        ? alert.nist_controls
            .map((c: any) => c?.control_id || c?.id || c)
            .filter(Boolean)
        : []),
    entities: storyContext.entities,
    evidence: storyContext.evidence,
    story_domains: storyContext.story_domains,
    story_summary: storySummary,
  };
}

/**
 * List alerts
 */
export async function listAlerts(params?: AlertListParams): Promise<AlertListResponse> {
  const response = await apiClient.get('/siem/alerts', { params });
  const data = response.data || {};
  const rawAlerts = data.alerts || data.items || [];

  return {
    alerts: rawAlerts.map(normalizeAlert),
    total: data.total ?? rawAlerts.length,
    limit: data.limit ?? params?.limit,
    offset: data.offset ?? params?.offset,
  };
}

/**
 * Get alert by ID
 */
export async function getAlert(alertId: string): Promise<Alert> {
  const response = await apiClient.get(`/siem/alerts/${alertId}`);
  return normalizeAlert(response.data || {});
}

export function getAlertStreamUrl(alertId: string): string {
  return `/api/v1/siem/alerts/${encodeURIComponent(alertId)}/stream`;
}

/**
 * Update alert status
 */
export async function updateAlertStatus(
  alertId: string,
  status: Alert['status']
): Promise<Alert> {
  const response = await apiClient.put(`/siem/alerts/${alertId}`, { status });
  return normalizeAlert(response.data || {});
}

export async function updateAlert(
  alertId: string,
  payload: Partial<Pick<Alert, 'status' | 'assigned_to' | 'due_date'> & { comments?: string }>
): Promise<Alert> {
  const response = await apiClient.put(`/siem/alerts/${alertId}`, payload);
  return normalizeAlert(response.data || {});
}

/**
 * Get SIEM statistics
 */
export async function getSIEMStats(): Promise<SIEMStats> {
  const response = await apiClient.get<SIEMStats>('/siem/stats');
  return response.data;
}

export interface SourceHealth {
  tenant_id: string;
  ingestion_service: string;
  siem_agent: string;
  opensearch: string;
  wazuh?: string;
  openedr?: string;
  velociraptor?: string;
}

export async function getSourceHealth(): Promise<SourceHealth> {
  const response = await apiClient.get<SourceHealth>('/siem/source-health');
  return response.data;
}

export interface EntityTimelineResponse {
  entity: { type: string; id: string; identifier?: string };
  time_range: { start: string; end: string };
  events: Array<{
    id: string;
    timestamp: string;
    event_type: string;
    source?: any;
    user?: any;
    device?: any;
    action?: string;
  }>;
  summary: Record<string, any>;
}

export async function getEntityTimeline(params: {
  entity_type: 'user' | 'host' | 'ip' | 'domain' | 'file_hash';
  entity_id: string;
  start_time?: string;
  end_time?: string;
  event_types?: string;
  limit?: number;
}): Promise<EntityTimelineResponse> {
  const response = await apiClient.get('/siem/entity-timeline', { params });
  return response.data;
}
