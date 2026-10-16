/**
 * New Campaign Page
 * Create a new audit campaign using the wizard
 */

'use client';

import { CampaignWizard } from '@/components/campaigns/CampaignWizard';
import Link from 'next/link';
import { useTenant } from '@/lib/hooks/useTenant';

export default function NewCampaignPage() {
  const { tenant, loading } = useTenant();

  if (loading) {
    return <div className="p-6 text-sm text-text-muted">Loading tenant context...</div>;
  }

  if (!tenant?.id) {
    return <div className="p-6 text-sm text-red-600">Tenant context is unavailable. Sign in again and retry.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/dashboard/campaigns" className="text-sm text-blue-600 hover:text-blue-700 mb-2 inline-block">
            ← Back to Campaigns
          </Link>
          <h1 className="text-2xl font-bold text-text-main">Create Audit Campaign</h1>
          <p className="mt-1 text-sm text-text-muted">Set up a new access review campaign</p>
        </div>
      </div>

      {/* Wizard */}
      <CampaignWizard tenantId={tenant.id} />
    </div>
  );
}
