/**
 * Requests Page
 * Main page for access request management
 */

'use client';

import { useEffect, useMemo, useState } from 'react';
import { RequestList } from '@/components/requests/RequestList';
import { RequestForm } from '@/components/requests/RequestForm';
import { useSearchParams } from 'next/navigation';
import { useAuth } from '@/lib/providers/AuthProvider';

export default function RequestsPage() {
  const { tenantId, user } = useAuth();
  const searchParams = useSearchParams();
  const [showForm, setShowForm] = useState(searchParams.get('new') === '1');
  const resourceId = searchParams.get('asset_id') || searchParams.get('resource_id') || undefined;
  const vulnId = searchParams.get('vuln_id') || undefined;
  const combinedResource = vulnId ? `${resourceId || ''} ${vulnId}`.trim() || undefined : resourceId;
  const initialRequestValues = useMemo(
    () => ({
      resource_type: searchParams.get('resource_type') || '',
      resource_id: searchParams.get('resource_id') || '',
      action: searchParams.get('action') || '',
      justification: searchParams.get('justification') || '',
      expires_at: searchParams.get('expires_at') || undefined,
    }),
    [searchParams]
  );

  useEffect(() => {
    if (searchParams.get('new') === '1') {
      setShowForm(true);
    }
  }, [searchParams]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Access Requests</h1>
          <p className="mt-1 text-sm text-text-muted">
            Request access to resources or review pending requests
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {showForm ? 'Cancel' : 'New Request'}
        </button>
      </div>

      {/* Request Form */}
      {showForm && tenantId && (
        <RequestForm
          tenantId={tenantId}
          onSuccess={() => setShowForm(false)}
          initialValues={initialRequestValues}
        />
      )}
      {showForm && !tenantId && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg p-4">
          Unable to determine tenant. Please sign in again to submit a request.
        </div>
      )}

      {/* Requests List */}
      {!showForm && (
        <RequestList
          tenantId={tenantId || undefined}
          resourceId={combinedResource}
          showUserRequestsOnly={!user?.roles?.some((role) => ['TENANT_ADMIN', 'SOC_MANAGER', 'PLATFORM_ADMIN'].includes(role))}
          userId={user?.id}
        />
      )}
    </div>
  );
}
