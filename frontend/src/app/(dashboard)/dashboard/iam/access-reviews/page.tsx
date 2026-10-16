/**
 * Access Reviews Page
 * Comprehensive landing page for access review workflows
 */

'use client';

import { useCampaigns } from '@/lib/hooks/useCampaigns';
import { usePendingCertifications } from '@/lib/hooks/useCertifications';
import { useCertifications } from '@/lib/hooks/useCertifications';
import { CampaignCard } from '@/components/campaigns/CampaignCard';
import { CertificationCard } from '@/components/certifications/CertificationCard';
import Link from 'next/link';
import {
  ClipboardDocumentCheckIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PlusIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';

export default function AccessReviewsPage() {
  // Fetch campaigns
  const { data: allCampaigns, isLoading: loadingCampaigns } = useCampaigns();
  
  // Fetch pending certifications
  const { data: pendingCerts, isLoading: loadingPendingCerts } = usePendingCertifications({ limit: 10 });
  
  // Fetch all certifications for statistics
  const { data: allCertifications } = useCertifications({ limit: 1000 });

  // Calculate statistics
  const activeCampaigns = allCampaigns?.filter(c => c.status === 'in_progress') || [];
  const pendingCampaigns = allCampaigns?.filter(c => c.status === 'pending') || [];
  const completedCampaigns = allCampaigns?.filter(c => c.status === 'completed') || [];
  
  const pendingCertCount = pendingCerts?.length || 0;
  const totalCertCount = allCertifications?.length || 0;
  const approvedCertCount = allCertifications?.filter(c => c.review_status === 'approved' || c.review_status === 'retained').length || 0;
  const revokedCertCount = allCertifications?.filter(c => c.review_status === 'revoked').length || 0;

  // Get current quarter for completed reviews
  const now = new Date();
  const currentQuarter = Math.floor(now.getMonth() / 3);
  const quarterStart = new Date(now.getFullYear(), currentQuarter * 3, 1);
  const completedThisQuarter = completedCampaigns.filter(c => {
    const completedDate = new Date(c.updated_at);
    return completedDate >= quarterStart;
  }).length;

  // Get upcoming deadlines (campaigns ending in next 7 days)
  const sevenDaysFromNow = new Date();
  sevenDaysFromNow.setDate(sevenDaysFromNow.getDate() + 7);
  const upcomingDeadlines = activeCampaigns.filter(c => {
    const endDate = new Date(c.end_date);
    return endDate <= sevenDaysFromNow && endDate >= now;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Access Reviews</h1>
          <p className="text-sm text-text-muted mt-1">
            Manage access review campaigns and certifications
          </p>
        </div>
        <Link
          href="/dashboard/campaigns/new"
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          Create Campaign
        </Link>
      </div>

      {/* Overview Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Campaigns */}
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-text-muted">Active Campaigns</h3>
            <ClipboardDocumentCheckIcon className="w-8 h-8 text-blue-600" />
          </div>
          <p className="text-3xl font-bold text-text-main">
            {loadingCampaigns ? '...' : activeCampaigns.length}
          </p>
          <p className="text-xs text-text-muted mt-1">In progress</p>
        </div>

        {/* Pending Certifications */}
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-text-muted">Pending Certifications</h3>
            <ClockIcon className="w-8 h-8 text-yellow-600" />
          </div>
          <p className="text-3xl font-bold text-text-main">
            {loadingPendingCerts ? '...' : pendingCertCount}
          </p>
          <p className="text-xs text-text-muted mt-1">Awaiting review</p>
        </div>

        {/* Completed This Quarter */}
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-text-muted">Completed This Quarter</h3>
            <CheckCircleIcon className="w-8 h-8 text-green-600" />
          </div>
          <p className="text-3xl font-bold text-text-main">
            {loadingCampaigns ? '...' : completedThisQuarter}
          </p>
          <p className="text-xs text-text-muted mt-1">Q{currentQuarter + 1} {now.getFullYear()}</p>
        </div>

        {/* Upcoming Deadlines */}
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-text-muted">Upcoming Deadlines</h3>
            <ExclamationTriangleIcon className="w-8 h-8 text-orange-600" />
          </div>
          <p className="text-3xl font-bold text-text-main">
            {loadingCampaigns ? '...' : upcomingDeadlines.length}
          </p>
          <p className="text-xs text-text-muted mt-1">Next 7 days</p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          href="/dashboard/campaigns/new"
          className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-text-main">Create New Campaign</h3>
            <PlusIcon className="w-6 h-6 text-blue-600" />
          </div>
          <p className="text-sm text-text-muted mb-4">
            Start a new access review campaign for quarterly or on-demand reviews
          </p>
          <span className="text-blue-600 text-sm font-medium flex items-center gap-1">
            Get Started <ArrowRightIcon className="w-4 h-4" />
          </span>
        </Link>

        <Link
          href="/dashboard/certifications"
          className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-text-main">View My Certifications</h3>
            <ClipboardDocumentCheckIcon className="w-6 h-6 text-indigo-600" />
          </div>
          <p className="text-sm text-text-muted mb-4">
            Review and certify your pending entitlements
          </p>
          <span className="text-indigo-600 text-sm font-medium flex items-center gap-1">
            Review Now <ArrowRightIcon className="w-4 h-4" />
          </span>
        </Link>

        <Link
          href="/dashboard/campaigns"
          className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-lg font-semibold text-text-main">View All Campaigns</h3>
            <ClipboardDocumentCheckIcon className="w-6 h-6 text-purple-600" />
          </div>
          <p className="text-sm text-text-muted mb-4">
            Manage all access review campaigns and view history
          </p>
          <span className="text-purple-600 text-sm font-medium flex items-center gap-1">
            View All <ArrowRightIcon className="w-4 h-4" />
          </span>
        </Link>
      </div>

      {/* Active Campaigns */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-text-main">Active Campaigns</h2>
            <p className="text-sm text-text-muted mt-1">
              Campaigns currently in progress
            </p>
          </div>
          {activeCampaigns.length > 0 && (
            <Link
              href="/dashboard/campaigns"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View All
            </Link>
          )}
        </div>

        {loadingCampaigns ? (
          <div className="flex items-center justify-center py-12 bg-surface-card rounded-lg border border-surface-card-border">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : activeCampaigns.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {activeCampaigns.slice(0, 6).map((campaign) => (
              <CampaignCard key={campaign.id} campaign={campaign} />
            ))}
          </div>
        ) : (
          <div className="bg-surface-card rounded-lg border border-surface-card-border p-8 text-center">
            <ClipboardDocumentCheckIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <p className="text-text-muted mb-2">No active campaigns</p>
            <p className="text-sm text-text-muted mb-4">
              Create your first campaign to start reviewing access
            </p>
            <Link
              href="/dashboard/campaigns/new"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <PlusIcon className="w-4 h-4" />
              Create Campaign
            </Link>
          </div>
        )}
      </div>

      {/* Pending Certifications Preview */}
      {pendingCertCount > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold text-text-main">Pending Certifications</h2>
              <p className="text-sm text-text-muted mt-1">
                {pendingCertCount} certification{pendingCertCount !== 1 ? 's' : ''} awaiting your review
              </p>
            </div>
            <Link
              href="/dashboard/certifications"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View All
            </Link>
          </div>

          {loadingPendingCerts ? (
            <div className="flex items-center justify-center py-12 bg-surface-card rounded-lg border border-surface-card-border">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingCerts?.slice(0, 5).map((certification) => (
                <CertificationCard
                  key={certification.id}
                  certification={certification}
                />
              ))}
              {pendingCertCount > 5 && (
                <div className="text-center pt-4">
                  <Link
                    href="/dashboard/certifications"
                    className="text-blue-600 hover:text-blue-700 font-medium text-sm"
                  >
                    View {pendingCertCount - 5} more certification{pendingCertCount - 5 !== 1 ? 's' : ''} →
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Recent Activity & Statistics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Review Statistics */}
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <h3 className="text-lg font-semibold text-text-main mb-4">Review Statistics</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Total Certifications</span>
              <span className="text-lg font-semibold text-text-main">{totalCertCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Approved/Retained</span>
              <span className="text-lg font-semibold text-green-600">{approvedCertCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Revoked</span>
              <span className="text-lg font-semibold text-red-600">{revokedCertCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-muted">Pending</span>
              <span className="text-lg font-semibold text-yellow-600">{pendingCertCount}</span>
            </div>
          </div>
        </div>

        {/* Upcoming Deadlines */}
        {upcomingDeadlines.length > 0 && (
          <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
            <h3 className="text-lg font-semibold text-text-main mb-4">Upcoming Deadlines</h3>
            <div className="space-y-3">
              {upcomingDeadlines.slice(0, 5).map((campaign) => (
                <Link
                  key={campaign.id}
                  href={`/dashboard/campaigns/${campaign.id}`}
                  className="block p-3 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-text-main">{campaign.name}</span>
                    <span className="text-xs text-orange-600 font-medium">
                      {format(new Date(campaign.end_date), 'MMM d')}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

