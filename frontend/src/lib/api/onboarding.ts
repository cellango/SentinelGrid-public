/**
 * Onboarding API Client
 * Handles all onboarding-related API calls
 */

import { tenantClient } from './client';
import axios from 'axios';
import { withSessionAuthorization } from '@/lib/auth/session';

// Get service URLs from environment
const CONNECTOR_SERVICE_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin}/api/v1`
    : (process.env.NEXT_PUBLIC_CONNECTOR_SERVICE_URL || 'http://localhost:8005/api/v1');
const DETECTION_SERVICE_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin}/api/v1`
    : (process.env.NEXT_PUBLIC_DETECTION_SERVICE_URL || 'http://localhost:8006/api/v1');
const ORCHESTRATOR_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin}/api/v1`
    : (process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8000/api/v1');

// Create clients for each service (without auth interceptors for onboarding)
const connectorClient = axios.create({
  baseURL: CONNECTOR_SERVICE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

const detectionClient = axios.create({
  baseURL: DETECTION_SERVICE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

const orchestratorClient = axios.create({
  baseURL: ORCHESTRATOR_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

// Helper to add tenant ID header
function addTenantHeader(config: any, tenantId: string) {
  if (tenantId) {
    config.headers = config.headers || {};
    config.headers['X-Tenant-ID'] = tenantId;
  }
  return config;
}

// ============================================================================
// Step 1: Account Creation
// ============================================================================

export interface TenantProvisionRequest {
  company_name: string;
  admin_email: string;
  admin_password: string;
  admin_first_name?: string;
  admin_last_name?: string;
  idp_mode?: 'sentinelgrid' | 'existing_sso';
}

export interface TenantProvisionResponse {
  tenant_id: string;
  realm_name: string;
  company_name: string;
  admin_username: string;
  admin_email: string;
  status: string;
  created_at: string;
}

/**
 * Provision a new tenant (Step 1)
 */
export async function provisionTenant(
  data: TenantProvisionRequest
): Promise<TenantProvisionResponse> {
  const response = await tenantClient.post<TenantProvisionResponse>(
    '/tenants/provision',
    data
  );
  return response.data;
}

// =============================================================================
// Additional onboarding helpers used by marketing onboarding wizard
// =============================================================================

export interface IdPConnectionRequest {
  tenant_id: string;
  provider: 'google_workspace' | 'microsoft_entra' | 'okta' | 'sentinelgrid';
  config: Record<string, any>;
}

export interface CloudConnectionRequest {
  tenant_id: string;
  cloud_provider: string;
  config: Record<string, any>;
}

export interface CloudProviderField {
  name: string;
  type: 'string' | 'secret' | 'textarea' | 'checkbox' | 'csv' | 'select';
  label?: string;
  placeholder?: string;
  default?: string | boolean | string[];
  required?: boolean;
  help_text?: string;
  format?: string;
  options?: Array<{ label: string; value: string }>;
}

export interface CloudProviderDefinition {
  id: string;
  display_name: string;
  aliases?: string[];
  adapter?: string;
  auth?: Record<string, any>;
  resources?: Record<string, any>;
  capabilities?: Record<string, boolean>;
  controls?: string[];
  onboarding?: {
    enabled?: boolean;
    default?: boolean;
    badge?: string;
    order?: number;
    target_mode?: string;
    description?: string;
    integration_method?: string;
  };
  onboarding_fields: CloudProviderField[];
  targets?: Array<Record<string, any>>;
}

export interface CloudProviderRegistryResponse {
  providers: CloudProviderDefinition[];
  targets?: Array<Record<string, any>>;
  scanner_aliases?: Record<string, any>;
  source?: string;
}

// Use API Gateway as the single entrypoint; default to local gateway if not provided
const API_BASE_URL = (() => {
  // Prefer the current origin when running in the browser to avoid mixed-content/CORS
  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const rawEnv = process.env.NEXT_PUBLIC_API_BASE;
  const raw = origin || rawEnv || 'http://localhost:8082';

  const trimmed = raw.replace(/\/+$/, '');
  if (/\/api($|\/v\d+$)/.test(trimmed)) {
    return trimmed;
  }
  return `${trimmed}/api`;
})();

function getTenantId(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('tenant_id') || sessionStorage.getItem('tenant_id') || '';
}

function getJsonAuthHeaders(): HeadersInit {
  const headers = withSessionAuthorization({
    'Content-Type': 'application/json',
  });
  const tenantId = getTenantId();

  if (tenantId) {
    headers['X-Tenant-ID'] = tenantId;
  }

  return headers;
}

export async function connectIdP(request: IdPConnectionRequest): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/connect-idp`, {
    method: 'POST',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
    body: JSON.stringify({
      tenant_id: request.tenant_id,
      idp_type: request.provider,
      config: request.config,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect identity provider');
  }
}

export async function connectCloud(request: CloudConnectionRequest): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/connect-cloud`, {
    method: 'POST',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect cloud provider');
  }
  return response.json();
}

export async function getCloudProviderRegistry(): Promise<CloudProviderRegistryResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/cloud/providers`, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to load cloud provider registry');
  }
  return response.json();
}

