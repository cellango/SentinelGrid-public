/**
 * Hook for fetching security snapshot data
 */

import { useQuery } from '@tanstack/react-query';
import { getSecuritySnapshot, SecuritySnapshot } from '@/lib/api/orchestrator';
import { clearAuthMetadata } from '@/lib/auth/session';
import axios from 'axios';

export function useSecuritySnapshot(tenantId: string | null) {
  return useQuery<SecuritySnapshot, any>({
    queryKey: ['security-snapshot', tenantId],
    queryFn: async () => {
      if (!tenantId) {
        throw new Error('Tenant ID is required');
      }
      try {
        return await getSecuritySnapshot(tenantId);
      } catch (error: any) {
        if (typeof window !== 'undefined' && axios.isAxiosError(error)) {
          const status = error.response?.status;
          const detail = (error.response?.data as any)?.detail || '';
          const lowerDetail = typeof detail === 'string' ? detail.toLowerCase() : '';
          if (status === 401 || status === 403 || lowerDetail.includes('token')) {
            clearAuthMetadata();
            sessionStorage.setItem('auth_message', 'Your session expired. Please sign in again.');
            window.location.href = '/login';
          }
        }
        throw error;
      }
    },
    enabled: !!tenantId,
    refetchInterval: 5 * 60 * 1000, // Auto-refresh every 5 minutes
    staleTime: 2 * 60 * 1000, // Consider data stale after 2 minutes
    retry: (failureCount, error: any) => {
      // Do not retry on auth failures
      if (axios.isAxiosError(error)) {
        const status = error.response?.status;
        if (status === 401 || status === 403) return false;
      }
      return failureCount < 2;
    },
  });
}
