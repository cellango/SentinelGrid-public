/**
 * Execution Detail Component
 * Show execution details with alert linkage and trigger metadata
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { playbooksApi } from '@/lib/api/playbooks';
import Link from 'next/link';

interface ExecutionDetailProps {
  executionId: string;
  onBack: () => void;
}

export default function ExecutionDetail({ executionId, onBack }: ExecutionDetailProps) {
  const { data: execution, isLoading } = useQuery({
    queryKey: ['playbook-execution', executionId],
    queryFn: () => playbooksApi.getExecution(executionId),
    enabled: !!executionId,
  });

  if (isLoading) {
    return (
      <div className="text-center py-12 text-text-muted dark:text-text-muted">
        Loading execution details...
      </div>
    );
  }

  if (!execution) {
    return (
      <div className="text-center py-12 text-red-600">
        Execution not found
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={onBack}
            className="text-sm text-text-muted dark:text-text-muted hover:text-text-main dark:hover:text-white mb-2"
          >
            ← Back to Executions
          </button>
          <h1 className="text-2xl font-bold text-text-main">
            Execution Details
          </h1>
        </div>
      </div>

      {/* Execution Info */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-text-muted dark:text-text-muted">
              Execution ID
            </label>
            <p className="mt-1 text-sm text-text-main">{execution.id}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-text-muted dark:text-text-muted">
              Status
            </label>
            <p className="mt-1 text-sm text-text-main">{execution.status}</p>
          </div>
          {(execution as any).approval_status && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Approval Status
              </label>
              <p className="mt-1 text-sm text-text-main">{(execution as any).approval_status}</p>
            </div>
          )}
          <div>
            <label className="text-sm font-medium text-text-muted dark:text-text-muted">
              Triggered By
            </label>
            <p className="mt-1 text-sm text-text-main">
              {execution.triggered_by || 'manual'}
            </p>
          </div>
          {(execution as any).alert_id && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Related Alert
              </label>
              <p className="mt-1">
                <Link
                  href={`/dashboard/alerts/${(execution as any).alert_id}`}
                  className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  View Alert {(execution as any).alert_id.slice(0, 8)}...
                </Link>
              </p>
            </div>
          )}
          {(execution as any).playbook_id && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Playbook
              </label>
              <p className="mt-1">
                <Link
                  href={`/dashboard/playbooks/${(execution as any).playbook_id}/edit`}
                  className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  {(execution as any).playbook_id}
                </Link>
              </p>
            </div>
          )}
          {(execution as any).detection_rule_id && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Detection Rule
              </label>
              <p className="mt-1">
                <Link
                  href={`/dashboard/siem/detection-rules/${(execution as any).detection_rule_id}`}
                  className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  {(execution as any).detection_rule_id}
                </Link>
              </p>
            </div>
          )}
          {(execution as any).detection_rule_version_id && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Detection Rule Version
              </label>
              <p className="mt-1 text-sm text-text-main font-mono break-all">
                {(execution as any).detection_rule_version_id}
              </p>
            </div>
          )}
          {(execution as any).playbook_version_id && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Playbook Version
              </label>
              <p className="mt-1 text-sm text-text-main font-mono break-all">
                {(execution as any).playbook_version_id}
              </p>
            </div>
          )}
          {execution.started_at && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Started At
              </label>
              <p className="mt-1 text-sm text-text-main">
                {new Date(execution.started_at).toLocaleString()}
              </p>
            </div>
          )}
          {execution.completed_at && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Completed At
              </label>
              <p className="mt-1 text-sm text-text-main">
                {new Date(execution.completed_at).toLocaleString()}
              </p>
            </div>
          )}
          {(execution as any).result && (
            <div>
              <label className="text-sm font-medium text-text-muted dark:text-text-muted">
                Result
              </label>
              <p className="mt-1 text-sm text-text-main whitespace-pre-wrap break-words">
                {typeof (execution as any).result === 'string'
                  ? (execution as any).result
                  : JSON.stringify((execution as any).result, null, 2)}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Execution Logs */}
      {execution.logs && execution.logs.length > 0 && (
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
          <h2 className="text-lg font-semibold text-text-main mb-4">
            Execution Logs
          </h2>
          <div className="space-y-2">
            {execution.logs.map((log: any, index: number) => (
              <div
                key={index}
                className="p-3 bg-surface-hover dark:bg-bg rounded-md text-sm font-mono text-text-main"
              >
                {JSON.stringify(log, null, 2)}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
