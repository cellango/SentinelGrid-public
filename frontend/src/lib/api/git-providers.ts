/**
 * Git Providers API Client (frontend)
 */

import { withSessionAuthorization } from '@/lib/auth/session';

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

// Use API gateway via nginx when running behind https://localhost:3443
const API_BASE_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin}/api`
    : process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

export async function connectGitProvider(
  request: GitProviderConnectRequest
): Promise<GitProvider> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/git-providers/connect`
    : `${API_BASE_URL}/api/v1/git-providers/connect`;

  const response = await fetch(url, {
    method: 'POST',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to connect Git provider');
  }

  return response.json();
}

export async function listGitProviders(): Promise<GitProvider[]> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/git-providers`
    : `${API_BASE_URL}/api/v1/git-providers`;

  const response = await fetch(url, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch Git providers: ${response.statusText}`);
  }

  return response.json();
}
