/**
 * Reporting API Client
 * Handles report generation and template management
 */

import { apiClient } from './client';

export interface ReportTemplate {
  id: string;
  tenant_id?: string;
  name: string;
  description?: string;
  type: 'executive' | 'compliance' | 'incident' | 'security_posture' | 'soc2' | 'ai_governance' | 'custom';
  sections: TemplateSection[];
  data_queries?: DataQuery[];
  schedule?: ScheduleConfig;
  required_roles?: string[];
  created_at: string;
  updated_at: string;
}

export interface TemplateSection {
  title: string;
  widget: string;
  data_source: string;
  config?: Record<string, any>;
  order: number;
}

export interface DataQuery {
  endpoint: string;
  method?: string;
  params?: Record<string, any>;
  headers?: Record<string, string>;
  transform?: string;
}

export interface ScheduleConfig {
  frequency: 'daily' | 'weekly' | 'monthly' | 'quarterly';
  day?: string;
  time: string;
  recipients: string[];
  enabled: boolean;
}

export interface Report {
  id: string;
  tenant_id: string;
  template_id?: string;
  name: string;
  format: 'pdf' | 'csv' | 'json' | 'html' | 'PDF' | 'CSV' | 'JSON' | 'HTML';
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'PENDING' | 'GENERATING' | 'COMPLETED' | 'FAILED';
  generated_at?: string;
  generated_by?: string;
  date_range_start?: string;
  date_range_end?: string;
  file_path?: string;
  file_size_bytes?: number;
  download_url?: string;
  sections?: string[];
  metadata?: Record<string, any>;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface ReportDownloadResponse {
  report_id: string;
  report_name: string;
  download_url: string;
  format: string;
  generated_at?: string | null;
}

export interface ReportGenerateRequest {
  template_id: string;
  format?: 'pdf' | 'csv';
  date_range?: {
    start: string;
    end: string;
  };
  sections?: string[];
  framework_ids?: string[];
  control_ids?: string[];
  evidence_package_ids?: string[];
  include_gaps?: boolean;
  include_expired_evidence?: boolean;
  parameters?: Record<string, any>;
}

/**
 * List available report templates
 */
export async function listTemplates(type?: string): Promise<ReportTemplate[]> {
  const params = type ? { type_filter: type } : {};
  const response = await apiClient.get<ReportTemplate[]>('/reports/templates', { params });
  return response.data;
}

/**
 * Get a specific template
 */
export async function getTemplate(templateId: string): Promise<ReportTemplate> {
  const response = await apiClient.get<ReportTemplate>(`/reports/templates/${templateId}`);
  return response.data;
}

/**
 * Generate a report
 */
export async function generateReport(request: ReportGenerateRequest): Promise<Report> {
  const response = await apiClient.post<Report>('/reports/generate', request);
  return response.data;
}

/**
 * List reports
 */
export async function listReports(params?: {
  limit?: number;
  offset?: number;
  status?: string;
  report_type?: string;
}): Promise<Report[]> {
  const response = await apiClient.get<Report[]>('/reports', {
    params: params
      ? {
          limit: params.limit,
          offset: params.offset,
          status_filter: params.status,
          report_type: params.report_type,
        }
      : undefined,
  });
  return response.data;
}

/**
 * Get a specific report
 */
export async function getReport(reportId: string): Promise<Report> {
  const response = await apiClient.get<Report>(`/reports/${reportId}`);
  return response.data;
}

/**
 * Get an audited report download URL
 */
export async function getReportDownload(reportId: string): Promise<ReportDownloadResponse> {
  const response = await apiClient.get<ReportDownloadResponse>(`/reports/${reportId}/download`);
  return response.data;
}

/**
 * Delete a report
 */
export async function deleteReport(reportId: string): Promise<void> {
  await apiClient.delete(`/reports/${reportId}`);
}

/**
 * Share Management
 */
export interface ShareCreateRequest {
  expires_in_days?: number;
  password?: string;
}

export interface Share {
  id: string;
  report_id: string;
  share_token: string;
  share_url: string;
  expires_at?: string;
  password_protected: boolean;
  access_count: number;
  last_accessed_at?: string;
  created_at: string;
}

/**
 * Create a shareable link for a report
 */
export async function createShare(reportId: string, request: ShareCreateRequest): Promise<Share> {
  const response = await apiClient.post<Share>(`/reports/${reportId}/share`, request);
  return response.data;
}

/**
 * List shares for a report
 */
export async function listShares(reportId: string): Promise<Share[]> {
  const response = await apiClient.get<Share[]>(`/reports/${reportId}/shares`);
  return response.data;
}

/**
 * Delete a share
 */
export async function deleteShare(shareId: string): Promise<void> {
  await apiClient.delete(`/shares/${shareId}`);
}

/**
 * Scheduled Reports
 */
export interface ScheduledReport {
  job_id: string;
  template_id?: string;
  template_name?: string;
  next_run_time?: string;
  trigger?: string;
}

export interface QuestionnaireAssistArtifact {
  template_key: string;
  reason: string;
}

export interface QuestionnaireAssistControl {
  id: string;
  title: string;
  status: string;
  open_findings: number;
  evidence_items: number;
}

export interface QuestionnaireAssistSignal {
  id: string;
  title: string;
  source_label?: string | null;
  status?: string | null;
  href?: string | null;
}

export interface QuestionnaireAssistAnswer {
  question: string;
  category: string;
  confidence: 'high' | 'medium' | 'low';
  answer: string;
  recommended_artifacts: QuestionnaireAssistArtifact[];
  supporting_controls: QuestionnaireAssistControl[];
  supporting_signals: QuestionnaireAssistSignal[];
  follow_up: string[];
}

export interface QuestionnaireAssistSummary {
  question_count: number;
  overall_score: number;
  criteria_ready: number;
  criteria_needing_attention: number;
  mapped_detections: number;
  control_checks: number;
  evidence_items: number;
  recommended_artifacts: QuestionnaireAssistArtifact[];
}

export interface QuestionnaireAssistResponse {
  summary: QuestionnaireAssistSummary;
  answers: QuestionnaireAssistAnswer[];
  suggested_questions: string[];
}

export interface SecurityReviewResponseTemplate {
  key: string;
  title: string;
  audience: string;
  use_when: string;
  subject: string;
  body: string;
  recommended_artifacts: QuestionnaireAssistArtifact[];
  talking_points: string[];
  follow_up: string[];
}

export interface SecurityReviewTemplatesResponse {
  summary: {
    overall_score: number;
    criteria_ready: number;
    criteria_needing_attention: number;
    mapped_detections: number;
    control_checks: number;
    evidence_items: number;
    framework_pack_states: Record<string, string>;
  };
  templates: SecurityReviewResponseTemplate[];
}

export interface AIGovernanceOverview {
  governance_score: number;
  active_apps: number;
  active_users: number;
  requests_in_window: number;
  open_ai_alerts: number;
  active_ai_incidents: number;
  policy_violations: number;
  prompt_injection_events: number;
  sensitive_data_events: number;
  apps_needing_review: number;
  unclassified_apps: number;
  high_risk_apps: number;
}

export interface AIGovernanceThreat {
  type: string;
  count: number;
  trend: 'up' | 'down' | 'flat';
}

export interface AIGovernanceTrendPoint {
  label: string;
  requests: number;
  unique_users: number;
  policy_hits: number;
}

export interface AIGovernanceAppInventoryEntry {
  app_id: string;
  label: string;
  requests_in_window: number;
  unique_users: number;
  models: string[];
  modules: string[];
  policy_hits: number;
  prompt_injection_hits: number;
  sensitive_data_hits: number;
  open_alerts: number;
  active_incidents: number;
  highest_severity: 'critical' | 'high' | 'medium' | 'low';
  governance_state: 'needs_review' | 'guardrail_watch' | 'monitored' | 'unclassified';
  last_activity?: string | null;
}

export interface AIGovernanceRecentActivity {
  id?: string;
  timestamp?: string | null;
  action: string;
  user_label: string;
  app_label: string;
  model?: string | null;
  module?: string | null;
}

export interface AIGovernanceSummary {
  generated_at: string;
  realm_name: string;
  lookback_days: number;
  overview: AIGovernanceOverview;
  risk_breakdown: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  top_threats: AIGovernanceThreat[];
  usage_trend: AIGovernanceTrendPoint[];
  app_inventory: AIGovernanceAppInventoryEntry[];
  recent_activity: AIGovernanceRecentActivity[];
  priority_actions: Array<{ label: string; href: string }>;
  current_risk_summary?: string | null;
  top_risk?: {
    item_type: 'incident' | 'alert';
    id: string;
    title: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    summary: string;
    href: string;
  } | null;
}

/**
 * List scheduled reports
 */
export async function listScheduledReports(): Promise<ScheduledReport[]> {
  const response = await apiClient.get<{ items: ScheduledReport[] }>('/reports/scheduled');
  return response.data.items;
}

export async function createScheduledReport(templateId: string, schedule: ScheduleConfig): Promise<{ job_id: string; message: string }> {
  const response = await apiClient.post(`/reports/scheduled`, {
    template_id: templateId,
    schedule: schedule
  });
  return response.data;
}

/**
 * Delete a scheduled report
 */
export async function deleteScheduledReport(jobId: string): Promise<void> {
  await apiClient.delete(`/reports/scheduled/${jobId}`);
}

export async function questionnaireAssist(request: { questions: string[] }): Promise<QuestionnaireAssistResponse> {
  const response = await apiClient.post<QuestionnaireAssistResponse>('/reports/questionnaire-assist', request);
  return response.data;
}

export async function listSecurityReviewTemplates(): Promise<SecurityReviewTemplatesResponse> {
  const response = await apiClient.get<SecurityReviewTemplatesResponse>('/reports/security-review-templates');
  return response.data;
}

export async function getAIGovernanceSummary(lookbackDays: number = 30): Promise<AIGovernanceSummary> {
  const response = await apiClient.get<AIGovernanceSummary>('/reports/ai-governance/summary', {
    params: { lookback_days: lookbackDays },
  });
  return response.data;
}
