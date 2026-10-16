/**
 * Request Detail Component
 * Approval workflow interface for managers
 */

'use client';

import { AccessRequest } from '@/lib/api/accessRequests';
import { useReviewAccessRequest, useCancelAccessRequest } from '@/lib/hooks/useAccessRequests';
import { format } from 'date-fns';
import { useState } from 'react';

interface RequestDetailProps {
  request: AccessRequest;
  canReview?: boolean; // Whether current user can review this request
  canCancel?: boolean; // Whether current user can cancel this request
  onUpdated?: () => void;
}

export function RequestDetail({ request, canReview = false, canCancel = false, onUpdated }: RequestDetailProps) {
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [decision, setDecision] = useState<'approve' | 'deny' | null>(null);
  const [comments, setComments] = useState('');
  const reviewMutation = useReviewAccessRequest();
  const cancelMutation = useCancelAccessRequest();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'denied':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-bg-alt text-text-main';
      default:
        return 'bg-bg-alt text-text-main';
    }
  };

  const handleReview = async () => {
    if (!decision) return;

    try {
      await reviewMutation.mutateAsync({
        requestId: request.id,
        review: {
          decision,
          comments: comments.trim() || undefined,
        },
      });
      setShowReviewModal(false);
      setDecision(null);
      setComments('');
      onUpdated?.();
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel this request?')) return;

    try {
      await cancelMutation.mutateAsync(request.id);
      onUpdated?.();
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  return (
    <>
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-text-main mb-2">
              {request.resource_type}:{request.resource_id === '*' ? '*' : request.resource_id}
              {' '}
              <span className="text-blue-600">{request.action}</span>
            </h2>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}>
              {request.status.toUpperCase()}
            </span>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            {canReview && request.status === 'pending' && (
              <button
                onClick={() => setShowReviewModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
              >
                Review Request
              </button>
            )}
            {canCancel && request.status === 'pending' && (
              <button
                onClick={handleCancel}
                disabled={cancelMutation.isPending}
                className="px-4 py-2 border border-border text-text-muted rounded-md text-sm font-medium hover:bg-surface-hover disabled:opacity-50"
              >
                {cancelMutation.isPending ? 'Cancelling...' : 'Cancel'}
              </button>
            )}
          </div>
        </div>

        {/* Request Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <span className="text-sm font-medium text-text-muted">Requested By</span>
            <p className="text-sm text-text-main mt-1">{request.requested_by.substring(0, 8)}...</p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">Requested For</span>
            <p className="text-sm text-text-main mt-1">{request.requested_for.substring(0, 8)}...</p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">Resource Type</span>
            <p className="text-sm text-text-main mt-1">{request.resource_type}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">Action</span>
            <p className="text-sm text-text-main mt-1">{request.action}</p>
          </div>
          <div>
            <span className="text-sm font-medium text-text-muted">Created</span>
            <p className="text-sm text-text-main mt-1">{format(new Date(request.created_at), 'PPP')}</p>
          </div>
          {request.expires_at && (
            <div>
              <span className="text-sm font-medium text-text-muted">Expires</span>
              <p className="text-sm text-text-main mt-1">{format(new Date(request.expires_at), 'PPP')}</p>
            </div>
          )}
        </div>

        {/* Justification */}
        <div>
          <span className="text-sm font-medium text-text-muted">Justification</span>
          <p className="text-sm text-text-main mt-2 p-4 bg-surface-hover rounded-md">{request.justification}</p>
        </div>

        {/* Review Info */}
        {request.status !== 'pending' && request.reviewed_at && (
          <div className="pt-4 border-t border-surface-card-border">
            <h3 className="text-sm font-medium text-text-muted mb-2">Review Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <span className="text-sm font-medium text-text-muted">Reviewed By</span>
                <p className="text-sm text-text-main mt-1">{request.reviewer_id?.substring(0, 8)}...</p>
              </div>
              <div>
                <span className="text-sm font-medium text-text-muted">Reviewed At</span>
                <p className="text-sm text-text-main mt-1">{format(new Date(request.reviewed_at), 'PPP')}</p>
              </div>
              {request.review_comments && (
                <div className="md:col-span-2">
                  <span className="text-sm font-medium text-text-muted">Comments</span>
                  <p className="text-sm text-text-main mt-1 p-3 bg-surface-hover rounded-md">{request.review_comments}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Created Entitlement */}
        {request.entitlement_id && (
          <div className="pt-4 border-t border-surface-card-border">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-text-muted">Entitlement Created:</span>
              <span className="text-sm text-green-600 font-mono">{request.entitlement_id.substring(0, 8)}...</span>
            </div>
          </div>
        )}
      </div>

      {/* Review Modal */}
      {showReviewModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-card rounded-lg max-w-md w-full">
            <div className="px-6 py-4 border-b border-surface-card-border">
              <h3 className="text-lg font-semibold text-text-main">Review Access Request</h3>
            </div>

            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-3">Decision</label>
                <div className="space-y-2">
                  <label
                    className={`flex items-center p-4 border-2 rounded-lg cursor-pointer ${
                      decision === 'approve'
                        ? 'border-green-500 bg-green-50'
                        : 'border-surface-card-border hover:border-border'
                    }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="approve"
                      checked={decision === 'approve'}
                      onChange={(e) => setDecision(e.target.value as 'approve')}
                      className="h-4 w-4 text-green-600 focus:ring-green-500"
                    />
                    <div className="ml-3">
                      <div className="text-sm font-medium text-text-main">Approve</div>
                      <div className="text-sm text-text-muted">Grant the requested access</div>
                    </div>
                  </label>
                  <label
                    className={`flex items-center p-4 border-2 rounded-lg cursor-pointer ${
                      decision === 'deny'
                        ? 'border-red-500 bg-red-50'
                        : 'border-surface-card-border hover:border-border'
                    }`}
                  >
                    <input
                      type="radio"
                      name="decision"
                      value="deny"
                      checked={decision === 'deny'}
                      onChange={(e) => setDecision(e.target.value as 'deny')}
                      className="h-4 w-4 text-red-600 focus:ring-red-500"
                    />
                    <div className="ml-3">
                      <div className="text-sm font-medium text-text-main">Deny</div>
                      <div className="text-sm text-text-muted">Reject the request</div>
                    </div>
                  </label>
                </div>
              </div>

              <div>
                <label htmlFor="review-comments" className="block text-sm font-medium text-text-muted mb-2">
                  Comments (Optional)
                </label>
                <textarea
                  id="review-comments"
                  rows={3}
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Add comments about your decision..."
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-surface-card-border flex justify-end gap-3">
              <button
                onClick={() => setShowReviewModal(false)}
                className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover"
              >
                Cancel
              </button>
              <button
                onClick={handleReview}
                disabled={!decision || reviewMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {reviewMutation.isPending ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

