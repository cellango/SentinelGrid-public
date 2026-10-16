'use client';

import React from 'react';
import type { PhishingFilters } from '@/lib/api/phishing';

interface PhishingFiltersProps {
  filters: PhishingFilters;
  onFilterChange: (filters: Partial<PhishingFilters>) => void;
}

const PhishingFilters: React.FC<PhishingFiltersProps> = ({ filters, onFilterChange }) => {
  return (
    <div className="bg-surface-dark border border-surface-card-border rounded-lg p-4">
      <h2 className="text-lg font-semibold text-text-main mb-4">Filters</h2>

      <div className="space-y-4">
        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-text-main mb-2">
            Status
          </label>
          <select
            value={filters.status || ''}
            onChange={(e) => onFilterChange({ status: e.target.value || undefined })}
            className="w-full px-3 py-2 bg-surface-light border border-surface-card-border rounded-lg text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Statuses</option>
            <option value="new">New</option>
            <option value="in_review">In Review</option>
            <option value="confirmed_phishing">Confirmed Phishing</option>
            <option value="confirmed_benign">Confirmed Benign</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>

        {/* Classification Filter */}
        <div>
          <label className="block text-sm font-medium text-text-main mb-2">
            Classification
          </label>
          <select
            value={filters.classification || ''}
            onChange={(e) => onFilterChange({ classification: e.target.value || undefined })}
            className="w-full px-3 py-2 bg-surface-light border border-surface-card-border rounded-lg text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Classifications</option>
            <option value="phishing">Phishing</option>
            <option value="benign">Benign</option>
            <option value="suspicious">Suspicious</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        {/* Severity Filter */}
        <div>
          <label className="block text-sm font-medium text-text-main mb-2">
            Severity
          </label>
          <select
            value={filters.severity || ''}
            onChange={(e) => onFilterChange({ severity: e.target.value || undefined })}
            className="w-full px-3 py-2 bg-surface-light border border-surface-card-border rounded-lg text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Clear Filters */}
        <button
          onClick={() => onFilterChange({ status: undefined, classification: undefined, severity: undefined })}
          className="w-full px-4 py-2 bg-bg-alt hover:bg-bg-alt text-white rounded-lg transition-colors"
        >
          Clear Filters
        </button>
      </div>
    </div>
  );
};

export default PhishingFilters;

