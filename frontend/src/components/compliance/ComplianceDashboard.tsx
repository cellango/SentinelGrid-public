/**
 * Compliance Dashboard Component
 * Compliance overview aggregating findings
 */

'use client';

import { useQuery } from '@tanstack/react-query';

export default function ComplianceDashboard() {
  // Placeholder - would aggregate findings from IAM and Posture Agents
  const { data: stats, isLoading } = useQuery({
    queryKey: ['compliance-stats'],
    queryFn: async () => {
      return {
        total_findings: 0,
        open_findings: 0,
        in_progress_remediations: 0,
        completed_remediations: 0,
        nist_controls_affected: 0,
      };
    },
  });

  if (isLoading) {
    return (
      <div className="py-12 text-center text-text-muted">
        Loading compliance dashboard...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow-sm">
          <h3 className="text-sm font-medium text-text-muted">Total Findings</h3>
          <p className="mt-2 text-2xl font-bold text-text-main">
            {stats?.total_findings || 0}
          </p>
        </div>
        <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow-sm">
          <h3 className="text-sm font-medium text-text-muted">Open Findings</h3>
          <p className="mt-2 text-2xl font-bold text-text-main">
            {stats?.open_findings || 0}
          </p>
        </div>
        <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow-sm">
          <h3 className="text-sm font-medium text-text-muted">In Progress</h3>
          <p className="mt-2 text-2xl font-bold text-text-main">
            {stats?.in_progress_remediations || 0}
          </p>
        </div>
        <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow-sm">
          <h3 className="text-sm font-medium text-text-muted">Completed</h3>
          <p className="mt-2 text-2xl font-bold text-text-main">
            {stats?.completed_remediations || 0}
          </p>
        </div>
      </div>

      {/* NIST Controls Affected */}
      <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-text-main">NIST Controls Affected</h2>
        <p className="text-sm text-text-muted">
          {stats?.nist_controls_affected || 0} NIST SP 800-53 controls are associated with open findings
        </p>
      </div>
    </div>
  );
}
