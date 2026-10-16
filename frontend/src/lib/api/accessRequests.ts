/**
 * Access Requests API Client
 */

import { entitlementClient } from './client';

export interface AccessRequest {
  id: string;
  tenant_id: string;
  requested_by: string;
  requested_for: string;
  resource_type: string;
  resource_id: string;
  action: string;
  justification: string;
  status: 'pending' | 'approved' | 'denied' | 'cancelled';
  reviewer_id?: string;
  reviewed_at?: string;
  review_comments?: string;
  expires_at?: string;
  entitlement_id?: string;
  created_at: string;
  updated_at: string;
}

export interface AccessRequestCreate {
  tenant_id: string;
  requested_for?: string;
  resource_type: string;
  resource_id: string;
  action: string;
  justification: string;
  expires_at?: string;
}

export interface AccessRequestReview {
  decision: 'approve' | 'deny';
  comments?: string;
}

export interface AccessRequestHistory {
  id: string;
  request_id: string;
  event_type: string;
  performed_by: string;
  performed_at: string;
  comments?: string;
  old_status?: string;
  new_status?: string;
}

// Access Requests API
export const accessRequestsApi = {
  /**
   * Create access request
   */
  create: async (request: AccessRequestCreate): Promise<AccessRequest> => {
    const response = await entitlementClient.post('/v1/access-requests', request);
    return response.data;
  },

  /**
   * List access requests
   */
  list: async (params?: {
    tenant_id?: string;
    status?: string;
    requested_by?: string;
    reviewer_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<AccessRequest[]> => {
    const response = await entitlementClient.get('/v1/access-requests', { params });
    return response.data;
  },

  /**
   * Get access request by ID
   */
  get: async (requestId: string): Promise<AccessRequest> => {
    const response = await entitlementClient.get(`/v1/access-requests/${requestId}`);
    return response.data;
  },

  /**
   * Review (approve/deny) access request
   */
  review: async (requestId: string, review: AccessRequestReview): Promise<AccessRequest> => {
    const response = await entitlementClient.post(`/v1/access-requests/${requestId}/review`, review);
    return response.data;
  },

  /**
   * Get access request history
   */
  getHistory: async (requestId: string): Promise<AccessRequestHistory[]> => {
    const response = await entitlementClient.get(`/v1/access-requests/${requestId}/history`);
    return response.data;
  },

  /**
   * Cancel access request
   */
  cancel: async (requestId: string): Promise<AccessRequest> => {
    const response = await entitlementClient.post(`/v1/access-requests/${requestId}/cancel`);
    return response.data;
  },
};
