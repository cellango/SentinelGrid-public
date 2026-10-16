/**
 * Detection events API client
 */

import { apiClient } from './client';

export interface DetectionEvent {
  event_id: string;
  timestamp: string;
  sg: {
    tenant_id: string;
    realm: string;
    alert_type: string;
    playbook_id: string;
    severity: string;
    category: string;
  };
  rule: {
    id: string;
    name: string;
    version: string;
  };
  user?: {
    id: string;
    email: string;
    name?: string;
  };
  host?: {
    name: string;
    id: string;
    ip: string;
  };
  source?: {
    ip: string;
    geo?: {
      country: string;
      city?: string;
    };
  };
  incident_id?: string;
  playbook_status?: string;
  description?: string;
  metadata?: any;
}

export interface DetectionRule {
  id: string;
  rule_key: string;
  name: string;
  description: string;
  category: string;
  current_version: string;
  is_enabled: boolean;
  severity: string;
  alert_type: string;
  playbook_id: string;
  index_pattern: string;
  metadata?: {
    mitre_techniques: string[];
    mitre_tactics: string[];
    nist_controls: string[];
    cis_controls: string[];
  };
  statistics?: {
    total_fires: number;
    fires_24h: number;
    fires_7d: number;
    incidents_created: number;
    last_fired: string;
  };
}

export interface DetectionStats {
  total_events: number;
  by_alert_type: Record<string, number>;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
  timeline: Array<{
    timestamp: string;
    count: number;
  }>;
}

/**
 * List detection events
 */
export async function listDetectionEvents(params?: {
  start_time?: string;
  end_time?: string;
  alert_types?: string;
  severities?: string;
  limit?: number;
  offset?: number;
}): Promise<{ events: DetectionEvent[]; total: number }> {
  const response = await apiClient.get('/siem/detection/events', { params });
  return response.data;
}

/**
 * Get a specific detection event
 */
export async function getDetectionEvent(
  eventId: string,
  date?: string
): Promise<DetectionEvent> {
  const response = await apiClient.get(`/siem/detection/events/${eventId}`, {
    params: { date }
  });
  return response.data;
}

/**
 * Get detection statistics
 */
export async function getDetectionStats(params?: {
  start_time?: string;
  end_time?: string;
}): Promise<DetectionStats> {
  const response = await apiClient.get('/siem/detection/stats', { params });
  return response.data;
}

/**
 * List all detection rules
 */
export async function listDetectionRules(params?: {
  category?: string;
  is_enabled?: boolean;
}): Promise<DetectionRule[]> {
  const response = await apiClient.get('/siem/detection-rules', { params });
  return response.data || [];
}

/**
 * Get a specific detection rule
 */
export async function getDetectionRule(ruleId: string): Promise<DetectionRule> {
  const response = await apiClient.get(`/siem/detection-rules/${ruleId}`);
  return response.data;
}

/**
 * Enable/disable a detection rule
 */
export async function toggleDetectionRule(
  ruleId: string,
  enabled: boolean
): Promise<void> {
  // TODO: Implement actual API endpoint
  console.log('Toggle rule:', ruleId, enabled);
}

/**
 * Update detection rule configuration
 */
export async function updateDetectionRule(
  ruleId: string,
  config: Partial<DetectionRule>
): Promise<DetectionRule> {
  // TODO: Implement actual API endpoint
  throw new Error('Not implemented');
}
