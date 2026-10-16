/**
 * IAM Portal API client
 */

import { withSessionAuthorization } from '@/lib/auth/session';

// Default to same-origin so browser requests stay HTTPS and pick up the Next.js proxy.
// Normalize to avoid double-appending /api when a base is provided.
const rawApiBase =
  typeof window !== 'undefined' ? `${window.location.origin}/api` : process.env.NEXT_PUBLIC_API_URL || '';
const trimmedBase = rawApiBase.endsWith('/') ? rawApiBase.slice(0, -1) : rawApiBase;
const API_BASE_URL = trimmedBase.endsWith('/api') ? trimmedBase.slice(0, -4) : trimmedBase;
const buildUrl = (path: string) => `${API_BASE_URL}${path}`;

// Types
export interface App {
  id: string;
  tenant_id: string;
  name: string;
  display_name: string;
  description?: string;
  app_type: string;
  protocol?: string;
  icon_url?: string;
  is_active: boolean;
  config?: Record<string, any>;
  client_id?: string;
  issuer?: string;
  created_at: string;
  updated_at: string;
}
export interface AppAssignment {
  id: string;
  subject_type: 'group' | 'user';
  subject_id: string;
  subject_name?: string;
  entitlement_id: string;
  entitlement_name?: string;
}

export interface Entitlement {
  id: string;
  tenant_id: string;
  app_id: string;
  name: string;
  display_name: string;
  description?: string;
  entitlement_type: string;
  is_privileged: boolean;
  requires_mfa: boolean;
  risk_level: string;
  created_at: string;
  updated_at: string;
}

export interface AccessProfile {
  id: string;
  tenant_id: string;
  name: string;
  display_name: string;
  description?: string;
  is_default: boolean;
  is_system: boolean;
   is_birthright?: boolean;
   scope?: string | null;
  entitlements: Entitlement[];
  created_at: string;
  updated_at: string;
}

