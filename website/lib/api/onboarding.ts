/**
 * Onboarding API Client
 */

export interface IdPConnectionRequest {
  idp_type: 'google' | 'microsoft' | 'okta' | 'keycloak' | 'none';
  config: Record<string, any>;
}

export interface CloudConnectionRequest {
  cloud_provider: 'aws' | 'azure' | 'gcp';
  account_id: string;
  integration_method?: string;
  // Provider-specific fields
  role_arn?: string;
  external_id?: string;
  tenant_id?: string;
  client_id?: string;
  client_secret?: string;
  project_id?: string;
  service_account_key?: string;
}

export interface OnboardingStatus {
  idp_connected: boolean;
  cloud_connected: boolean;
  endpoint_deployed: boolean;
  git_connected: boolean;
  onboarding_completed: boolean;
  step_idp_completed?: boolean;
  step_cloud_completed?: boolean;
  step_endpoint_completed?: boolean;
  step_git_completed?: boolean;
  step_idp_completed_at?: string;
  step_cloud_completed_at?: string;
  step_endpoint_completed_at?: string;
  step_git_completed_at?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:3443';

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const response = await fetch(`${API_BASE_URL}/api/v1/onboarding/status`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch onboarding status: ${response.statusText}`);
  }

  return response.json();
}

export async function connectIdP(request: IdPConnectionRequest): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/onboarding/connect-idp`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect identity provider');
  }
}

export async function connectCloud(request: CloudConnectionRequest): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/onboarding/connect-${request.cloud_provider}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect cloud provider');
  }
}