export interface InfrastructureChangeApprovalRequest {
  provider?: string;
  admin_ssh_cidrs?: string[];
  inputs?: Record<string, any>;
  notes?: string;
}

export interface InfrastructureChangeApplyRequest {
  provider?: string;
  confirm?: boolean;
}

export async function approveInfrastructureChangeRequest(
  changeRequestId: string,
  data: InfrastructureChangeApprovalRequest
): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/v1/onboarding/cloud/change-requests/${changeRequestId}/approve`,
    {
      method: 'POST',
      headers: getJsonAuthHeaders(),
      credentials: 'include',
      body: JSON.stringify(data),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to approve infrastructure change request');
  }
  return response.json();
}

export async function applyInfrastructureChangeRequest(
  changeRequestId: string,
  data: InfrastructureChangeApplyRequest = { confirm: true }
): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/v1/onboarding/cloud/change-requests/${changeRequestId}/apply`,
    {
      method: 'POST',
      headers: getJsonAuthHeaders(),
      credentials: 'include',
      body: JSON.stringify({ confirm: true, ...data }),
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to apply infrastructure change request');
  }
  return response.json();
}

export async function connectAppSec(data: {
  gateway_url: string;
  api_key: string;
  app_id?: string;
  openapi_url?: string;
}): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/connect-appsec`, {
    method: 'POST',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect AppSec');
  }
  return response.json();
}

export async function connectAIShield(data: {
  mode: 'hosted' | 'self';
  endpoint_url?: string;
  api_key?: string;
  gateway_url?: string;
  client_id?: string;
  client_secret?: string;
}): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/connect-ai`, {
    method: 'POST',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect AI Shield');
  }
  return response.json();
}

export type TicketingProvider = 'internal' | 'jira' | 'servicenow';

export type TicketAssignmentMode =
  | 'project_default'
  | 'service_owner'
  | 'named_owner';

export type TicketAssigneeIdentifierType =
  | 'account_id'
  | 'email'
  | 'username'
  | 'sys_id';

export interface TicketingConnectionRequest {
  provider: TicketingProvider;
  url?: string;
  project?: string;
  api_key?: string;
  socManaged?: boolean;
  issue_type?: string;
  assignment_mode?: TicketAssignmentMode;
  default_assignee?: string;
  assignee_identifier_type?: TicketAssigneeIdentifierType;
  auto_create_tickets?: boolean;
  notify_slack?: boolean;
  slack_channel?: string;
  slack_webhook_url?: string;
}

export async function connectTicketing(
  data: TicketingConnectionRequest
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/connect-ticketing`, {
    method: 'POST',
    headers: getJsonAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect ticketing');
  }
  return response.json();
}

export interface TicketingAssigneeSearchRequest {
  query: string;
  provider?: TicketingProvider;
  url?: string;
  project?: string;
  api_key?: string;
  assignee_identifier_type?: TicketAssigneeIdentifierType;
  limit?: number;
}

export interface TicketingAssigneeSearchResult {
  value: string;
  label: string;
  description?: string | null;
  identifierType: TicketAssigneeIdentifierType;
  identifiers: Partial<Record<TicketAssigneeIdentifierType, string>>;
}

export interface TicketingAssigneeSearchResponse {
  provider: TicketingProvider;
  assigneeIdentifierType: TicketAssigneeIdentifierType;
  source: 'draft_config' | 'stored_config';
  results: TicketingAssigneeSearchResult[];
}

export async function searchTicketingAssignees(
  data: TicketingAssigneeSearchRequest
): Promise<TicketingAssigneeSearchResponse> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/ticketing-assignees/search`, {
    method: 'POST',
    headers: getJsonAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to search ticketing assignees');
  }
  return response.json();
}

