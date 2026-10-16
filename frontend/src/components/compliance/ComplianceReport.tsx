/**
 * Compliance Report Component
 * Detailed compliance report with export functionality
 */

'use client';

import { ComplianceReport as ComplianceReportType } from '@/lib/api/compliance';
import { format } from 'date-fns';
import { useState } from 'react';

interface ComplianceReportProps {
  report: ComplianceReportType;
}

export function ComplianceReport({ report }: ComplianceReportProps) {
  const [exporting, setExporting] = useState(false);

  const handleExportPDF = () => {
    // TODO: Implement PDF export
    setExporting(true);
    setTimeout(() => {
      setExporting(false);
      alert('PDF export functionality coming soon!');
    }, 1000);
  };

  const handleExportCSV = () => {
    // Export report data as CSV
    const csvRows = [
      ['Compliance Report', report.report_date],
      [],
      ['Metric', 'Value'],
      ['Total Entitlements', report.total_entitlements],
      ['Active Entitlements', report.active_entitlements],
      ['Revoked Entitlements', report.revoked_entitlements],
      ['Expired Entitlements', report.expired_entitlements],
      ['Pending Review', report.pending_review],
      ['Users with Entitlements', report.users_with_entitlements],
      [],
      ['Entitlements by Resource Type', 'Count'],
      ...Object.entries(report.entitlements_by_resource_type).map(([type, count]) => [type, count]),
      [],
      ['Entitlements by Action', 'Count'],
      ...Object.entries(report.entitlements_by_action).map(([action, count]) => [action, count]),
    ];

    const csv = csvRows.map((row) => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `compliance-report-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-text-main">Detailed Compliance Report</h3>
          <p className="text-sm text-text-muted mt-1">
            Generated on {format(new Date(report.report_date), 'PPpp')}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleExportCSV}
            className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover"
          >
            Export CSV
          </button>
          <button
            onClick={handleExportPDF}
            disabled={exporting}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {exporting ? 'Exporting...' : 'Export PDF'}
          </button>
        </div>
      </div>

      {/* Summary Section */}
      <div className="mb-6 pb-6 border-b border-surface-card-border">
        <h4 className="text-sm font-semibold text-text-main mb-4">Summary</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <span className="text-sm text-text-muted">Total Entitlements</span>
            <p className="text-2xl font-bold text-text-main">{report.total_entitlements}</p>
          </div>
          <div>
            <span className="text-sm text-text-muted">Active</span>
            <p className="text-2xl font-bold text-green-600">{report.active_entitlements}</p>
          </div>
          <div>
            <span className="text-sm text-text-muted">Revoked</span>
            <p className="text-2xl font-bold text-red-600">{report.revoked_entitlements}</p>
          </div>
          <div>
            <span className="text-sm text-text-muted">Expired</span>
            <p className="text-2xl font-bold text-yellow-600">{report.expired_entitlements}</p>
          </div>
          <div>
            <span className="text-sm text-text-muted">Pending Review</span>
            <p className="text-2xl font-bold text-blue-600">{report.pending_review}</p>
          </div>
          <div>
            <span className="text-sm text-text-muted">Users with Entitlements</span>
            <p className="text-2xl font-bold text-purple-600">{report.users_with_entitlements}</p>
          </div>
        </div>
      </div>

      {/* Breakdown by Resource Type */}
      {Object.keys(report.entitlements_by_resource_type).length > 0 && (
        <div className="mb-6 pb-6 border-b border-surface-card-border">
          <h4 className="text-sm font-semibold text-text-main mb-4">By Resource Type</h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-surface-hover">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-text-muted uppercase">Resource Type</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted uppercase">Count</th>
                </tr>
              </thead>
              <tbody className="bg-surface-card divide-y divide-border">
                {Object.entries(report.entitlements_by_resource_type)
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => (
                    <tr key={type}>
                      <td className="px-4 py-2 text-sm text-text-main">{type}</td>
                      <td className="px-4 py-2 text-sm text-text-main text-right">{count}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Breakdown by Action */}
      {Object.keys(report.entitlements_by_action).length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-text-main mb-4">By Action</h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-surface-hover">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-text-muted uppercase">Action</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted uppercase">Count</th>
                </tr>
              </thead>
              <tbody className="bg-surface-card divide-y divide-border">
                {Object.entries(report.entitlements_by_action)
                  .sort(([, a], [, b]) => b - a)
                  .map(([action, count]) => (
                    <tr key={action}>
                      <td className="px-4 py-2 text-sm text-text-main">{action}</td>
                      <td className="px-4 py-2 text-sm text-text-main text-right">{count}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

