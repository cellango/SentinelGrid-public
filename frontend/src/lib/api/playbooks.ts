/**
 * Playbooks API Client
 * Routes through API Gateway on port 8082
 */

import { apiClient } from './client';

export interface Playbook {
  id: string;
  tenant_id: string;
  name: string;
  description?: string;
  category?: 'phishing' | 'suspicious_login' | 'malware' | 'custom';
  version: string;
  workflow?: {
    nodes: any[];
    edges: any[];
    viewport?: any;
  } | null;
  workflow_status?: 'stored' | 'missing' | 'external_reference';
  workflow_message?: string | null;
  workflow_ref?: string | null;
  timeout_seconds: number;
  retry_policy?: {
    max_retries: number;
    retry_delay_seconds: number;
    backoff_multiplier: number;
  };
  on_failure: 'fail' | 'continue' | 'escalate';
  is_template: boolean;
  requires_approval: boolean;
  tags: string[];
  playbook_key?: string;
  severity_default?: string;
  applicable_sources?: string[];
  triggers?: string[];
  prerequisites?: string[];
  artifacts_required?: string[];
  phases?: any;
  cis_controls?: string[];
  nist_controls?: string[];
  mitre_tactics?: string[];
  mitre_techniques?: string[];
  trigger_conditions?: any;
  auto_trigger_enabled?: boolean;
  trigger_priority?: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
  n8n_workflow_id?: string;
  n8n_webhook_url?: string;
}

export interface PlaybookCreate {
  name: string;
  description?: string;
  category?: string;
  version?: string;
  workflow: {
    nodes: any[];
    edges: any[];
  };
  timeout_seconds?: number;
  retry_policy?: any;
  on_failure?: string;
  is_template?: boolean;
  requires_approval?: boolean;
  tags?: string[];
  trigger_conditions?: any;
  auto_trigger_enabled?: boolean;
  trigger_priority?: number;
}

export interface PlaybookUpdate {
  name?: string;
  description?: string;
  category?: string;
  version?: string;
  workflow?: {
    nodes: any[];
    edges: any[];
  };
  timeout_seconds?: number;
  retry_policy?: any;
  on_failure?: string;
  is_template?: boolean;
  requires_approval?: boolean;
  tags?: string[];
  trigger_conditions?: any;
  auto_trigger_enabled?: boolean;
  trigger_priority?: number;
}

export interface PlaybookCopy {
  new_name: string;
  new_key?: string;
  new_version?: string;
}

export interface PlaybookValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface PlaybookExecutionResponse {
  execution_id: string;
  status: string;
  approval_status?: string;
  workflow_exec_id?: string | null;
  trigger_type?: string;
  trigger_id?: string | null;
  alert_id?: string | null;
  message?: string;
}

export interface PlaybookExecutionRecord {
  id: string;
  tenant_id?: string;
  playbook_id?: string | null;
  playbook_name?: string | null;
  playbook_version_id?: string | null;
  trigger_type?: string;
  trigger_id?: string | null;
  status: string;
  workflow_exec_id?: string | null;
  triggered_by?: string;
  approval_status?: string;
  started_at?: string | null;
  completed_at?: string | null;
  result?: any;
  logs?: any[];
  alert_id?: string | null;
  detection_rule_id?: string | null;
  detection_rule_version_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export function describePlaybookExecution(response?: Partial<PlaybookExecutionResponse>): string {
  if (!response) {
    return 'Execution request recorded.';
  }
  if (response.message) {
    return response.message;
  }
  if (response.approval_status === 'pending') {
    return 'Execution request recorded and awaiting approval.';
  }
  if (response.status === 'pending') {
    return 'Execution request recorded and pending worker handoff.';
  }
  if (response.status === 'running') {
    return 'Execution started.';
  }
  if (response.status === 'completed') {
    return 'Execution completed.';
  }
  if (response.status === 'failed') {
    return 'Execution failed.';
  }
  return `Execution status: ${response.status || 'pending'}`;
}

export const playbooksApi = {
  /**
   * List all playbooks for the current tenant
   */
  list: async (category?: string, is_template?: boolean): Promise<Playbook[]> => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (is_template !== undefined) params.append('is_template', String(is_template));
    
    const response = await apiClient.get(`/playbooks?${params.toString()}`);
    const data = response.data;
    if (Array.isArray(data)) return data;
    if (data?.items && Array.isArray(data.items)) return data.items;
    return [];
  },

