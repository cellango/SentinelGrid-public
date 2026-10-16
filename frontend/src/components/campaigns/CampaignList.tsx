/**
 * Campaign List Component
 * Displays a list of campaigns with filtering
 */

'use client';

import { useCampaigns } from '@/lib/hooks/useCampaigns';
import { CampaignCard } from './CampaignCard';
import { useState } from 'react';

export function CampaignList() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const { data: campaigns, isLoading, error } = useCampaigns({ status: statusFilter });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error loading campaigns. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex items-center gap-4">
        <label className="text-sm font-medium text-text-muted">Filter by status:</label>
        <select
          value={statusFilter || ''}
          onChange={(e) => setStatusFilter(e.target.value || undefined)}
          className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Campaigns Grid */}
      {campaigns && campaigns.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {campaigns.map((campaign) => (
            <CampaignCard key={campaign.id} campaign={campaign} />
          ))}
        </div>
      ) : (
        <div className="bg-surface-hover border border-surface-card-border rounded-lg p-8 text-center">
          <p className="text-text-muted">No campaigns found.</p>
          <p className="text-sm text-text-muted mt-2">Create your first campaign to get started.</p>
        </div>
      )}
    </div>
  );
}

