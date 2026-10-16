/**
 * Hardened Images API Client (frontend)
 */

import { withSessionAuthorization } from '@/lib/auth/session';

export interface HardenedImage {
  id: string;
  os_name: string;
  os_version: string;
  cloud_provider: string;
  image_id: string;
  image_name: string;
  region?: string;
  hardening_level: string;
  cis_benchmark_version?: string;
  agent_version: string;
  agent_installed: boolean;
  build_date: string;
  status: string;
  metadata?: Record<string, any>;
  download_url?: string;
  documentation_url?: string;
}

export interface HardenedImageListResponse {
  images: HardenedImage[];
  total: number;
  page: number;
  page_size: number;
}

// Use API gateway via nginx when running behind https://localhost:3443
const API_BASE_URL =
  typeof window !== 'undefined'
    ? `${window.location.origin}/api`
    : process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

export async function listHardenedImages(
  filters?: {
    os_name?: string;
    os_version?: string;
    cloud_provider?: string;
    hardening_level?: string;
    region?: string;
    status?: string;
  },
  page: number = 1,
  pageSize: number = 20
): Promise<HardenedImageListResponse> {
  const params = new URLSearchParams();
  
  if (filters?.os_name) params.append('os_name', filters.os_name);
  if (filters?.os_version) params.append('os_version', filters.os_version);
  if (filters?.cloud_provider) params.append('cloud_provider', filters.cloud_provider);
  if (filters?.hardening_level) params.append('hardening_level', filters.hardening_level);
  if (filters?.region) params.append('region', filters.region);
  if (filters?.status) params.append('status', filters.status);
  
  params.append('page', page.toString());
  params.append('page_size', pageSize.toString());

  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/hardened-images?${params}`
    : `${API_BASE_URL}/api/v1/hardened-images?${params}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hardened images: ${response.statusText}`);
  }

  return response.json();
}

export async function getHardenedImage(imageId: string): Promise<HardenedImage> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/hardened-images/${imageId}`
    : `${API_BASE_URL}/api/v1/hardened-images/${imageId}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch hardened image: ${response.statusText}`);
  }

  return response.json();
}

export async function getRecommendedImages(
  cloudProvider: string,
  region?: string
): Promise<HardenedImage[]> {
  const params = new URLSearchParams();
  params.append('cloud_provider', cloudProvider);
  if (region) params.append('region', region);

  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/hardened-images/recommendations/list?${params}`
    : `${API_BASE_URL}/api/v1/hardened-images/recommendations/list?${params}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: withSessionAuthorization({
      'Content-Type': 'application/json',
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch recommended images: ${response.statusText}`);
  }

  return response.json();
}
