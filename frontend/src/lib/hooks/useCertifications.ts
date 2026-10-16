/**
 * React Query hooks for Certification management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { certificationsApi, type Certification, type CertificationDecision, type BulkCertificationRequest } from '../api/governance';
import { toast } from 'react-hot-toast';

// Query keys
export const certificationKeys = {
  all: ['certifications'] as const,
  lists: () => [...certificationKeys.all, 'list'] as const,
  list: (filters?: Record<string, any>) => [...certificationKeys.lists(), filters] as const,
  pending: (filters?: Record<string, any>) => [...certificationKeys.all, 'pending', filters] as const,
  details: () => [...certificationKeys.all, 'detail'] as const,
  detail: (id: string) => [...certificationKeys.details(), id] as const,
};

/**
 * Hook to fetch pending certifications
 */
export function usePendingCertifications(filters?: {
  user_id?: string;
  campaign_id?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: certificationKeys.pending(filters),
    queryFn: () => certificationsApi.getPending(filters),
  });
}

/**
 * Hook to fetch certifications list
 */
export function useCertifications(filters?: {
  campaign_id?: string;
  user_id?: string;
  review_status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: certificationKeys.list(filters),
    queryFn: () => certificationsApi.list(filters),
  });
}

/**
 * Hook to submit certification decision
 */
export function useCertifyEntitlement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ certificationId, decision }: { certificationId: string; decision: CertificationDecision }) =>
      certificationsApi.certify(certificationId, decision),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: certificationKeys.all });
      toast.success('Certification submitted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to submit certification');
    },
  });
}

/**
 * Hook for bulk certification
 */
export function useBulkCertify() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BulkCertificationRequest) => certificationsApi.bulkCertify(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: certificationKeys.all });
      toast.success('Certifications submitted successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to submit certifications');
    },
  });
}

