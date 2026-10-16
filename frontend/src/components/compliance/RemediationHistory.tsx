/**
 * Remediation History Component
 * Show remediation playbook executions
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { getRemediationStatus } from '@/lib/api/compliance-remediation';
import Link from 'next/link';

interface RemediationHistoryProps {
  findingId: string;
  findingType: 'iam_finding' | 'posture_finding';
}

export default function RemediationHistory({
  findingId,
  findingType,
}: RemediationHistoryProps) {
  const { data: status, isLoading } = useQuery({
    queryKey: ['remediation-status', findingId, findingType],
    queryFn: () => getRemediationStatus(findingId, findingType),
  });

  if (isLoading) {
    return (
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
        <div className="text-sm text-text-muted dark:text-text-muted">Loading remediation history...</div>
      </div>
    );
  }

  if (!status || status.status === 'not_started') {
    return (
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
        <h2 className="text-lg font-semibold text-text-main mb-4">
          Remediation History
        </h2>
        <div className="text-center py-8 text-text-muted dark:text-text-muted">
          <p className="text-sm">No remediation history</p>
          <p className="text-xs mt-1">Remediation has not been started for this finding</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
      <h2 className="text-lg font-semibold text-text-main mb-4">
        Remediation History
      </h2>

      <div className="space-y-4">
        <div className="p-4 bg-surface-hover dark:bg-bg rounded-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-text-main">
              Status: {status.status}
            </span>
            <span
              className={`px-2 py-1 text-xs font-medium rounded-full ${
                status.status === 'completed'
                  ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                  : status.status === 'in_progress'
                  ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                  : status.status === 'failed'
                  ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  : 'bg-bg-alt text-text-main dark:bg-bg-alt dark:text-text-muted'
              }`}
            >
              {status.status}
            </span>
          </div>
          {status.execution_id && (
            <div className="mt-2">
              <Link
                href={`/dashboard/playbooks/executions/${status.execution_id}`}
                className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                View Execution: {status.execution_id.slice(0, 8)}...
              </Link>
            </div>
          )}
          {status.created_at && (
            <p className="text-xs text-text-muted dark:text-text-muted mt-2">
              Started: {new Date(status.created_at).toLocaleString()}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

