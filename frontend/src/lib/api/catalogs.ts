import { apiClient } from './client';

export interface CatalogDetection {
  id: string;
  name: string;
  category: string;
  severity: string;
  incident_type: string;
  default_playbook_key: string;
  alert_type?: string;
  mitre_tactics?: string[];
  mitre_techniques?: string[];
  nist_controls?: string[];
  query_template_ref?: string;
  parameters?: Record<string, any>;
  owner?: string;
  status?: string;
}

export interface CatalogPlaybook {
  id: string;
  incident_type: string;
  name: string;
  automation_default?: string;
  mitre_tactics?: string[];
  mitre_techniques?: string[];
  nist_controls?: string[];
  runbook_ref?: string;
  owner?: string;
  status?: string;
}

export const catalogApi = {
  listDetections: async (): Promise<CatalogDetection[]> => {
    const res = await apiClient.get('/catalog/detections');
    return res.data?.detections || [];
  },
  listPlaybooks: async (): Promise<CatalogPlaybook[]> => {
    const res = await apiClient.get('/catalog/playbooks');
    return res.data?.playbooks || [];
  },
};
