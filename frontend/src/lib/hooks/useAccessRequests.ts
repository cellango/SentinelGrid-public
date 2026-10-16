/**
 * React Query hooks for Access Request management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  accessRequestsApi,
  type AccessRequest,
  type AccessRequestCreate,
  type AccessRequestReview,
  type AccessRequestHistory,
} from '../api/accessRequests';
import { toast } from 'react-hot-toast';

// Query keys
export const accessRequestKeys = {
  all: ['access-requests'] as const,
  lists: () => [...accessRequestKeys.all, 'list'] as const,
  list: (filters?: Record<string, any>) => [...accessRequestKeys.lists(), filters] as const,
  details: () => [...accessRequestKeys.all, 'detail'] as const,
  detail: (id: string) => [...accessRequestKeys.details(), id] as const,
  history: (id: string) => [...accessRequestKeys.detail(id), 'history'] as const,
};

/**
 * Hook to fetch access requests list
 */
export function useAccessRequests(filters?: {
  tenant_id?: string;
  status?: string;
  requested_by?: string;
  reviewer_id?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: accessRequestKeys.list(filters),
    queryFn: () => accessRequestsApi.list(filters),
    enabled: !!filters?.tenant_id || filters?.tenant_id === undefined,
  });
}

/**
 * Hook to fetch single access request
 */
export function useAccessRequest(requestId: string) {
  return useQuery({
    queryKey: accessRequestKeys.detail(requestId),
    queryFn: () => accessRequestsApi.get(requestId),
    enabled: !!requestId,
  });
}

/**
 * Hook to fetch access request history
 */
export function useAccessRequestHistory(requestId: string) {
  return useQuery({
    queryKey: accessRequestKeys.history(requestId),
    queryFn: () => accessRequestsApi.getHistory(requestId),
    enabled: !!requestId,
  });
}

/**
 * Hook to create access request
 */
export function useCreateAccessRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: AccessRequestCreate) => accessRequestsApi.create(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: accessRequestKeys.lists() });
      toast.success('Access request created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create access request');
    },
  });
}

/**
 * Hook to review access request
 */
export function useReviewAccessRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ requestId, review }: { requestId: string; review: AccessRequestReview }) =>
      accessRequestsApi.review(requestId, review),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: accessRequestKeys.detail(variables.requestId) });
      queryClient.invalidateQueries({ queryKey: accessRequestKeys.lists() });
      queryClient.invalidateQueries({ queryKey: accessRequestKeys.history(variables.requestId) });
      toast.success(`Access request ${variables.review.decision === 'approve' ? 'approved' : 'denied'}`);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to review access request');
    },
  });
}

/**
 * Hook to cancel access request
 */
export function useCancelAccessRequest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (requestId: string) => accessRequestsApi.cancel(requestId),
    onSuccess: (_, requestId) => {
      queryClient.invalidateQueries({ queryKey: accessRequestKeys.detail(requestId) });
      queryClient.invalidateQueries({ queryKey: accessRequestKeys.lists() });
      toast.success('Access request cancelled');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to cancel access request');
    },
  });
}
