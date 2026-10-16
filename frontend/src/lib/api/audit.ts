import { apiClient } from './client';

export interface AuditEvent {
  ts: string;
  text: string;
  actor?: string;
}

export async function getAlertAudit(alertId: string): Promise<AuditEvent[]> {
  try {
    const resp = await apiClient.get(`/audit/alerts/${alertId}`);
    return resp.data?.items || [];
  } catch {
    return [];
  }
}

export async function getIncidentAudit(incidentId: string): Promise<AuditEvent[]> {
  try {
    const resp = await apiClient.get(`/audit/incidents/${incidentId}`);
    return resp.data?.items || [];
  } catch {
    return [];
  }
}
