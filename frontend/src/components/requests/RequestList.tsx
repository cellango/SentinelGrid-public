/**
 * Request List Component
 * Lists access requests with filters
 */

'use client';

import { useState } from 'react';
import { useAccessRequests } from '@/lib/hooks/useAccessRequests';
import { RequestCard } from './RequestCard';

interface RequestListProps {
  showUserRequestsOnly?: boolean;
  userId?: string;
  tenantId?: string;
  resourceId?: string;
}

export function RequestList({ showUserRequestsOnly, userId, resourceId, tenantId }: RequestListProps) {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const { data: requests, isLoading, error } = useAccessRequests({
    tenant_id: tenantId,
    status: statusFilter,
    requested_by: showUserRequestsOnly && userId ? userId : undefined,
  });

  const filtered = (() => {
    if (!resourceId) return requests || [];
    return (requests || []).filter((r) => r.resource_id?.toLowerCase().includes(resourceId.toLowerCase()));
  })();

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
        <p className="text-red-800">Error loading access requests. Please try again.</p>
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
          <option value="approved">Approved</option>
          <option value="denied">Denied</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {resourceId && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          Filtering requests related to <span className="font-semibold">{resourceId}</span>
        </div>
      )}

      {/* Requests Grid */}
      {filtered && filtered.length > 0 ? (
        <div className="space-y-4">
          {filtered.map((request) => (
            <RequestCard key={request.id} request={request} />
          ))}
        </div>
      ) : (
        <div className="bg-surface-hover border border-surface-card-border rounded-lg p-8 text-center">
          <p className="text-text-muted">No access requests found.</p>
          <p className="text-sm text-text-muted mt-2">
            {statusFilter ? 'Try adjusting your filters.' : 'Create your first access request to get started.'}
          </p>
        </div>
      )}
    </div>
  );
}