export interface UserEntitlement {
  id: string;
  tenant_id: string;
  user_id: string;
  entitlement_id: string;
  entitlement?: Entitlement;
  granted_by?: string;
  granted_at: string;
  expires_at?: string;
  status: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface AccessRequest {
  id: string;
  tenant_id: string;
  requested_by: string;
  entitlement_id: string;
  entitlement?: Entitlement;
  reason: string;
  duration_days?: number;
  status: string;
  requested_at: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface AccessProfileCreate {
  name: string;
  display_name: string;
  description?: string;
  is_default?: boolean;
  is_birthright?: boolean;
  scope?: string;
  entitlement_ids?: string[];
}

export interface UserInfo {
  user_id: string;
  username: string;
  email: string;
  first_name?: string;
  last_name?: string;
  enabled: boolean;
  manager_id?: string;
  department?: string;
  team?: string;
  location?: string;
  employee_type?: string;
  is_privileged?: boolean;
  access_profile_id?: string;
  tenant_id?: string;
  entitlements: UserEntitlement[];
  created_at?: string;
  activate_at?: string | null;
  deactivate_at?: string | null;
}

export interface UserCreate {
  username: string;
  email: string;
  tenant_id: string;
  first_name?: string;
  last_name?: string;
  department?: string;
  team?: string;
  manager_id?: string;
  location?: string;
  employee_type?: string;
  access_profile_id?: string;
  make_admin?: boolean;
  is_privileged?: boolean;
}

export interface MyAccessSummary {
  current_entitlements: UserEntitlement[];
  pending_requests: AccessRequest[];
  available_entitlements: Entitlement[];
}

export interface BirthrightRule {
  id: string;
  tenant_id: string;
  name?: string | null;
  attribute_key: 'department' | 'team' | 'location' | 'manager_id' | 'employee_type' | string;
  match_value: string;
  access_profile_id: string;
  is_active: boolean;
}

export interface LifecycleSchedule {
  activate_at?: string | null;
  deactivate_at?: string | null;
}

export interface AuditEntry {
  action: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  details?: Record<string, any> | null;
  created_at?: string | null;
}

export type TimelineEntry = AuditEntry;

// Helper function for API calls
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = withSessionAuthorization({
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  });
  
  const response = await fetch(buildUrl(`/api/iam-portal${endpoint}`), {
    ...options,
    headers,
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// Apps API
export async function getApps(): Promise<App[]> {
  return apiCall<App[]>('/apps');
}

export async function getApp(appId: string): Promise<App> {
  return apiCall<App>(`/apps/${appId}`);
}

export async function listAppAssignments(appId: string): Promise<AppAssignment[]> {
  try {
    return await apiCall<AppAssignment[]>(`/apps/${appId}/assignments`);
  } catch {
    return [];
  }
}

export async function addAppAssignment(
  appId: string,
  payload: { subject_type: 'group' | 'user'; subject_id: string; entitlement_id: string }
): Promise<{ ok: boolean }> {
  try {
    await apiCall(`/apps/${appId}/assignments`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    return { ok: true };
  } catch (err: any) {
    throw err;
  }
}

export async function removeAppAssignment(appId: string, assignmentId: string): Promise<{ ok: boolean }> {
  try {
    await apiCall(`/apps/${appId}/assignments/${assignmentId}`, { method: 'DELETE' });
    return { ok: true };
  } catch (err: any) {
    throw err;
  }
}

// Birthright rules
export async function getBirthrightRules(): Promise<BirthrightRule[]> {
  return apiCall<BirthrightRule[]>('/birthright-rules');
}

export async function createBirthrightRule(payload: {
  name?: string;
  attribute_key: 'department' | 'team' | 'location' | 'manager_id' | 'employee_type';
  match_value: string;
  access_profile_id: string;
}): Promise<BirthrightRule> {
  return apiCall<BirthrightRule>('/birthright-rules', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deleteBirthrightRule(ruleId: string): Promise<{ success: boolean }> {
  return apiCall<{ success: boolean }>(`/birthright-rules/${ruleId}`, {
    method: 'DELETE',
  });
}

// Lifecycle scheduling
export async function getLifecycleSchedule(userId: string): Promise<LifecycleSchedule> {
  return apiCall<LifecycleSchedule>(`/users/${userId}/lifecycle`);
}

export async function setLifecycleSchedule(userId: string, payload: LifecycleSchedule): Promise<LifecycleSchedule> {
  return apiCall<LifecycleSchedule>(`/users/${userId}/lifecycle`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getUserAudit(userId: string): Promise<AuditEntry[]> {
  return apiCall<AuditEntry[]>(`/users/${userId}/audit`);
}

export async function getUserTimeline(userId: string): Promise<TimelineEntry[]> {
  return apiCall<TimelineEntry[]>(`/users/${userId}/timeline`);
}

export async function setAppStatus(appId: string, is_active: boolean): Promise<{ ok: boolean; is_active: boolean }> {
  return apiCall(`/apps/${appId}/status`, {
    method: 'POST',
    body: JSON.stringify({ is_active }),
  });
}

// Entitlements API
export async function getEntitlements(appId?: string): Promise<Entitlement[]> {
  const params = appId ? `?app_id=${appId}` : '';
  return apiCall<Entitlement[]>(`/entitlements${params}`);
}

// Access Profiles API
export async function getAccessProfiles(): Promise<AccessProfile[]> {
  return apiCall<AccessProfile[]>('/access-profiles');
}

export async function createAccessProfile(payload: AccessProfileCreate): Promise<AccessProfile> {
  return apiCall<AccessProfile>('/access-profiles', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getAccessProfile(profileId: string): Promise<AccessProfile> {
  return apiCall<AccessProfile>(`/access-profiles/${profileId}`);
}

// Birthrights API (leveraging access profiles with a birthright flag)
export async function getBirthrights(): Promise<AccessProfile[]> {
  return apiCall<AccessProfile[]>('/birthrights');
}

export async function createBirthright(payload: AccessProfileCreate): Promise<AccessProfile> {
  return apiCall<AccessProfile>('/birthrights', {
    method: 'POST',
    body: JSON.stringify({ ...payload, is_birthright: true }),
  });
}

// Users API
export async function getIAMUsers(filters?: { department?: string; team?: string; privileged?: boolean }): Promise<UserInfo[]> {
  const params = new URLSearchParams();
  if (filters?.department) params.append('department', filters.department);
  if (filters?.team) params.append('team', filters.team);
  if (typeof filters?.privileged === 'boolean') params.append('privileged', String(filters.privileged));
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiCall<UserInfo[]>(`/users${query}`);
}

export async function getIAMUser(userId: string): Promise<UserInfo> {
  return apiCall<UserInfo>(`/users/${userId}`);
}

export interface ArtifactAccess {
  tenant_namespace: string;
  ecr_repo: string;
  helm_repo: string;
  s3_prefix: string;
  notes?: string;
}

export async function getArtifactAccess(): Promise<ArtifactAccess> {
  return apiCall<ArtifactAccess>('/onboarding/artifacts');
}

export async function createIAMUser(userData: UserCreate): Promise<UserInfo> {
  return apiCall<UserInfo>('/users', {
    method: 'POST',
    body: JSON.stringify(userData),
  });
}

export async function updateIAMUser(userId: string, updates: Partial<UserCreate>): Promise<UserInfo> {
  return apiCall<UserInfo>(`/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  });
}

export async function bulkUserAction(body: {
  action: 'suspend' | 'offboard' | 'mark_privileged' | 'unmark_privileged';
  user_ids: string[];
}): Promise<{ action: string; updated: number }> {
  return apiCall<{ action: string; updated: number }>('/users/bulk/actions', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// Access Requests API
export async function getAccessRequests(userId?: string, status?: string): Promise<AccessRequest[]> {
  const params = new URLSearchParams();
  if (userId) params.append('user_id', userId);
  if (status) params.append('status', status);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiCall<AccessRequest[]>(`/access-requests${query}`);
}

export async function createAccessRequest(requestData: {
  entitlement_id: string;
  reason: string;
  duration_days?: number;
}): Promise<AccessRequest> {
  return apiCall<AccessRequest>('/access-requests', {
    method: 'POST',
    body: JSON.stringify(requestData),
  });
}

export async function approveAccessRequest(requestId: string, notes?: string): Promise<void> {
  return apiCall<void>(`/access-requests/${requestId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

export async function denyAccessRequest(requestId: string, notes?: string): Promise<void> {
  return apiCall<void>(`/access-requests/${requestId}/deny`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

// My Access API
export async function getMyAccess(): Promise<MyAccessSummary> {
  return apiCall<MyAccessSummary>('/my-access');
}

// Policy Types
export interface Policy {
  id: string;
  tenant_id: string;
  name: string;
  display_name: string;
  description?: string;
  policy_type: 'signon' | 'access' | 'approval' | 'sod' | 'authorization';
  scope: 'tenant' | 'app' | 'entitlement';
  scope_id?: string;
  policy_data: any; // Policy DSL JSON
  is_active: boolean;
  priority: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyTemplate {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  policy_type: 'signon' | 'access' | 'approval' | 'sod' | 'authorization';
  template_data: any;
  is_system: boolean;
  category?: string;
  created_at: string;
  updated_at: string;
}

export interface PolicyCreate {
  name: string;
  display_name: string;
  description?: string;
  policy_type: 'signon' | 'access' | 'approval' | 'sod' | 'authorization';
  scope?: 'tenant' | 'app' | 'entitlement';
  scope_id?: string;
  policy_data: any;
  is_active?: boolean;
  priority?: number;
}

export type PolicyBundle = Policy;

// Policies API
export async function getPolicies(policyType?: string, scope?: string, scopeId?: string): Promise<Policy[]> {
  const params = new URLSearchParams();
  if (policyType) params.append('policy_type', policyType);
  if (scope) params.append('scope', scope);
  if (scopeId) params.append('scope_id', scopeId);
  const query = params.toString() ? `?${params.toString()}` : '';
  return apiCall<Policy[]>(`/policies${query}`);
}

export async function getPolicy(policyId: string): Promise<Policy> {
  return apiCall<Policy>(`/policies/${policyId}`);
}

export async function createPolicy(policyData: PolicyCreate): Promise<Policy> {
  return apiCall<Policy>('/policies', {
    method: 'POST',
    body: JSON.stringify(policyData),
  });
}

export async function updatePolicy(policyId: string, policyData: Partial<PolicyCreate>): Promise<Policy> {
  return apiCall<Policy>(`/policies/${policyId}`, {
    method: 'PUT',
    body: JSON.stringify(policyData),
  });
}

export async function deletePolicy(policyId: string): Promise<void> {
  return apiCall<void>(`/policies/${policyId}`, {
    method: 'DELETE',
  });
}

// Policy Templates API
export async function getPolicyTemplates(policyType?: string): Promise<PolicyTemplate[]> {
  const params = policyType ? `?policy_type=${policyType}` : '';
  // Use /templates/list to avoid path conflicts with /{policy_id}
  return apiCall<PolicyTemplate[]>(`/policies/templates/list${params}`);
}

export async function createPolicyFromTemplate(
  templateId: string,
  name: string,
  displayName: string
): Promise<Policy> {
  return apiCall<Policy>(`/policies/templates/${templateId}/create?name=${encodeURIComponent(name)}&display_name=${encodeURIComponent(displayName)}`, {
    method: 'POST',
  });
}

// Seed bundles (sg_admin)
export async function listPolicyBundles(): Promise<PolicyBundle[]> {
  return apiCall<PolicyBundle[]>('/policies/bundles');
}

export async function clonePolicyBundle(
  bundleId: string,
  payload?: { name?: string; display_name?: string }
): Promise<PolicyBundle> {
  return apiCall<PolicyBundle>(`/policies/bundles/${bundleId}/clone`, {
    method: 'POST',
    body: payload ? JSON.stringify(payload) : undefined,
  });
}
