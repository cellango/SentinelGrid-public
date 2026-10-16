/**
 * Audit Trail Viewer Component
 * Filterable timeline of entitlement changes
 */

'use client';

import { useState } from 'react';
import { useAuditTrail } from '@/lib/hooks/useCompliance';
import { format } from 'date-fns';
import { AuditTrailEntry } from '@/lib/api/compliance';

interface AuditTrailViewerProps {
  tenantId: string;
}

export function AuditTrailViewer({ tenantId }: AuditTrailViewerProps) {
  const [startDate, setStartDate] = useState<string>(
    format(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), 'yyyy-MM-dd')
  );
  const [endDate, setEndDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'));

  const { data: auditTrail, isLoading, error } = useAuditTrail({
    tenant_id: tenantId,
    start_date: startDate ? new Date(startDate).toISOString() : undefined,
    end_date: endDate ? new Date(endDate + 'T23:59:59').toISOString() : undefined,
    limit: 100,
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'revoked':
        return 'bg-red-100 text-red-800';
      case 'expired':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-bg-alt text-text-main';
    }
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
        <p className="text-red-800">Error loading audit trail. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-text-main mb-4">Audit Trail</h3>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div>
            <label htmlFor="start_date" className="block text-xs font-medium text-text-muted mb-1">
              Start Date
            </label>
            <input
              type="date"
              id="start_date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="end_date" className="block text-xs font-medium text-text-muted mb-1">
              End Date
            </label>
            <input
              type="date"
              id="end_date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 border border-border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {auditTrail && (
            <div className="ml-auto text-sm text-text-muted">
              {auditTrail.count} entries found
            </div>
          )}
        </div>
      </div>

      {/* Audit Trail List */}
      {auditTrail && auditTrail.results.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-surface-hover">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Action
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Updated
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface-card divide-y divide-border">
              {auditTrail.results.map((entry: AuditTrailEntry) => (
                <tr key={entry.entitlement_id} className="hover:bg-surface-hover">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-text-main">{entry.resource_type}</div>
                    <div className="text-sm text-text-muted font-mono">
                      {entry.resource_id === '*' ? '*' : entry.resource_id.substring(0, 16) + '...'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-text-main">{entry.action}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                        entry.status
                      )}`}
                    >
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                    {entry.updated_at
                      ? format(new Date(entry.updated_at), 'MMM d, yyyy HH:mm')
                      : entry.granted_at
                      ? format(new Date(entry.granted_at), 'MMM d, yyyy HH:mm')
                      : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-text-muted">No audit trail entries found for the selected date range.</p>
        </div>
      )}
    </div>
  );
}

