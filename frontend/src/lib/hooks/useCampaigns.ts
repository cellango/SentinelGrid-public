/**
 * React Query hooks for Campaign management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignsApi, type Campaign, type CampaignCreate, type CampaignUpdate, type CampaignProgress } from '../api/governance';
import { toast } from 'react-hot-toast';

// Query keys
export const campaignKeys = {
  all: ['campaigns'] as const,
  lists: () => [...campaignKeys.all, 'list'] as const,
  list: (filters?: Record<string, any>) => [...campaignKeys.lists(), filters] as const,
  details: () => [...campaignKeys.all, 'detail'] as const,
  detail: (id: string) => [...campaignKeys.details(), id] as const,
  progress: (id: string) => [...campaignKeys.detail(id), 'progress'] as const,
};

/**
 * Hook to fetch campaigns list
 */
export function useCampaigns(filters?: {
  tenant_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: campaignKeys.list(filters),
    queryFn: () => campaignsApi.list(filters),
  });
}

/**
 * Hook to fetch single campaign
 */
export function useCampaign(campaignId: string) {
  return useQuery({
    queryKey: campaignKeys.detail(campaignId),
    queryFn: () => campaignsApi.get(campaignId),
    enabled: !!campaignId,
  });
}

/**
 * Hook to fetch campaign progress
 */
export function useCampaignProgress(campaignId: string) {
  return useQuery({
    queryKey: campaignKeys.progress(campaignId),
    queryFn: () => campaignsApi.getProgress(campaignId),
    enabled: !!campaignId,
    refetchInterval: 30000, // Refetch every 30 seconds for active campaigns
  });
}

/**
 * Hook to create a campaign
 */
export function useCreateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaign: CampaignCreate) => campaignsApi.create(campaign),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: campaignKeys.lists() });
      toast.success('Campaign created successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create campaign');
    },
  });
}

/**
 * Hook to update a campaign
 */
export function useUpdateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: CampaignUpdate }) =>
      campaignsApi.update(id, updates),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: campaignKeys.detail(variables.id) });
      queryClient.invalidateQueries({ queryKey: campaignKeys.lists() });
      toast.success('Campaign updated successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to update campaign');
    },
  });
}

/**
 * Hook to start a campaign
 */
export function useStartCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (campaignId: string) => campaignsApi.start(campaignId),
    onSuccess: (_, campaignId) => {
      queryClient.invalidateQueries({ queryKey: campaignKeys.detail(campaignId) });
      queryClient.invalidateQueries({ queryKey: campaignKeys.lists() });
      toast.success('Campaign started successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start campaign');
    },
  });
}

/**
 * Hook to complete a campaign
 */
export function useCompleteCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ campaignId, autoRevoke }: { campaignId: string; autoRevoke?: boolean }) =>
      campaignsApi.complete(campaignId, autoRevoke),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: campaignKeys.detail(variables.campaignId) });
      queryClient.invalidateQueries({ queryKey: campaignKeys.lists() });
      toast.success('Campaign completed successfully');
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to complete campaign');
    },
  });
}

