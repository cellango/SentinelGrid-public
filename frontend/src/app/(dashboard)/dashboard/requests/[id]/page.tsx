/**
 * Request Detail Page
 * View access request details and review
 */

'use client';

import { useParams } from 'next/navigation';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import { useAccessRequest } from '@/lib/hooks/useAccessRequests';
import { RequestDetail } from '@/components/requests/RequestDetail';
import { RequestTimeline } from '@/components/requests/RequestTimeline';
import Link from 'next/link';
import { useAuth } from '@/lib/providers/AuthProvider';

export default function RequestDetailPage() {
  const params = useParams();
  const requestId = params.id as string;
  const { user } = useAuth();

  const { data: request, isLoading, error, refetch } = useAccessRequest(requestId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !request) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <p className="text-red-800">Access request not found or error loading request.</p>
        <Link href="/dashboard/requests" className="text-blue-600 hover:text-blue-700 text-sm mt-2 inline-block">
          ← Back to Requests
        </Link>
      </div>
    );
  }

  const isRequestAdmin = Boolean(
    user?.roles?.some((role) => ['TENANT_ADMIN', 'SOC_MANAGER', 'PLATFORM_ADMIN'].includes(role))
  );
  const canReview = request.status === 'pending' && isRequestAdmin;
  const canCancel = request.status === 'pending' && request.requested_by === user?.id;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Breadcrumbs />
        <Link href="/dashboard/requests" className="text-sm text-blue-600 hover:text-blue-700 mb-2 inline-block">
          ← Back to Requests
        </Link>
      </div>

      {/* Request Detail */}
      <RequestDetail
        request={request}
        canReview={canReview}
        canCancel={canCancel}
        onUpdated={() => refetch()}
      />

      {/* Timeline */}
      <RequestTimeline requestId={requestId} />
    </div>
  );
}
