import { apiClient } from './client';

export type FixGroup = {
  id: string;
  type: string;
  description?: string;
  fixed_in_target?: string;
  priority?: string;
  sla_due?: string;
  status?: string;
  owning_team_id?: string;
  ai_guidance?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  ticket_id?: string;
  ticket_status?: string;
};

export type ScanDetail = {
  id: string;
  scan_type?: string;
  scanner_id?: string;
  target_ref?: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  started_at?: string;
  finished_at?: string;
  summary?: {
    findings?: number;
    severity?: string;
    type?: string;
    target_url?: string;
    repo?: string;
    cves?: { id: string; cvss?: number; description?: string; fix?: string }[];
    remediation?: { summary?: string; steps?: string[]; validation?: string[] };
    externally_exposed?: boolean;
    nist_controls?: string[];
    mitre_techniques?: string[];
    [key: string]: any;
  };
  artifact_url?: string;
  raw_artifact_url?: string;
  fix_groups?: FixGroup[];
};

export async function getScan(scanId: string): Promise<ScanDetail> {
  try {
    const response = await apiClient.get<ScanDetail>(`/orchestrator/scans/${scanId}`);
    return response.data;
  } catch (error: any) {
    const status = error?.response?.status;
    const wrappedError: any = new Error(
      error?.response?.data?.detail || error?.message || 'Failed to fetch scan'
    );
    wrappedError.status = status;
    throw wrappedError;
  }
}
