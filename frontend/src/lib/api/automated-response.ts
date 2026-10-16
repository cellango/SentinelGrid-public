/**
 * Automated Response Service API Client
 * Hero Flow 4 - Automated Threat Response
 */

import { apiClient } from './client';

export interface TriggerCondition {
  severity?: string[];
  category?: string[];
  source?: string[];
  time_window?: string;
  threshold?: {
    min_similar_alerts?: number;
  };
}

export interface PlaybookTrigger {
  playbook_id: string;
  playbook_name: string;
  trigger_reason: string;
  priority: number;
}

export interface TriggerEvaluationResponse {
  alert_id: string;
  matching_playbooks: PlaybookTrigger[];
  total_matched: number;
}

export interface TriggerPlaybookRequest {
  playbook_id: string;
  trigger_reason: string;
}

export interface TriggerPlaybookResponse {
  trigger_id: string;
  execution_id: string;
  status: string;
  trigger_reason: string;
}

export interface AutoTriggerResponse {
  alert_id: string;
  triggered: boolean;
  playbooks_triggered: number;
  results: Array<{
    playbook_id: string;
    playbook_name: string;
    execution_id?: string;
    status?: string;
    error?: string;
  }>;
}

/**
 * Evaluate an alert against playbook triggers
 */
export async function evaluateAlertTriggers(alertId: string): Promise<TriggerEvaluationResponse> {
  const response = await apiClient.post(
    `/automated-response/alerts/${alertId}/evaluate`
  );
  return response.data;
}

/**
 * Trigger a specific playbook for an alert
 */
export async function triggerPlaybookForAlert(
  alertId: string,
  request: TriggerPlaybookRequest
): Promise<TriggerPlaybookResponse> {
  const response = await apiClient.post(
    `/automated-response/alerts/${alertId}/trigger`,
    request
  );
  return response.data;
}

/**
 * Automatically evaluate and trigger all matching playbooks for an alert
 */
export async function autoTriggerForAlert(alertId: string): Promise<AutoTriggerResponse> {
  const response = await apiClient.post(
    `/automated-response/alerts/${alertId}/auto-trigger`
  );
  return response.data;
}

