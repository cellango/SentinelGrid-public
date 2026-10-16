/**
 * Bulk Certification Actions Component
 * Handles bulk certification decisions
 */

'use client';

import { useState } from 'react';
import { useBulkCertify } from '@/lib/hooks/useCertifications';

interface BulkCertificationActionsProps {
  certificationIds: string[];
  onComplete: () => void;
}

export function BulkCertificationActions({ certificationIds, onComplete }: BulkCertificationActionsProps) {
  const [decision, setDecision] = useState<'approved' | 'revoked' | 'retained' | null>(null);
  const [comments, setComments] = useState('');
  const [showModal, setShowModal] = useState(false);
  const bulkCertify = useBulkCertify();

  const handleSubmit = async () => {
    if (!decision) return;

    try {
      await bulkCertify.mutateAsync({
        certification_ids: certificationIds,
        decision,
        comments: comments.trim() || undefined,
      });
      setShowModal(false);
      onComplete();
    } catch (error) {
      // Error handled by mutation hook
    }
  };

  return (
    <>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-blue-900">
            {certificationIds.length} certification{certificationIds.length !== 1 ? 's' : ''} selected
          </span>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
        >
          Bulk Certify
        </button>
      </div>

      {/* Bulk Certify Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface-card rounded-lg max-w-md w-full">
            {/* Header */}
            <div className="px-6 py-4 border-b border-surface-card-border">
              <h2 className="text-xl font-semibold text-text-main">
                Bulk Certify {certificationIds.length} Certification{certificationIds.length !== 1 ? 's' : ''}
              </h2>
            </div>

            {/* Content */}
            <div className="px-6 py-4 space-y-6">
              {/* Decision */}
              <div>
                <label className="block text-sm font-medium text-text-muted mb-3">
                  Decision <span className="text-red-500">*</span>
                </label>
                <div className="space-y-3">
                  {[
                    {
                      value: 'retained' as const,
                      label: 'Retain All',
                      description: 'Keep all selected entitlements active',
                      color: 'bg-green-50 border-green-200 text-green-800',
                    },
                    {
                      value: 'revoked' as const,
                      label: 'Revoke All',
                      description: 'Remove all selected entitlements',
                      color: 'bg-red-50 border-red-200 text-red-800',
                    },
                    {
                      value: 'approved' as const,
                      label: 'Approve All',
                      description: 'Approve and keep all selected entitlements',
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
                        name="bulk-decision"
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
                <label htmlFor="bulk-comments" className="block text-sm font-medium text-text-muted mb-2">
                  Comments (Optional)
                </label>
                <textarea
                  id="bulk-comments"
                  rows={3}
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Add comments for all certifications..."
                />
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-surface-card-border flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!decision || bulkCertify.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {bulkCertify.isPending ? 'Submitting...' : 'Submit Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

