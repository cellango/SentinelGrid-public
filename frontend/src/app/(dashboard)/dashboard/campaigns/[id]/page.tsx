/**
 * Campaign Detail Page
 * View campaign details, progress, and certifications
 */

'use client';

import { useParams, useRouter } from 'next/navigation';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { useCampaign, useStartCampaign, useCompleteCampaign } from '@/lib/hooks/useCampaigns';
import { CampaignProgress } from '@/components/campaigns/CampaignProgress';
import { CertificationsList } from '@/components/campaigns/CertificationsList';
import { format } from 'date-fns';
import Link from 'next/link';
import { useState } from 'react';

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;

  const { data: campaign, isLoading, error } = useCampaign(campaignId);
  const startCampaign = useStartCampaign();
  const completeCampaign = useCompleteCampaign();

  const [showCompleteConfirm, setShowCompleteConfirm] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-800">Campaign not found or error loading campaign.</p>
        <Link href="/dashboard/campaigns" className="text-blue-600 hover:text-blue-700 text-sm mt-2 inline-block">
          ← Back to Campaigns
        </Link>
      </div>
    );
  }

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

  const handleStart = async () => {
    try {
      await startCampaign.mutateAsync(campaignId);
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  const handleComplete = async (autoRevoke: boolean) => {
    try {
      await completeCampaign.mutateAsync({ campaignId, autoRevoke });
      setShowCompleteConfirm(false);
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  return (
    <div className="space-y-6">
      <Breadcrumbs />
      {/* Header */}
      <div>
        <Link href="/dashboard/campaigns" className="text-sm text-blue-600 hover:text-blue-700 mb-2 inline-block">
          ← Back to Campaigns
        </Link>
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-text-main">{campaign.name}</h1>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(campaign.status)}`}
              >
                {campaign.status.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            {campaign.description && (
              <p className="mt-2 text-sm text-text-muted">{campaign.description}</p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            {campaign.status === 'pending' && (
              <button
                onClick={handleStart}
                disabled={startCampaign.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {startCampaign.isPending ? 'Starting...' : 'Start Campaign'}
              </button>
            )}
            {campaign.status === 'in_progress' && (
              <button
                onClick={() => setShowCompleteConfirm(true)}
                className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700"
              >
                Complete Campaign
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Campaign Info */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
        <h2 className="text-lg font-semibold text-text-main mb-4">Campaign Details</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <span className="text-sm font-medium text-text-muted">Start Date</span>
            <p className="text-sm text-text-main mt-1">
              {format(new Date(campaign.start_date), 'PPP')}
            </p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">End Date</span>
            <p className="text-sm text-text-main mt-1">
              {format(new Date(campaign.end_date), 'PPP')}
            </p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">Reviewer Type</span>
            <p className="text-sm text-text-main mt-1 capitalize">{campaign.reviewer_type}</p>
          </div>
          {campaign.auto_revoke_days && (
            <div>
              <span className="text-sm font-medium text-text-muted">Auto-Revoke</span>
              <p className="text-sm text-text-main mt-1">
                {campaign.auto_revoke_days} days after end date
              </p>
            </div>
          )}
          <div>
            <span className="text-sm font-medium text-text-muted">Created</span>
            <p className="text-sm text-text-main mt-1">
              {format(new Date(campaign.created_at), 'PPP')}
            </p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">Last Updated</span>
            <p className="text-sm text-text-main mt-1">
              {format(new Date(campaign.updated_at), 'PPP')}
            </p>
          </div>
        </div>
      </div>

      {/* Progress (only show if campaign is started) */}
      {campaign.status === 'in_progress' || campaign.status === 'completed' ? (
        <CampaignProgress campaignId={campaignId} />
      ) : null}

      {/* Certifications List (only show if campaign is started) */}
      {campaign.status === 'in_progress' || campaign.status === 'completed' ? (
        <CertificationsList campaignId={campaignId} />
      ) : null}

      {/* Complete Confirmation Modal */}
      {showCompleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-text-main mb-4">Complete Campaign</h3>
            <p className="text-sm text-text-muted mb-6">
              Complete this campaign and optionally revoke entitlements that were not certified.
            </p>
            <div className="space-y-3 mb-6">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  id="auto_revoke"
                  defaultChecked={true}
                  className="rounded border-border text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-text-muted">
                  Auto-revoke uncertified entitlements
                </span>
              </label>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowCompleteConfirm(false)}
                className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const autoRevoke = (
                    document.getElementById('auto_revoke') as HTMLInputElement
                  )?.checked;
                  handleComplete(autoRevoke);
                }}
                disabled={completeCampaign.isPending}
                className="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {completeCampaign.isPending ? 'Completing...' : 'Complete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
