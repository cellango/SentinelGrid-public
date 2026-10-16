/**
 * Campaign Card Component
 * Displays a campaign summary card
 */

'use client';

import { Campaign } from '@/lib/api/governance';
import { format } from 'date-fns';
import Link from 'next/link';

interface CampaignCardProps {
  campaign: Campaign;
}

export function CampaignCard({ campaign }: CampaignCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-bg-alt text-text-main';
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'cancelled':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-bg-alt text-text-main';
    }
  };

  const getReviewerTypeLabel = (type: string) => {
    switch (type) {
      case 'self':
        return 'Self';
      case 'manager':
        return 'Manager';
      case 'admin':
        return 'Admin';
      default:
        return type;
    }
  };

  return (
    <Link href={`/dashboard/campaigns/${campaign.id}`}>
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 hover:shadow-md transition-shadow cursor-pointer">
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-main">{campaign.name}</h3>
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
              campaign.status
            )}`}
          >
            {campaign.status.replace('_', ' ').toUpperCase()}
          </span>
        </div>

        {campaign.description && (
          <p className="text-sm text-text-muted mb-4 line-clamp-2">{campaign.description}</p>
        )}

        <div className="space-y-2 text-sm text-text-muted">
          <div className="flex items-center justify-between">
            <span className="font-medium">Start Date:</span>
            <span>{format(new Date(campaign.start_date), 'MMM d, yyyy')}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-medium">End Date:</span>
            <span>{format(new Date(campaign.end_date), 'MMM d, yyyy')}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-medium">Reviewer Type:</span>
            <span>{getReviewerTypeLabel(campaign.reviewer_type)}</span>
          </div>
          {campaign.auto_revoke_days && (
            <div className="flex items-center justify-between">
              <span className="font-medium">Auto-Revoke:</span>
              <span>{campaign.auto_revoke_days} days</span>
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-surface-card-border">
          <div className="text-xs text-text-muted">
            Created {format(new Date(campaign.created_at), 'MMM d, yyyy')}
          </div>
        </div>
      </div>
    </Link>
  );
}