  /**
   * Get a single playbook by ID
   */
  get: async (id: string): Promise<Playbook> => {
    const response = await apiClient.get(`/playbooks/${id}`);
    return response.data;
  },

  /**
   * Create a new playbook
   */
  create: async (playbook: PlaybookCreate): Promise<Playbook> => {
    const response = await apiClient.post('/playbooks', playbook);
    return response.data;
  },

  /**
   * Update an existing playbook
   */
  update: async (id: string, playbook: PlaybookUpdate): Promise<Playbook> => {
    const response = await apiClient.put(`/playbooks/${id}`, playbook);
    return response.data;
  },

  /**
   * Delete a playbook
   */
  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/playbooks/${id}`);
  },

  /**
   * Copy/duplicate a playbook (customer-managed SOC)
   */
  copy: async (id: string, copyRequest: PlaybookCopy): Promise<Playbook> => {
    const response = await apiClient.post(`/playbooks/${id}/clone`, copyRequest);
    return response.data;
  },

  /**
   * Validate a playbook structure
   */
  validate: async (id: string): Promise<PlaybookValidationResult> => {
    const response = await apiClient.post(`/playbooks/${id}/validate`);
    return response.data;
  },

  preview: async (id: string, payload?: any): Promise<PlaybookValidationResult> => {
    // Alias to validate for now
    const response = await apiClient.post(`/playbooks/${id}/validate`, payload || {});
    return response.data;
  },

  approve: async (id: string): Promise<Playbook> => {
    const response = await apiClient.post(`/soar/playbooks/${id}/approve`);
    return response.data;
  },

  reject: async (id: string): Promise<Playbook> => {
    const response = await apiClient.post(`/soar/playbooks/${id}/reject`);
    return response.data;
  },

  /**
   * Execute a playbook
   */
  execute: async (
    id: string,
    triggerType: string,
    triggerId?: string,
    parameters?: any
  ): Promise<PlaybookExecutionResponse> => {
    const response = await apiClient.post(`/playbooks/${id}/execute`, {
      trigger_type: triggerType,
      trigger_id: triggerId,
      parameters,
    });
    return response.data;
  },

  /**
   * List playbook executions (with optional filters)
   */
  listExecutions: async (params?: {
    status?: string;
    approval_status?: string;
    alert_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<PlaybookExecutionRecord[]> => {
    const response = await apiClient.get('/playbook-executions', {
      params,
    });
    return response.data || [];
  },

  /**
   * Get execution status
   */
  getExecution: async (executionId: string): Promise<PlaybookExecutionRecord> => {
    try {
      const response = await apiClient.get(`/playbook-executions/${executionId}`);
      const data = response.data || {};
      const ctx = data.context || data.result || {};
      return {
        ...data,
        playbook_id: data.playbook_id || data.playbook?.id || ctx.playbook_id,
        playbook_version_id: data.playbook_version_id || ctx.playbook_version_id,
        detection_rule_id: data.detection_rule_id || ctx.detection_rule_id,
        detection_rule_version_id: data.detection_rule_version_id || ctx.detection_rule_version_id,
        alert_id: data.alert_id || ctx.alert_id,
      };
    } catch {
      return { id: executionId, status: 'pending', approval_status: 'pending' };
    }
  },

  /**
   * Get observable types
   */
  getObservableTypes: async (): Promise<{ types: Array<{ id: string; label: string }> }> => {
    // Stub - return empty types
    return { types: [] };
  },

  /**
   * List analyzers
   */
  listAnalyzers: async (dataType?: string): Promise<{ analyzers: any[] }> => {
    // Stub - return empty analyzers
    return { analyzers: [] };
  },

  /**
   * Get analyzer details
   */
  getAnalyzer: async (analyzerId: string): Promise<any> => {
    // Stub - return basic analyzer
    return { id: analyzerId, name: 'Analyzer', data_type_list: [] };
  },

  /**
   * Create observable in TheHive
   */
  createObservable: async (observable: {
    data_type: string;
    data: string;
    tags?: string[];
    ioc?: boolean;
    sighted?: boolean;
    message?: string;
    case_id?: string;
  }): Promise<any> => {
    // Stub - return created observable
    return { id: 'obs-1', ...observable };
  },

  /**
   * Run analyzer on observable
   */
  runAnalyzer: async (
    analyzerId: string,
    observableId: string,
    parameters?: any
  ): Promise<any> => {
    // Stub - return job result
    return { job_id: 'job-1', status: 'pending' };
  },
};
