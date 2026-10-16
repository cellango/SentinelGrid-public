/**
 * Privileged Access Page
 * Request, approve, and manage just-in-time privileged access
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  ShieldCheckIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  PlusIcon,
} from '@heroicons/react/24/outline';

// Use relative URLs to leverage Next.js rewrites
const API_BASE = '';

interface PrivilegedAccessRequest {
  id: string;
  tenant_id: string;
  requested_by: string;
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  reason: string;
  duration_hours: number;
  status: 'pending' | 'approved' | 'rejected' | 'expired' | 'revoked';
  requested_at: string;
  approved_at?: string;
  expires_at?: string;
}

async function getPrivilegedAccessRequests(
  status?: string
): Promise<PrivilegedAccessRequest[]> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);

  const response = await fetch(`/api/v1/privileged-access/requests?${params.toString()}`, {
    credentials: 'include',
  });
  return response.json();
}

async function requestPrivilegedAccess(
  data: {
    resource_type: string;
    resource_id: string;
    resource_name?: string;
    reason: string;
    duration_hours: number;
  }
): Promise<PrivilegedAccessRequest> {
  const response = await fetch(`/api/v1/privileged-access/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return response.json();
}

async function approveRequest(requestId: string, comments: string): Promise<void> {
  await fetch(`/api/v1/privileged-access/requests/${requestId}/approve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ comments }),
  });
}

async function rejectRequest(requestId: string, reason: string): Promise<void> {
  await fetch(`/api/v1/privileged-access/requests/${requestId}/reject`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ rejection_reason: reason }),
  });
}

export default function PrivilegedAccessPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [showRequestModal, setShowRequestModal] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { data: requests = [], isLoading } = useQuery({
    queryKey: ['privileged-access-requests', statusFilter],
    queryFn: () => getPrivilegedAccessRequests(statusFilter || undefined),
    enabled: isAuthenticated,
  });

  const requestMutation = useMutation({
    mutationFn: (data: Parameters<typeof requestPrivilegedAccess>[0]) =>
      requestPrivilegedAccess(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privileged-access-requests'] });
      setShowRequestModal(false);
    },
  });

  const approveMutation = useMutation({
    mutationFn: ({ requestId, comments }: { requestId: string; comments: string }) =>
      approveRequest(requestId, comments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privileged-access-requests'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ requestId, reason }: { requestId: string; reason: string }) =>
      rejectRequest(requestId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privileged-access-requests'] });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200';
      case 'rejected':
        return 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-amber-900/40 dark:text-amber-200';
      case 'expired':
      case 'revoked':
        return 'bg-bg-alt text-text-main dark:bg-slate-800/60 dark:text-slate-200';
      default:
        return 'bg-bg-alt text-text-main dark:bg-slate-800/60 dark:text-slate-200';
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-text-muted">Loading privileged access requests...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Privileged Access</h1>
          <p className="text-sm text-text-muted mt-1">
            Request and manage just-in-time (JIT) privileged access
          </p>
        </div>
        <button
          onClick={() => setShowRequestModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm shadow-blue-600/30"
        >
          <PlusIcon className="w-5 h-5" />
          Request Access
        </button>
      </div>

      {/* Filters */}
      <div className="mb-6">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500/60 bg-surface-card text-slate-900 dark:text-slate-100 shadow-sm dark:shadow-[0_1px_0_0_rgba(255,255,255,0.04)]"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="expired">Expired</option>
          <option value="revoked">Revoked</option>
        </select>
      </div>

      {/* Requests List */}
      {requests.length > 0 ? (
        <div className="space-y-4">
          {requests.map((request) => (
            <div
              key={request.id}
              className="bg-surface-card border border-surface-card-border rounded-lg p-6 shadow-sm dark:shadow-none"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <ShieldCheckIcon className="w-6 h-6 text-blue-600" />
                    <h3 className="font-semibold">
                      {request.resource_name || `${request.resource_type}:${request.resource_id}`}
                    </h3>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(request.status)} dark:bg-opacity-30`}
                    >
                      {request.status}
                    </span>
                  </div>
                  <p className="text-sm text-text-muted mb-3">{request.reason}</p>
                  <div className="flex items-center gap-4 text-xs text-text-muted">
                    <span>Requested: {new Date(request.requested_at).toLocaleString()}</span>
                    <span>Duration: {request.duration_hours} hour(s)</span>
                    {request.expires_at && (
                      <span>Expires: {new Date(request.expires_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {request.status === 'pending' && (
                    <>
                      <button
                        onClick={() => {
                          const comments = prompt('Approval comments (optional):');
                          if (comments !== null) {
                            approveMutation.mutate({ requestId: request.id, comments: comments || '' });
                          }
                        }}
                        disabled={approveMutation.isPending}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm shadow-green-600/30"
                      >
                        <CheckCircleIcon className="w-4 h-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => {
                          const reason = prompt('Rejection reason:');
                          if (reason && reason.length >= 5) {
                            rejectMutation.mutate({ requestId: request.id, reason });
                          }
                        }}
                        disabled={rejectMutation.isPending}
                        className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm shadow-red-600/30"
                      >
                        <XCircleIcon className="w-4 h-4" />
                        Reject
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg shadow-sm dark:shadow-none">
          <ShieldCheckIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">No privileged access requests</p>
        </div>
      )}

      {/* Request Modal */}
      {showRequestModal && (
        <PrivilegedAccessRequestModal
          onClose={() => setShowRequestModal(false)}
          onSubmit={(data) => requestMutation.mutate(data)}
          isLoading={requestMutation.isPending}
        />
      )}
    </div>
  );
}

// Privileged Access Request Modal
function PrivilegedAccessRequestModal({
  onClose,
  onSubmit,
  isLoading,
}: {
  onClose: () => void;
  onSubmit: (data: Parameters<typeof requestPrivilegedAccess>[0]) => void;
  isLoading: boolean;
}) {
  const [formData, setFormData] = useState({
    resource_type: 'role',
    resource_id: '',
    resource_name: '',
    reason: '',
    duration_hours: 1,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.reason.length < 10) {
      alert('Reason must be at least 10 characters');
      return;
    }
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-card rounded-lg p-6 max-w-md w-full mx-4 shadow-xl shadow-black/20 text-slate-900 dark:text-slate-100">
        <h2 className="text-xl font-bold mb-4">Request Privileged Access</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Resource Type *
            </label>
            <select
              value={formData.resource_type}
              onChange={(e) => setFormData({ ...formData, resource_type: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500/60 bg-surface-card text-slate-900 dark:text-slate-100"
            >
              <option value="role">Role</option>
              <option value="permission">Permission</option>
              <option value="resource">Resource</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Resource ID *
            </label>
            <input
              type="text"
              required
              value={formData.resource_id}
              onChange={(e) => setFormData({ ...formData, resource_id: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500/60 bg-surface-card text-slate-900 dark:text-slate-100"
              placeholder="e.g., ADMIN_ROLE"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Resource Name (Optional)
            </label>
            <input
              type="text"
              value={formData.resource_name}
              onChange={(e) => setFormData({ ...formData, resource_name: e.target.value })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500/60 bg-surface-card text-slate-900 dark:text-slate-100"
              placeholder="e.g., Administrator Role"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Reason * (min 10 characters)
            </label>
            <textarea
              required
              minLength={10}
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500/60 bg-surface-card text-slate-900 dark:text-slate-100"
              placeholder="Explain why you need this privileged access..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted mb-1">
              Duration (hours) *
            </label>
            <input
              type="number"
              required
              min={1}
              max={24}
              value={formData.duration_hours}
              onChange={(e) => setFormData({ ...formData, duration_hours: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500/60 bg-surface-card text-slate-900 dark:text-slate-100"
            />
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-border text-text-muted rounded-lg hover:bg-surface-hover transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || formData.reason.length < 10}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 shadow-sm shadow-blue-600/30"
            >
              {isLoading ? 'Submitting...' : 'Submit Request'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
