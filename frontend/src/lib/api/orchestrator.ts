/**
 * Orchestrator API Client
 * Handles security snapshot and orchestration operations
 */

import { apiClient } from './client';

export interface AlertSummary {
  id: string;
  title: string;
  severity: string;
  status: string;
  description?: string;
  created_at?: string;
}

export interface SecuritySnapshotSummary {
  events_count: number;
  alerts_count: number;
  users_active: number;
  users_total: number;
}

export interface IAMSummary {
  users_count: number;
  active_users_count: number;
  roles_count: number;
  groups_count: number;
}

export interface Recommendation {
  priority: string; // High, Medium, Low
  action: string;
}

export interface AIAnalysis {
  posture: string; // Good, Needs Attention, At Risk
  risk_level: string; // Low, Medium, High, Critical
  key_findings: string[];
  recommendations: Recommendation[];
  summary: string;
  raw_response?: string;
  error?: string;
}

export interface SecuritySnapshot {
  tenant_id: string;
  generated_at: string;
  summary: SecuritySnapshotSummary;
  alerts_by_severity: Record<string, number>;
  alerts_by_status: Record<string, number>;
  top_findings: AlertSummary[];
  iam_summary: IAMSummary;
  ai_analysis: AIAnalysis;
}

/**
 * Get security snapshot for a tenant
 */
export async function getSecuritySnapshot(tenantId: string): Promise<SecuritySnapshot> {
  // Note: The orchestrator endpoint requires an internal service token
  // For now, we'll call through the API Gateway which should proxy this
  // In production, the API Gateway should handle the internal token
  const response = await apiClient.get<SecuritySnapshot>(
    `/orchestrator/tenant/${tenantId}/security-snapshot`,
    {
      headers: {
        'X-Tenant-ID': tenantId,
      },
    }
  );
  return response.data;
}

