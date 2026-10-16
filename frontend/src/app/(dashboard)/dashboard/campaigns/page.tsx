/**
 * Campaigns Page
 * Main page for viewing and managing audit campaigns
 */

'use client';

import { CampaignList } from '@/components/campaigns/CampaignList';
import Link from 'next/link';

export default function CampaignsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Audit Campaigns</h1>
          <p className="mt-1 text-sm text-text-muted">
            Manage access review campaigns and certifications
          </p>
        </div>
        <Link
          href="/dashboard/campaigns/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create Campaign
        </Link>
      </div>

      {/* Campaigns List */}
      <CampaignList />
    </div>
  );
}

