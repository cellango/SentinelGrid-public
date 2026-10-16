/**
 * Compliance Remediation Service API Client
 * Hero Flow 5 - Compliance Violation Remediation
 */

import { apiClient } from './client';

export interface RemediationPlan {
  steps: Array<{
    step: number;
    action: string;
    description: string;
    playbook_action?: string;
  }>;
  estimated_time: string;
  complexity: string;
  requires_approval: boolean;
  finding_id?: string;
  finding_type?: string;
  severity?: string;
  created_at?: string;
}

export interface EnhanceFindingResponse {
  finding_id: string;
  nist_control_id?: string;
  remediation_plan: RemediationPlan;
  remediation_status: string;
}

export interface RemediationPlanResponse {
  plan: RemediationPlan;
}

export interface ExecuteRemediationRequest {
  playbook_id?: string;
  auto_approve: boolean;
}

export interface ExecuteRemediationResponse {
  remediation_id: string;
  execution_id: string;
  status: string;
  finding_id: string;
  finding_type: string;
}

export interface RemediationStatus {
  finding_id: string;
  remediation_id?: string;
  status: string;
  execution_id?: string;
  created_at?: string;
}

/**
 * Enhance a finding with compliance metadata
 */
export async function enhanceFinding(
  findingId: string,
  findingType: 'iam_finding' | 'posture_finding'
): Promise<EnhanceFindingResponse> {
  const response = await apiClient.post(
    `/compliance/findings/${findingId}/enhance`,
    { finding_type: findingType }
  );
  return response.data;
}

/**
 * Create a remediation plan for a finding
 */
export async function createRemediationPlan(
  findingId: string,
  findingType: 'iam_finding' | 'posture_finding',
  customSteps?: RemediationPlan['steps']
): Promise<RemediationPlanResponse> {
  const response = await apiClient.post(
    `/compliance/findings/${findingId}/remediation-plan`,
    {
      finding_type: findingType,
      custom_steps: customSteps
    }
  );
  return response.data;
}

/**
 * Execute remediation for a finding
 */
export async function executeRemediation(
  findingId: string,
  findingType: 'iam_finding' | 'posture_finding',
  request: ExecuteRemediationRequest
): Promise<ExecuteRemediationResponse> {
  const response = await apiClient.post(
    `/compliance/findings/${findingId}/remediate`,
    request,
    {
      params: { finding_type: findingType }
    }
  );
  return response.data;
}

/**
 * Get remediation status for a finding
 */
export async function getRemediationStatus(
  findingId: string,
  findingType: 'iam_finding' | 'posture_finding'
): Promise<RemediationStatus> {
  const response = await apiClient.get(
    `/compliance/findings/${findingId}/remediation-status`,
    {
      params: { finding_type: findingType }
    }
  );
  return response.data;
}

