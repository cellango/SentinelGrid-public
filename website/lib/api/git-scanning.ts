/**
 * Git Security Scanning API Client
 */

export interface GitFinding {
  id: string;
  repo_id: string;
  finding_type: 'secret' | 'vulnerability' | 'code_issue' | 'dependency_vulnerability';
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  title: string;
  description?: string;
  file_path?: string;
  line_number?: number;
  commit_sha?: string;
  scanner_tool: string;
  scanner_rule_id?: string;
  status: 'open' | 'resolved' | 'false_positive' | 'ignored';
  detected_at: string;
}

export interface FindingListResponse {
  findings: GitFinding[];
  total: number;
  page: number;
  page_size: number;
}

export interface ScanRequest {
  repo_id: string;
  scan_types: ('secrets' | 'dependencies' | 'code')[];
  branch?: string;
}

export interface ScanResponse {
  scan_id: string;
  repo_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  scan_types: string[];
  findings_count: number;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:3443';

export async function scanRepository(request: ScanRequest): Promise<ScanResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/git-scanning/scan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to start scan: ${response.statusText}`);
  }

  return response.json();
}

export async function listFindings(
  filters?: {
    repo_id?: string;
    finding_type?: string;
    severity?: string;
    status?: string;
  },
  page: number = 1,
  pageSize: number = 20
): Promise<FindingListResponse> {
  const params = new URLSearchParams();
  
  if (filters?.repo_id) params.append('repo_id', filters.repo_id);
  if (filters?.finding_type) params.append('finding_type', filters.finding_type);
  if (filters?.severity) params.append('severity', filters.severity);
  if (filters?.status) params.append('status', filters.status);
  
  params.append('page', page.toString());
  params.append('page_size', pageSize.toString());

  const response = await fetch(`${API_BASE_URL}/api/v1/git-scanning/findings?${params}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch findings: ${response.statusText}`);
  }

  return response.json();
}

export async function getFinding(findingId: string): Promise<GitFinding> {
  const response = await fetch(`${API_BASE_URL}/api/v1/git-scanning/findings/${findingId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch finding: ${response.statusText}`);
  }

  return response.json();
}

export async function updateFindingStatus(
  findingId: string,
  status: 'open' | 'resolved' | 'false_positive' | 'ignored'
): Promise<{ success: boolean; status: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/git-scanning/findings/${findingId}?status=${status}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to update finding: ${response.statusText}`);
  }

  return response.json();
}

