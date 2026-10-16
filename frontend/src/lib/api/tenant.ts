/**
 * Tenant Service API Client
 * Handles tenant provisioning and management
 */

import { apiClient } from './client';

export interface TenantProvisionRequest {
  company_name: string;
  admin_email: string;
  admin_password: string;
  idp_mode?: 'sentinelgrid' | 'existing_sso';
}

export interface TenantResponse {
  tenant_id: string;
  realm: string;
  admin_username: string;
  status: string;
  keycloak_url?: string;
}

/**
 * Provision a new tenant
 */
export async function provisionTenant(data: TenantProvisionRequest): Promise<TenantResponse> {
  const response = await apiClient.post<TenantResponse>('/tenants/provision', data);
  return response.data;
}

/**
 * Get tenant details
 */
export async function getTenant(tenantId: string): Promise<TenantResponse> {
  const response = await apiClient.get<TenantResponse>(`/tenants/${tenantId}`);
  return response.data;
}

