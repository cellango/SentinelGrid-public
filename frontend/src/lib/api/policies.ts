import { apiClient } from './client';

export interface Policy {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  policy_type: string;
  scope: string;
  scope_id?: string;
  policy_data: Record<string, any>;
  is_active: boolean;
  priority: number;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PolicyTemplate {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  policy_type: string;
  template_data: Record<string, any>;
  category?: string;
}

export interface PolicyCreatePayload {
  name: string;
  display_name: string;
  description?: string;
  policy_type: string;
  scope?: string;
  scope_id?: string;
  policy_data: Record<string, any>;
  is_active?: boolean;
  priority?: number;
}

export interface PolicyUpdatePayload {
  name?: string;
  display_name?: string;
  description?: string;
  policy_type?: string;
  scope?: string;
  scope_id?: string;
  policy_data?: Record<string, any>;
  is_active?: boolean;
  priority?: number;
}

export interface PolicyEvaluationResult {
  result: string;
  policy_id?: string;
  matched_rules?: string[];
  actions?: any[];
  explanation?: string;
}

export const policiesApi = {
  list: async (policy_type?: string): Promise<Policy[]> => {
    const params = new URLSearchParams();
    if (policy_type) params.append('policy_type', policy_type);
    const res = await apiClient.get('/iam-portal/policies', { params });
    return res.data;
  },

  get: async (id: string): Promise<Policy> => {
    const res = await apiClient.get(`/iam-portal/policies/${id}`);
    return res.data;
  },

  create: async (payload: PolicyCreatePayload): Promise<Policy> => {
    const res = await apiClient.post('/iam-portal/policies', payload);
    return res.data;
  },

  update: async (id: string, payload: PolicyUpdatePayload): Promise<Policy> => {
    const res = await apiClient.put(`/iam-portal/policies/${id}`, payload);
    return res.data;
  },

  updateStatus: async (id: string, is_active: boolean): Promise<Policy> => {
    const res = await apiClient.put(`/iam-portal/policies/${id}`, { is_active });
    return res.data;
  },

  listTemplates: async (policy_type?: string): Promise<PolicyTemplate[]> => {
    const params = new URLSearchParams();
    if (policy_type) params.append('policy_type', policy_type);
    const res = await apiClient.get('/iam-portal/policies/templates/list', { params });
    return res.data;
  },

  createFromTemplate: async (template_id: string, name: string, display_name: string): Promise<Policy> => {
    const res = await apiClient.post(`/iam-portal/policies/templates/${template_id}/create`, null, {
      params: { name, display_name }
    });
    return res.data;
  },

  evaluate: async (policy_type: string, context: Record<string, any>): Promise<PolicyEvaluationResult> => {
    const res = await apiClient.post('/iam-portal/policies/evaluate', {
      policy_type,
      ...context,
    });
    return res.data;
  },

  approve: async (id: string): Promise<Policy> => {
    const res = await apiClient.post(`/iam-portal/policies/${id}/approve`);
    return res.data;
  },

  reject: async (id: string): Promise<Policy> => {
    const res = await apiClient.post(`/iam-portal/policies/${id}/reject`);
    return res.data;
  },
};
