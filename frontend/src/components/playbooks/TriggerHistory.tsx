/**
 * Trigger History Component
 * Show alerts that triggered this playbook
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { automatedResponseClient } from '@/lib/api/client';
import Link from 'next/link';

interface TriggerHistoryProps {
  playbookId: string;
}

interface TriggerHistoryItem {
  id: string;
  alert_id: string;
  trigger_reason: string;
  evaluated_at: string;
  triggered_at?: string;
  playbook_execution_id?: string;
}

export default function TriggerHistory({ playbookId }: TriggerHistoryProps) {
  const { data: triggers, isLoading } = useQuery({
    queryKey: ['playbook-triggers', playbookId],
    queryFn: async () => {
      // Note: This endpoint would need to be added to the Automated Response Service
      // For now, return empty array
      return [] as TriggerHistoryItem[];
    },
    enabled: !!playbookId,
  });

  if (isLoading) {
    return (
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
        <div className="text-sm text-text-muted dark:text-text-muted">Loading trigger history...</div>
      </div>
    );
  }

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
      <h2 className="text-lg font-semibold text-text-main mb-4">
        Trigger History
      </h2>
      <p className="text-sm text-text-muted dark:text-text-muted mb-4">
        Recent alerts that triggered this playbook
      </p>

      {!triggers || triggers.length === 0 ? (
        <div className="text-center py-8 text-text-muted dark:text-text-muted">
          <p className="text-sm">No triggers yet</p>
          <p className="text-xs mt-1">This playbook hasn't been triggered automatically</p>
        </div>
      ) : (
        <div className="space-y-3">
          {triggers.slice(0, 10).map((trigger) => (
            <div
              key={trigger.id}
              className="p-3 bg-surface-hover dark:bg-bg rounded-md hover:bg-bg-alt dark:hover:bg-surface-card transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <Link
                    href={`/dashboard/alerts/${trigger.alert_id}`}
                    className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Alert {trigger.alert_id.slice(0, 8)}...
                  </Link>
                  <p className="text-xs text-text-muted dark:text-text-muted mt-1">
                    {trigger.trigger_reason}
                  </p>
                  <p className="text-xs text-text-muted dark:text-text-muted mt-1">
                    {new Date(trigger.evaluated_at).toLocaleString()}
                  </p>
                </div>
                {trigger.playbook_execution_id && (
                  <Link
                    href={`/dashboard/playbooks/executions/${trigger.playbook_execution_id}`}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    View Execution
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

