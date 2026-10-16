import { apiClient } from './client';

export interface DetectionRuleVersion {
  id?: string;
  version: string;
  index_pattern: string;
  query: Record<string, any>;
  trigger_condition: Record<string, any>;
  severity: string;
  action_config?: Record<string, any>;
  metadata?: Record<string, any>;
  is_active?: boolean;
  is_template?: boolean;
  graph_json?: Record<string, any>;
}

export interface DetectionRule {
  id: string;
  rule_key: string;
  name: string;
  description?: string;
  category: string;
  current_version: string;
  approval_required: boolean;
  versions: DetectionRuleVersion[];
  deployment?: {
    monitor_id?: string;
    destination_id?: string;
    is_enabled?: boolean;
    approval_status?: string;
    rule_version?: string;
  };
  mapping?: {
    alert_type?: string;
    playbook_key?: string;
    auto_execute?: boolean;
    requires_approval?: boolean;
  };
}

export interface DetectionRuleCreate {
  rule_key: string;
  name: string;
  description?: string;
  category: string;
  version: DetectionRuleVersion;
  approval_required?: boolean;
}

export interface PreviewRequest {
  index_pattern: string;
  query: Record<string, any>;
  trigger_condition: Record<string, any>;
  time_range_minutes?: number;
}

export interface PreviewResponse {
  hits: number;
  sample: any[];
  aggregations?: Record<string, any>;
}

export interface DeployRequest {
  destination_id: string;
  auto_execute?: boolean;
  schedule_minutes?: number;
  message_template?: Record<string, any>;
  severity?: string;
}

export interface DeployResponse {
  monitor_id: string;
  destination_id?: string;
  deployed: boolean;
  approval_status?: string;
}

const basePath = '/siem/detection-rules';

export async function listDetectionRules(): Promise<DetectionRule[]> {
  const res = await apiClient.get<DetectionRule[]>(basePath);
  return res.data;
}

export async function getDetectionRule(id: string): Promise<DetectionRule> {
  const res = await apiClient.get<DetectionRule>(`${basePath}/${id}`);
  return res.data;
}

export async function createDetectionRule(payload: DetectionRuleCreate): Promise<DetectionRule> {
  const res = await apiClient.post<DetectionRule>(basePath, payload);
  return res.data;
}

export async function cloneDetectionRule(
  id: string,
  payload: { name: string; rule_key: string; description?: string }
): Promise<DetectionRule> {
  const res = await apiClient.post<DetectionRule>(`${basePath}/${id}/clone`, payload);
  return res.data;
}

export async function previewDetectionRule(
  id: string,
  payload: PreviewRequest
): Promise<PreviewResponse> {
  const res = await apiClient.post<PreviewResponse>(`${basePath}/${id}/preview`, payload);
  return res.data;
}

export async function deployDetectionRule(
  id: string,
  payload: DeployRequest
): Promise<DeployResponse> {
  const res = await apiClient.post<DeployResponse>(`${basePath}/${id}/deploy`, payload);
  return res.data;
}

export async function setDetectionRuleMapping(
  id: string,
  payload: { alert_type: string; playbook_key: string; auto_execute?: boolean; requires_approval?: boolean }
): Promise<DetectionRule> {
  const res = await apiClient.post<DetectionRule>(`${basePath}/${id}/mapping`, payload);
  return res.data;
}

export async function approveDetectionRule(id: string): Promise<{ rule_id: string; approval_status: string }> {
  const res = await apiClient.post<{ rule_id: string; approval_status: string }>(`${basePath}/${id}/approve`);
  return res.data;
}

export async function rejectDetectionRule(id: string): Promise<{ rule_id: string; approval_status: string }> {
  const res = await apiClient.post<{ rule_id: string; approval_status: string }>(`${basePath}/${id}/reject`);
  return res.data;
}

export async function disableDetectionRule(id: string): Promise<{ rule_id: string; disabled: boolean }> {
  const res = await apiClient.post<{ rule_id: string; disabled: boolean }>(`${basePath}/${id}/disable`);
  return res.data;
}
