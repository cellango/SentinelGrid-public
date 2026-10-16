/**
 * Certification Card Component
 * Displays a certification with entitlement details and review actions
 */

'use client';

import { Certification } from '@/lib/api/governance';
import { Entitlement } from '@/lib/api/entitlements';
import { format } from 'date-fns';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { entitlementsApi } from '@/lib/api/entitlements';
import { ReviewPanel } from './ReviewPanel';

interface CertificationCardProps {
  certification: Certification;
  onCertified?: () => void;
}

export function CertificationCard({ certification, onCertified }: CertificationCardProps) {
  const [showReviewPanel, setShowReviewPanel] = useState(false);

  // Fetch entitlement details
  const { data: entitlement, isLoading: loadingEntitlement } = useQuery({
    queryKey: ['entitlement', certification.entitlement_id],
    queryFn: () => entitlementsApi.get(certification.entitlement_id),
    enabled: !!certification.entitlement_id,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'approved':
      case 'retained':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'revoked':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-bg-alt text-text-main border-surface-card-border';
    }
  };

  if (loadingEntitlement) {
    return (
      <div className="bg-surface-card rounded-lg border border-surface-card-border p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-surface-hover rounded w-3/4 mb-4"></div>
          <div className="h-4 bg-surface-hover rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className={`bg-surface-card rounded-lg border-2 p-6 ${getStatusColor(certification.review_status)}`}>
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-text-main mb-2">
              {entitlement ? (
                <>
                  {entitlement.resource_type}:{entitlement.resource_id === '*' ? '*' : entitlement.resource_id.substring(0, 8) + '...'}
                  {' '}
                  <span className="text-blue-600">{entitlement.action}</span>
                </>
              ) : (
                'Loading...'
              )}
            </h3>
            <div className="flex items-center gap-4 text-sm text-text-muted">
              {entitlement?.last_used_at && (
                <span>
                  Last used: {format(new Date(entitlement.last_used_at), 'MMM d, yyyy')}
                </span>
              )}
              {entitlement?.usage_count_90d !== undefined && (
                <span>Used {entitlement.usage_count_90d} times (90d)</span>
              )}
            </div>
          </div>
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
              certification.review_status
            )}`}
          >
            {certification.review_status.toUpperCase()}
          </span>
        </div>

        {/* Entitlement Details */}
        {entitlement && (
          <div className="mb-4 space-y-2 text-sm">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="font-medium text-text-muted">Resource Type:</span>
                <p className="text-text-main">{entitlement.resource_type}</p>
              </div>
              <div>
                <span className="font-medium text-text-muted">Action:</span>
                <p className="text-text-main">{entitlement.action}</p>
              </div>
              <div>
                <span className="font-medium text-text-muted">Granted:</span>
                <p className="text-text-main">
                  {format(new Date(entitlement.granted_at), 'MMM d, yyyy')}
                </p>
              </div>
              {entitlement.expires_at && (
                <div>
                  <span className="font-medium text-text-muted">Expires:</span>
                  <p className="text-text-main">
                    {format(new Date(entitlement.expires_at), 'MMM d, yyyy')}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Review Status */}
        {certification.review_status === 'pending' && (
          <div className="pt-4 border-t border-surface-card-border">
            <button
              onClick={() => setShowReviewPanel(true)}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
            >
              Review Entitlement
            </button>
          </div>
        )}

        {/* Review Info */}
        {certification.review_status !== 'pending' && certification.review_date && (
          <div className="pt-4 border-t border-surface-card-border">
            <div className="text-sm text-text-muted">
              <p>
                Reviewed on {format(new Date(certification.review_date), 'MMM d, yyyy')}
              </p>
              {certification.comments && (
                <p className="mt-2 text-text-muted italic">"{certification.comments}"</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Review Panel Modal */}
      {showReviewPanel && entitlement && (
        <ReviewPanel
          certification={certification}
          entitlement={entitlement}
          onClose={() => setShowReviewPanel(false)}
          onCertified={() => {
            setShowReviewPanel(false);
            onCertified?.();
          }}
        />
      )}
    </>
  );
}

