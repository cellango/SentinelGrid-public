/**
 * Review Panel Component
 * Panel for reviewing and certifying an entitlement
 */

'use client';

import { Certification } from '@/lib/api/governance';
import { Entitlement } from '@/lib/api/entitlements';
import { useCertifyEntitlement } from '@/lib/hooks/useCertifications';
import { useState } from 'react';
import { format } from 'date-fns';

interface ReviewPanelProps {
  certification: Certification;
  entitlement: Entitlement;
  onClose: () => void;
  onCertified: () => void;
}

export function ReviewPanel({ certification, entitlement, onClose, onCertified }: ReviewPanelProps) {
  const [decision, setDecision] = useState<'approved' | 'revoked' | 'retained' | null>(null);
  const [comments, setComments] = useState('');
  const certifyMutation = useCertifyEntitlement();

  const handleSubmit = async () => {
    if (!decision) return;

    try {
      await certifyMutation.mutateAsync({
        certificationId: certification.id,
        decision: {
          decision,
          comments: comments.trim() || undefined,
        },
      });
      onCertified();
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-surface-card rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-surface-card-border flex items-center justify-between">
          <h2 className="text-xl font-semibold text-text-main">Review Entitlement</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-muted"
            aria-label="Close"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Entitlement Details */}
          <div className="bg-surface-hover rounded-lg p-4">
            <h3 className="text-sm font-medium text-text-muted mb-3">Entitlement Details</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium text-text-muted">Resource Type:</span>
                <p className="text-text-main mt-1">{entitlement.resource_type}</p>
              </div>
              <div>
                <span className="font-medium text-text-muted">Resource ID:</span>
                <p className="text-text-main mt-1 font-mono">
                  {entitlement.resource_id === '*' ? 'All (*)' : entitlement.resource_id}
                </p>
              </div>
              <div>
                <span className="font-medium text-text-muted">Action:</span>
                <p className="text-text-main mt-1">{entitlement.action}</p>
              </div>
              <div>
                <span className="font-medium text-text-muted">Status:</span>
                <p className="text-text-main mt-1 capitalize">{entitlement.status}</p>
              </div>
              <div>
                <span className="font-medium text-text-muted">Granted:</span>
                <p className="text-text-main mt-1">
                  {format(new Date(entitlement.granted_at), 'MMM d, yyyy')}
                </p>
              </div>
              {entitlement.expires_at && (
                <div>
                  <span className="font-medium text-text-muted">Expires:</span>
                  <p className="text-text-main mt-1">
                    {format(new Date(entitlement.expires_at), 'MMM d, yyyy')}
                  </p>
                </div>
              )}
            </div>

            {/* Usage Stats */}
            {(entitlement.last_used_at || entitlement.usage_count_90d > 0) && (
              <div className="mt-4 pt-4 border-t border-surface-card-border">
                <h4 className="text-sm font-medium text-text-muted mb-2">Usage Statistics</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {entitlement.last_used_at && (
                    <div>
                      <span className="text-text-muted">Last Used:</span>
                      <p className="text-text-main">
                        {format(new Date(entitlement.last_used_at), 'MMM d, yyyy')}
                      </p>
                    </div>
                  )}
                  <div>
                    <span className="text-text-muted">Used in last 90 days:</span>
                    <p className="text-text-main">{entitlement.usage_count_90d} times</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Decision */}
          <div>
            <label className="block text-sm font-medium text-text-muted mb-3">
              Decision <span className="text-red-500">*</span>
            </label>
            <div className="space-y-3">
              {[
                {
                  value: 'retained' as const,
                  label: 'Retain',
                  description: 'Keep this entitlement active',
                  color: 'bg-green-50 border-green-200 text-green-800',
                },
                {
                  value: 'revoked' as const,
                  label: 'Revoke',
                  description: 'Remove this entitlement',
                  color: 'bg-red-50 border-red-200 text-red-800',
                },
                {
                  value: 'approved' as const,
                  label: 'Approve',
                  description: 'Approve and keep this entitlement',
                  color: 'bg-blue-50 border-blue-200 text-blue-800',
                },
              ].map((option) => (
                <label
                  key={option.value}
                  className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                    decision === option.value
                      ? option.color
                      : 'border-surface-card-border hover:border-border'
                  }`}
                >
                  <input
                    type="radio"
                    name="decision"
                    value={option.value}
                    checked={decision === option.value}
                    onChange={(e) => setDecision(e.target.value as typeof decision)}
                    className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="ml-3 flex-1">
                    <div className="text-sm font-medium">{option.label}</div>
                    <div className="text-sm opacity-75">{option.description}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div>
            <label htmlFor="comments" className="block text-sm font-medium text-text-muted mb-2">
              Comments (Optional)
            </label>
            <textarea
              id="comments"
              rows={4}
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Add any comments about this decision..."
            />
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-surface-card-border flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!decision || certifyMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {certifyMutation.isPending ? 'Submitting...' : 'Submit Decision'}
          </button>
        </div>
      </div>
    </div>
  );
}

