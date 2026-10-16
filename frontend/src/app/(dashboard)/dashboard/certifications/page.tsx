/**
 * Certifications Page
 * Main page for users to certify their entitlements
 */

'use client';

import { CertificationList } from '@/components/certifications/CertificationList';
import { useState } from 'react';

export default function CertificationsPage() {
  const [statusFilter, setStatusFilter] = useState<'pending' | 'all'>('pending');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">My Certifications</h1>
          <p className="mt-1 text-sm text-text-muted">
            Review and certify your entitlements
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setStatusFilter('pending')}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              statusFilter === 'pending'
                ? 'bg-blue-600 text-white'
                : 'bg-bg-alt text-text-muted hover:bg-surface-hover'
            }`}
          >
            Pending
          </button>
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              statusFilter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-bg-alt text-text-muted hover:bg-surface-hover'
            }`}
          >
            All
          </button>
        </div>
      </div>

      {/* Certifications List */}
      {statusFilter === 'pending' ? (
        <CertificationList />
      ) : (
        <div className="bg-surface-hover border border-surface-card-border rounded-lg p-8 text-center">
          <p className="text-text-muted">All certifications view coming soon.</p>
        </div>
      )}
    </div>
  );
}

