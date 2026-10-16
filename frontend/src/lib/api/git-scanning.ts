/**
 * Git Scanning API Client
 */

import { withSessionAuthorization } from '@/lib/auth/session';

export interface Finding {
  id: string;
  repository: string;
  file_path: string;
  line_number: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  rule_id: string;
  description: string;
  title?: string;
  finding_type?: string;
  scanner_tool?: string;
  commit_sha?: string;
  detected_at: string;
  status: 'open' | 'resolved' | 'false_positive';
}

export interface FindingListResponse {
  findings: Finding[];
  total: number;
  page: number;
  page_size: number;
}

const API_BASE_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin}/api`
    : process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

export async function listFindings(
  params?: {
    repository?: string;
    severity?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }
): Promise<FindingListResponse> {
  const queryParams = new URLSearchParams();
  if (params?.repository) queryParams.append('repository', params.repository);
  if (params?.severity) queryParams.append('severity', params.severity);
  if (params?.status) queryParams.append('status', params.status);
  if (params?.page) queryParams.append('page', params.page.toString());
  if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/git-scanning/findings?${queryParams}`
    : `${API_BASE_URL}/api/v1/git-scanning/findings?${queryParams}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch git scanning findings: ${response.statusText}`);
  }

  return response.json();
}

export async function updateFindingStatus(
  findingId: string,
  status: 'open' | 'resolved' | 'false_positive'
): Promise<Finding> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/git-scanning/findings/${findingId}`
    : `${API_BASE_URL}/api/v1/git-scanning/findings/${findingId}`;

  const response = await fetch(url, {
    method: 'PATCH',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
    body: JSON.stringify({ status }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update finding status: ${response.statusText}`);
  }

  return response.json();
}
