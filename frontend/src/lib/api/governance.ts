/**
 * Governance API Client
 * Campaign and certification management
 */

import { entitlementClient } from './client';
import type { PaginatedResponse } from './client';

export interface Campaign {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  reviewer_type: 'self' | 'manager' | 'admin';
  auto_revoke_days?: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface CampaignCreate {
  tenant_id: string;
  name: string;
  description?: string;
  start_date: string;
  end_date: string;
  reviewer_type: 'self' | 'manager' | 'admin';
  auto_revoke_days?: number;
  entitlement_patterns?: string[];
}

export interface CampaignUpdate {
  name?: string;
  description?: string;
  start_date?: string;
  end_date?: string;
  status?: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  reviewer_type?: 'self' | 'manager' | 'admin';
  auto_revoke_days?: number;
}

export interface Certification {
  id: string;
  campaign_id: string;
  entitlement_id: string;
  user_id: string;
  reviewer_id: string;
  review_status: 'pending' | 'approved' | 'revoked' | 'retained';
  review_date?: string;
  comments?: string;
  created_at: string;
  updated_at: string;
}

export interface CertificationDecision {
  decision: 'approved' | 'revoked' | 'retained';
  comments?: string;
}

export interface BulkCertificationRequest {
  certification_ids: string[];
  decision: 'approved' | 'revoked' | 'retained';
  comments?: string;
}

export interface CampaignProgress {
  total: number;
  pending: number;
  approved: number;
  revoked: number;
  questioned: number;
  percentage_complete: number;
}

// Campaign Management
export const campaignsApi = {
  /**
   * List campaigns
   */
  list: async (params?: {
    tenant_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<Campaign[]> => {
    const response = await entitlementClient.get('/governance/campaigns', { params });
    return response.data;
  },

  /**
   * Get campaign by ID
   */
  get: async (campaignId: string): Promise<Campaign> => {
    const response = await entitlementClient.get(`/governance/campaigns/${campaignId}`);
    return response.data;
  },

  /**
   * Create new campaign
   */
  create: async (campaign: CampaignCreate): Promise<Campaign> => {
    const response = await entitlementClient.post('/governance/campaigns', campaign);
    return response.data;
  },

  /**
   * Update campaign
   */
  update: async (campaignId: string, updates: CampaignUpdate): Promise<Campaign> => {
    const response = await entitlementClient.put(`/governance/campaigns/${campaignId}`, updates);
    return response.data;
  },

  /**
   * Start campaign (generate certifications)
   */
  start: async (campaignId: string): Promise<Campaign> => {
    const response = await entitlementClient.post(`/governance/campaigns/${campaignId}/start`);
    return response.data;
  },

  /**
   * Complete campaign
   */
  complete: async (campaignId: string, autoRevoke: boolean = true): Promise<Campaign> => {
    const response = await entitlementClient.post(
      `/governance/campaigns/${campaignId}/complete`,
      null,
      { params: { auto_revoke: autoRevoke } }
    );
    return response.data;
  },

  /**
   * Get campaign progress
   */
  getProgress: async (campaignId: string): Promise<CampaignProgress> => {
    // This might need to be calculated from certifications
    // For now, we'll fetch certifications and calculate
    const certifications = await certificationsApi.list({ campaign_id: campaignId, limit: 1000 });
    
    const total = certifications.length;
    const pending = certifications.filter(c => c.review_status === 'pending').length;
    const approved = certifications.filter(c => c.review_status === 'approved' || c.review_status === 'retained').length;
    const revoked = certifications.filter(c => c.review_status === 'revoked').length;
    
    return {
      total,
      pending,
      approved,
      revoked,
      questioned: 0, // TODO: Add questioned status
      percentage_complete: total > 0 ? ((total - pending) / total) * 100 : 0,
    };
  },
};

// Certification Management
export const certificationsApi = {
  /**
   * Get pending certifications
   */
  getPending: async (params?: {
    user_id?: string;
    campaign_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<Certification[]> => {
    const response = await entitlementClient.get('/governance/certifications/pending', { params });
    return response.data;
  },

  /**
   * List certifications
   */
  list: async (params?: {
    campaign_id?: string;
    user_id?: string;
    review_status?: string;
    limit?: number;
    offset?: number;
  }): Promise<Certification[]> => {
    const response = await entitlementClient.get('/governance/certifications', { params });
    return response.data;
  },

  /**
   * Submit certification decision
   */
  certify: async (certificationId: string, decision: CertificationDecision): Promise<Certification> => {
    const response = await entitlementClient.post(
      `/governance/certifications/${certificationId}/certify`,
      decision
    );
    return response.data;
  },

  /**
   * Bulk certify
   */
  bulkCertify: async (request: BulkCertificationRequest): Promise<{ certified_count: number; decision: string }> => {
    const response = await entitlementClient.post('/governance/certifications/bulk-certify', request);
    return response.data;
  },
};