export async function recheckHealth(target: 'appsec' | 'ai' | 'ticketing' | 'cloud' | 'git' | 'endpoint' | 'idp'): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/recheck-health`, {
    method: 'POST',
    headers: getJsonAuthHeaders(),
    body: JSON.stringify({ target }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to re-run health check');
  }
  return response.json();
}

export interface TrustProfile {
  enabled: boolean;
  frameworks: string[];
  primaryDriver?: string | null;
  targetTimeline?: string | null;
  needsQuestionnaireSupport: boolean;
  needsEvidenceExports: boolean;
  notes?: string | null;
}

export async function saveTrustProfile(data: TrustProfile): Promise<{ success: boolean; status: string; trustProfile: TrustProfile; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/v1/onboarding/trust-profile`, {
    method: 'POST',
    headers: getJsonAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to save trust profile');
  }
  return response.json();
}

// ============================================================================
// Step 2: Identity Provider Setup
// ============================================================================

export interface OAuthInitRequest {
  provider: 'google_workspace' | 'microsoft_entra' | 'okta';
  tenant_id: string;
  redirect_uri: string;
}

export interface OAuthInitResponse {
  oauth_url: string;
  state_token: string;
}

export interface OAuthCallbackRequest {
  provider: 'google_workspace' | 'microsoft_entra' | 'okta';
  code: string;
  state: string;
}

export interface OAuthCallbackResponse {
  status: string;
  connector_id: string;
  users_synced?: number;
  last_sync?: string;
}

/**
 * Initialize OAuth flow for identity provider
 */
export async function initOAuth(
  data: OAuthInitRequest
): Promise<OAuthInitResponse> {
  const response = await connectorClient.post<OAuthInitResponse>(
    '/connectors/oauth/init',
    data
  );
  return response.data;
}

/**
 * Handle OAuth callback
 */
export async function handleOAuthCallback(
  data: OAuthCallbackRequest
): Promise<OAuthCallbackResponse> {
  const response = await connectorClient.post<OAuthCallbackResponse>(
    '/connectors/oauth/callback',
    data
  );
  return response.data;
}

/**
 * Test connector connection
 */
export async function testConnection(
  connectorId: string,
  tenantId: string
): Promise<any> {
  const config = addTenantHeader({}, tenantId);
  const response = await connectorClient.post(
    `/connectors/${connectorId}/test`,
    { tenant_id: tenantId },
    config
  );
  return response.data;
}

// ============================================================================
// Step 3: Cloud Integration
// ============================================================================

export interface CloudConnectorRequest {
  tenant_id: string;
  type: 'aws' | 'azure' | 'gcp';
  config: {
    iam_role_arn?: string;
    regions?: string[];
    services?: string[];
    subscription_id?: string;
    project_id?: string;
  };
}

export interface CloudConnectorResponse {
  connector_id: string;
  status: string;
  cloudformation_url?: string;
}

/**
 * Create cloud connector
 */
export async function createCloudConnector(
  data: CloudConnectorRequest
): Promise<CloudConnectorResponse> {
  const response = await connectorClient.post<CloudConnectorResponse>(
    '/connectors',
    {
      type: data.type,
      name: `${data.type.toUpperCase()} Connector`,
      credentials: data.config,
      sync_settings: {
        regions: data.config.regions || [],
        services: data.config.services || [],
      },
    }
  );
  return response.data;
}

/**
 * Start connector sync
 */
export async function startConnectorSync(
  connectorId: string,
  tenantId: string
): Promise<any> {
  const config = addTenantHeader({}, tenantId);
  const response = await connectorClient.post(
    `/connectors/${connectorId}/sync`,
    { tenant_id: tenantId },
    config
  );
  return response.data;
}

// ============================================================================
// Step 4: Initial Configuration
// ============================================================================

export interface EnableRulesRequest {
  tenant_id: string;
  rule_keys: ('failed_logins' | 'new_admin' | 'suspicious_cloud')[];
}

export interface EnableRulesResponse {
  tenant_id: string;
  rules_enabled: string[];
  rules_created: number;
  rules_updated: number;
}

/**
 * Enable baseline detection rules
 */
export async function enableDetectionRules(
  data: EnableRulesRequest
): Promise<EnableRulesResponse> {
  const config = addTenantHeader({}, data.tenant_id);
  const response = await detectionClient.post<EnableRulesResponse>(
    '/rules/enable',
    data,
    config
  );
  return response.data;
}

export interface AlertPreferencesRequest {
  email_notifications: {
    critical?: boolean;
    high?: boolean;
    medium?: boolean;
    low?: boolean;
    all?: boolean;
  };
  notification_email: string;
}

