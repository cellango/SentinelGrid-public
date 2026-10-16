/**
 * Certification List Component
 * Lists certifications with filters and bulk actions
 */

'use client';

import { useState } from 'react';
import { usePendingCertifications } from '@/lib/hooks/useCertifications';
import { CertificationCard } from './CertificationCard';
import { BulkCertificationActions } from './BulkCertificationActions';

interface CertificationListProps {
  campaignId?: string;
  userId?: string;
}

export function CertificationList({ campaignId, userId }: CertificationListProps) {
  const [selectedCertifications, setSelectedCertifications] = useState<Set<string>>(new Set());
  const { data: certifications, isLoading, error, refetch } = usePendingCertifications({
    campaign_id: campaignId,
    user_id: userId,
  });

  const toggleSelection = (certificationId: string) => {
    const newSelection = new Set(selectedCertifications);
    if (newSelection.has(certificationId)) {
      newSelection.delete(certificationId);
    } else {
      newSelection.add(certificationId);
    }
    setSelectedCertifications(newSelection);
  };

  const handleCertified = () => {
    setSelectedCertifications(new Set());
    refetch();
  };

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
        <p className="text-red-800">Error loading certifications. Please try again.</p>
      </div>
    );
  }

  if (!certifications || certifications.length === 0) {
    return (
      <div className="bg-surface-hover border border-surface-card-border rounded-lg p-8 text-center">
        <p className="text-text-muted">No pending certifications found.</p>
        <p className="text-sm text-text-muted mt-2">All certifications have been completed.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Bulk Actions */}
      {selectedCertifications.size > 0 && (
        <BulkCertificationActions
          certificationIds={Array.from(selectedCertifications)}
          onComplete={() => {
            setSelectedCertifications(new Set());
            refetch();
          }}
        />
      )}

      {/* List Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-main">
            Pending Certifications ({certifications.length})
          </h2>
          <p className="text-sm text-text-muted mt-1">
            Review and certify your entitlements
          </p>
        </div>
        {certifications.length > 0 && (
          <label className="flex items-center text-sm text-text-muted">
            <input
              type="checkbox"
              checked={selectedCertifications.size === certifications.length}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedCertifications(new Set(certifications.map((c) => c.id)));
                } else {
                  setSelectedCertifications(new Set());
                }
              }}
              className="rounded border-border text-blue-600 focus:ring-blue-500 mr-2"
            />
            Select All
          </label>
        )}
      </div>

      {/* Certifications Grid */}
      <div className="space-y-4">
        {certifications.map((certification) => (
          <div key={certification.id} className="flex items-start gap-3">
            <input
              type="checkbox"
              checked={selectedCertifications.has(certification.id)}
              onChange={() => toggleSelection(certification.id)}
              className="mt-6 rounded border-border text-blue-600 focus:ring-blue-500"
            />
            <div className="flex-1">
              <CertificationCard certification={certification} onCertified={handleCertified} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

