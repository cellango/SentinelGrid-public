/**
 * API client for phishing email ingestion and analysis.
 */

import { emailIngestionClient, orchestratorClient } from './client';

export interface PhishingReport {
  id: string;
  tenant_id: string;
  message_id: string;
  subject?: string;
  from_address: string;
  to_address: string;
  reply_to?: string;
  received_date: string; // ISO date string
  reported_by?: string;
  raw_email: string;
  html_body?: string;
  text_body?: string;
  attachments?: Array<{
    filename?: string;
    content_type?: string;
    size?: number;
  }>;
  classification?: 'phishing' | 'benign' | 'suspicious' | 'pending';
  classification_confidence?: number;
  classified_by?: 'ai' | 'analyst' | 'system';
  classified_at?: string; // ISO date string
  ai_analysis?: Record<string, any>;
  ai_summary?: string;
  ai_recommended_actions?: string[];
  mitre_tactics?: string[];
  mitre_techniques?: string[];
  nist_controls?: string[];
  status: 'new' | 'in_review' | 'confirmed_phishing' | 'confirmed_benign' | 'resolved';
  severity?: 'critical' | 'high' | 'medium' | 'low';
  assigned_to?: string;
  ticket_id?: string;
  incident_id?: string;
  similar_emails?: string[];
  created_at: string; // ISO date string
  updated_at: string; // ISO date string
}

export interface PhishingObservable {
  id: string;
  tenant_id: string;
  phishing_report_id: string;
  observable_type: 'ip' | 'domain' | 'url' | 'email' | 'hash';
  observable_value: string;
  observable_context?: string;
  threat_intel?: Record<string, any>;
  reputation_score?: number;
  is_malicious: boolean;
  created_at: string; // ISO date string
}

export interface PhishingFilters {
  status?: string;
  classification?: string;
  severity?: string;
  reporter?: string;
  limit?: number;
  offset?: number;
}

export interface PhishingAnalysisResponse {
  phishing_report_id: string;
  classification: string;
  confidence: number;
  reasoning: string;
  indicators: {
    urls?: string[];
    domains?: string[];
    ips?: string[];
    email_addresses?: string[];
  };
  recommended_actions: string[];
  mitre_mapping: {
    tactics: string[];
    techniques: string[];
  };
  nist_mapping: {
    controls: string[];
  };
  severity?: string;
}

/**
 * Ingest a raw email (RFC 822 format).
 */
export async function ingestEmail(
  rawEmail: string,
  tenantId: string
): Promise<PhishingReport> {
  const response = await emailIngestionClient.post<PhishingReport>(
    `/phishing/ingest?tenant_id=${tenantId}`,
    rawEmail,
    {
      headers: {
        'Content-Type': 'text/plain',
      },
    }
  );
  return response.data;
}

/**
 * List phishing reports with optional filters.
 */
export async function getPhishingReports(
  tenantId: string,
  filters?: PhishingFilters
): Promise<PhishingReport[]> {
  const params = new URLSearchParams({ tenant_id: tenantId });
  
  if (filters?.status) params.append('status', filters.status);
  if (filters?.classification) params.append('classification', filters.classification);
  if (filters?.severity) params.append('severity', filters.severity);
  if (filters?.reporter) params.append('reporter', filters.reporter);
  if (filters?.limit) params.append('limit', filters.limit.toString());
  if (filters?.offset) params.append('offset', filters.offset.toString());
  
  const response = await emailIngestionClient.get<PhishingReport[]>(
    `/phishing/reports?${params.toString()}`
  );
  return response.data;
}

/**
 * Get a phishing report by ID.
 */
export async function getPhishingReport(
  reportId: string,
  tenantId: string
): Promise<PhishingReport> {
  const response = await emailIngestionClient.get<PhishingReport>(
    `/phishing/reports/${reportId}?tenant_id=${tenantId}`
  );
  return response.data;
}

/**
 * Get observables for a phishing report.
 */
export async function getPhishingObservables(
  reportId: string,
  tenantId: string
): Promise<PhishingObservable[]> {
  const response = await emailIngestionClient.get<PhishingObservable[]>(
    `/phishing/reports/${reportId}/observables?tenant_id=${tenantId}`
  );
  return response.data;
}

/**
 * Trigger AI classification for a phishing report.
 */
export async function classifyPhishingReport(
  reportId: string,
  tenantId: string
): Promise<PhishingReport> {
  const response = await emailIngestionClient.post<PhishingReport>(
    `/phishing/reports/${reportId}/classify?tenant_id=${tenantId}`
  );
  return response.data;
}

/**
 * Update a phishing report.
 */
export async function updatePhishingReport(
  reportId: string,
  tenantId: string,
  updates: {
    classification?: string;
    status?: string;
    severity?: string;
    assigned_to?: string;
  }
): Promise<PhishingReport> {
  const response = await emailIngestionClient.put<PhishingReport>(
    `/phishing/reports/${reportId}?tenant_id=${tenantId}`,
    updates
  );
  return response.data;
}

/**
 * Analyze phishing email via Orchestrator.
 */
export async function analyzePhishingEmail(
  reportId: string,
  tenantId: string,
  forceReanalyze: boolean = false
): Promise<PhishingAnalysisResponse> {
  const response = await orchestratorClient.post<PhishingAnalysisResponse>(
    '/orchestrator/analyze-phishing-email',
    {
      phishing_report_id: reportId,
      tenant_id: tenantId,
      force_reanalyze: forceReanalyze,
    }
  );
  return response.data;
}

/**
 * Run containment playbook for phishing report.
 */
export async function runContainmentPlaybook(
  reportId: string,
  tenantId: string,
  options?: {
    quarantine_emails?: boolean;
    block_domains?: boolean;
    create_ticket?: boolean;
    notify_users?: boolean;
  }
): Promise<{
  report_id: string;
  similar_emails_found: number;
  deletion_result?: any;
  block_result?: any;
  ticket_result?: any;
  notification_result?: any;
  status: string;
}> {
  const response = await emailIngestionClient.post(
    `/phishing/reports/${reportId}/run-containment-playbook?tenant_id=${tenantId}`,
    options || {
      quarantine_emails: true,
      block_domains: true,
      create_ticket: true,
      notify_users: true,
    }
  );
  return response.data;
}

/**
 * Search for similar emails.
 */
export async function searchSimilarEmails(
  reportId: string,
  tenantId: string,
  provider: 'microsoft_graph' | 'gmail' = 'microsoft_graph'
): Promise<{
  report_id: string;
  search_criteria: any;
  results: Array<{
    id: string;
    message_id?: string;
    subject?: string;
    from?: string;
    received_date?: string;
    has_attachments?: boolean;
  }>;
  count: number;
}> {
  const response = await emailIngestionClient.post(
    `/phishing/reports/${reportId}/search-similar?tenant_id=${tenantId}`,
    {
      provider,
    }
  );
  return response.data;
}

/**
 * Delete or quarantine similar emails.
 */
export async function deleteSimilarEmails(
  reportId: string,
  tenantId: string,
  emailIds: string[],
  action: 'delete' | 'quarantine' | 'move' = 'quarantine',
  provider: 'microsoft_graph' | 'gmail' = 'microsoft_graph'
): Promise<{
  success_count: number;
  failure_count: number;
  total: number;
  errors: Array<{ email_id: string; error: string }>;
}> {
  const response = await emailIngestionClient.post(
    `/phishing/reports/${reportId}/delete-similar?tenant_id=${tenantId}`,
    {
      email_ids: emailIds,
      provider,
      action,
    }
  );
  return response.data;
}

