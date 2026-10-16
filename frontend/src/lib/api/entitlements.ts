/**
 * Entitlements API Client
 */

import { entitlementClient } from './client';

export interface Entitlement {
  id: string;
  tenant_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  granted_to_type: string;
  granted_to_id: string;
  granted_to_name?: string;
  status: string;
  granted_by: string;
  granted_at: string;
  expires_at?: string;
  last_used_at?: string;
  usage_count_90d: number;
  metadata: Record<string, any>;
}

// Entitlements API
export const entitlementsApi = {
  /**
   * Get entitlement by ID
   */
  get: async (entitlementId: string): Promise<Entitlement> => {
    const response = await entitlementClient.get(`/entitlements/${entitlementId}`);
    return response.data;
  },

  /**
   * List entitlements
   */
  list: async (params?: {
    tenant_id?: string;
    user_id?: string;
    resource_type?: string;
    action?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<Entitlement[]> => {
    const response = await entitlementClient.get('/entitlements', { params });
    return response.data;
  },
};