export interface AlertPreferencesResponse {
  tenant_id: string;
  email_notifications: Record<string, boolean>;
  notification_email: string;
  updated_at: string;
}

/**
 * Set alert preferences
 */
export async function setAlertPreferences(
  tenantId: string,
  data: AlertPreferencesRequest
): Promise<AlertPreferencesResponse> {
  const config = addTenantHeader({}, tenantId);
  const response = await tenantClient.post<AlertPreferencesResponse>(
    `/tenants/${tenantId}/alert-preferences`,
    data,
    config
  );
  return response.data;
}

export interface UserInvitationRequest {
  emails: string[];
  role: 'soc_analyst' | 'soc_manager' | 'view_only' | 'tenant_admin';
}

export interface UserInvitationResponse {
  tenant_id: string;
  invitations_sent: number;
  invitations: Array<{
    email: string;
    user_id?: string;
    status: string;
    role?: string;
    error?: string;
  }>;
  created_at: string;
}

/**
 * Invite users to tenant
 */
export async function inviteUsers(
  tenantId: string,
  data: UserInvitationRequest
): Promise<UserInvitationResponse> {
  const config = addTenantHeader({}, tenantId);
  const response = await tenantClient.post<UserInvitationResponse>(
    `/tenants/${tenantId}/invitations`,
    data,
    config
  );
  return response.data;
}

// ============================================================================
// Onboarding Status
// ============================================================================

export interface OnboardingStatus {
  idp_connected: boolean;
  idp_provider?: 'google_workspace' | 'microsoft_entra' | 'okta' | 'sentinelgrid' | 'keycloak' | null;
  cloud_connected: boolean;
  endpoint_deployed: boolean;
  git_connected: boolean;
  appsec_connected?: boolean;
  ai_connected?: boolean;
  ticketing_connected?: boolean;
  onboarding_completed: boolean;
  cloud_health?: any;
  git_health?: any;
  appsec_health?: any;
  ai_health?: any;
  ticketing_health?: any;
  step_idp_completed?: boolean;
  step_cloud_completed?: boolean;
  step_endpoint_completed?: boolean;
  step_git_completed?: boolean;
  step_idp_completed_at?: string;
  step_cloud_completed_at?: string;
  step_endpoint_completed_at?: string;
  step_git_completed_at?: string;
  services_selected?: any;
  overall_complete?: boolean;
  last_incomplete_step_id?: string | null;
  steps?: { id: string; done: boolean; health?: any; tested_at?: string | null }[];
  access_profile_ready?: boolean;
  birthright_ready?: boolean;
  trust_profile?: TrustProfile | null;
  announcements?: { id: string; title?: string; body?: string; level?: string; cta?: string; dismissed?: boolean }[];
  next_step?: string | null;
  status_version?: string;
}

/**
 * Get onboarding status
 */
export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  const url = `${API_BASE_URL}/v1/onboarding/status`;

  const response = await fetch(url, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch onboarding status: ${response.statusText}`);
  }

  return response.json();
}

// ============================================================================
// Step 5: Welcome & Dashboard
// ============================================================================

export interface IntegrationStatus {
  identity_provider?: {
    provider: string;
    status: string;
    last_sync?: string;
    users_count?: number;
    error_message?: string;
  };
  cloud_provider?: {
    provider: string;
    status: string;
    last_events?: string;
    events_ingested?: number;
    error_message?: string;
  };
}

/**
 * Get integration status for tenant
 */
export async function getIntegrationStatus(
  tenantId: string
): Promise<IntegrationStatus> {
  const config = addTenantHeader({}, tenantId);
  const response = await tenantClient.get<IntegrationStatus>(
    `/tenants/${tenantId}/integration-status`,
    config
  );
  return response.data;
}

export interface SecuritySnapshot {
  tenant_id: string;
  security_posture: 'good' | 'needs_attention' | 'at_risk';
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  summary: string;
  key_findings: Array<{
    title: string;
    severity: string;
    description: string;
  }>;
  recommendations: Array<{
    priority: 'high' | 'medium' | 'low';
    title: string;
    description: string;
  }>;
  stats: {
    total_alerts: number;
    critical_alerts: number;
    users_count: number;
    events_last_24h: number;
  };
}

/**
 * Get security snapshot from orchestrator
 */
export async function getSecuritySnapshot(
  tenantId: string
): Promise<SecuritySnapshot> {
  const config = addTenantHeader({}, tenantId);
  const response = await orchestratorClient.get<SecuritySnapshot>(
    `/orchestrator/tenant/${tenantId}/security-snapshot`,
    config
  );
  return response.data;
}
