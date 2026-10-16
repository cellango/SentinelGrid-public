/**
 * Git Providers API Client
 */

export interface GitProviderConnectRequest {
  provider: 'github' | 'gitlab' | 'bitbucket' | 'azure_devops' | 'self_hosted';
  config: Record<string, any>;
  organization?: string;
  workspace?: string;
  project?: string;
}

export interface GitProvider {
  id: string;
  provider: string;
  organization?: string;
  workspace?: string;
  project?: string;
  status: string;
  connected_at?: string;
  last_sync_at?: string;
  repository_count?: number;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:3443';

export async function connectGitProvider(
  request: GitProviderConnectRequest
): Promise<GitProvider> {
  const response = await fetch(`${API_BASE_URL}/api/v1/git-providers/connect`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect Git provider');
  }

  return response.json();
}

export async function listGitProviders(): Promise<GitProvider[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/git-providers`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch Git providers: ${response.statusText}`);
  }

  return response.json();
}

