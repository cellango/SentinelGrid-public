/**
 * Playbook Executions Page
 * List and monitor playbook executions with alert linkage
 */

'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { playbooksApi, type PlaybookExecutionRecord } from '@/lib/api/playbooks';
import Link from 'next/link';
import ExecutionDetail from '@/components/executions/ExecutionDetail';
import { getSourceHealth, type SourceHealth } from '@/lib/api/siem';
import HealthBadge from '@/components/ui/HealthBadge';
import { useSearchParams } from 'next/navigation';

export default function PlaybookExecutionsPage() {
  const searchParams = useSearchParams();
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);
  const [filter, setFilter] = useState<{
    status?: string;
    approvalStatus?: string;
    alertId?: string;
  }>({
    status: searchParams.get('status') || undefined,
    approvalStatus: searchParams.get('approval_status') || undefined,
    alertId: searchParams.get('alert_id') || undefined,
  });

  useEffect(() => {
    setFilter({
      status: searchParams.get('status') || undefined,
      approvalStatus: searchParams.get('approval_status') || undefined,
      alertId: searchParams.get('alert_id') || undefined,
    });
  }, [searchParams]);

  const { data: executions, isLoading } = useQuery<PlaybookExecutionRecord[]>({
    queryKey: ['playbook-executions', filter],
    queryFn: async () =>
      playbooksApi.listExecutions({
        status: filter.status,
        approval_status: filter.approvalStatus,
        alert_id: filter.alertId,
      }),
  });
  const { data: sourceHealth } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  if (selectedExecution) {
    return (
      <ExecutionDetail
        executionId={selectedExecution}
        onBack={() => setSelectedExecution(null)}
      />
    );
  }

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">
            Playbook Executions
          </h1>
          <p className="mt-1 text-sm text-text-muted dark:text-text-muted">
            Monitor and track playbook execution history
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 text-xs text-text-muted dark:text-text-muted">
        <span className="uppercase tracking-wide">Pipeline health</span>
        <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
        <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
        <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
      </div>

      {/* Filters */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-4">
        <div className="flex gap-4">
          <div>
            <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
              Status
            </label>
            <select
              value={filter.status || 'all'}
              onChange={(e) =>
                setFilter({ ...filter, status: e.target.value === 'all' ? undefined : e.target.value })
              }
              className="px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
              Approval
            </label>
            <select
              value={filter.approvalStatus || 'all'}
              onChange={(e) =>
                setFilter({
                  ...filter,
                  approvalStatus: e.target.value === 'all' ? undefined : e.target.value,
                })
              }
              className="px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
            >
              <option value="all">All approvals</option>
              <option value="pending">Awaiting approval</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-1">
              Alert ID
            </label>
            <input
              type="text"
              value={filter.alertId || ''}
              onChange={(e) =>
                setFilter({ ...filter, alertId: e.target.value || undefined })
              }
              placeholder="Filter by alert ID"
              className="px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
            />
          </div>
        </div>
      </div>

      {/* Executions Table */}
      {isLoading ? (
        <div className="text-center py-12 text-text-muted dark:text-text-muted">
          Loading executions...
        </div>
      ) : !executions || executions.length === 0 ? (
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-12 text-center">
          <p className="text-text-muted dark:text-text-muted">No executions found</p>
        </div>
      ) : (
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border overflow-hidden">
          <table className="min-w-full divide-y divide-border dark:divide-gray-700">
            <thead className="bg-surface-hover dark:bg-bg">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Execution ID
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Status / Approval
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Triggered By
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Playbook / Detection
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Alert
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Versions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Started
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted dark:text-text-muted uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface-card divide-y divide-border dark:divide-gray-700">
              {executions.map((execution) => (
                <tr
                  key={execution.id}
                  className="hover:bg-surface-hover dark:hover:bg-bg"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                    {execution.id.slice(0, 8)}...
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        execution.status === 'completed'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : execution.status === 'running'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          : execution.status === 'failed'
                          ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          : 'bg-bg-alt text-text-main dark:bg-bg-alt dark:text-text-muted'
                      }`}
                    >
                      {execution.status}
                    </span>
                    {execution.approval_status && (
                      <div className="mt-1">
                        <span
                          className={`px-2 py-1 text-[11px] font-medium rounded-full ${
                            execution.approval_status === 'approved'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200'
                              : execution.approval_status === 'pending'
                              ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                              : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                          }`}
                        >
                          {execution.approval_status}
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted dark:text-text-muted">
                    {execution.triggered_by}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex flex-col text-xs text-text-muted dark:text-text-muted">
                      {execution.playbook_id ? (
                        <Link
                          href={`/dashboard/playbooks/${execution.playbook_id}/edit`}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          {execution.playbook_name || `Playbook ${execution.playbook_id.slice(0, 8)}...`}
                        </Link>
                      ) : (
                        <span className="text-text-muted">Playbook: —</span>
                      )}
                      {execution.detection_rule_id ? (
                        <Link
                          href={`/dashboard/siem/detection-rules/${execution.detection_rule_id}`}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          Detection {execution.detection_rule_id.slice(0, 8)}...
                        </Link>
                      ) : (
                        <span className="text-text-muted">Detection: —</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {execution.alert_id ? (
                      <Link
                        href={`/dashboard/alerts/${execution.alert_id}`}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        {execution.alert_id.slice(0, 8)}...
                      </Link>
                    ) : (
                      <span className="text-text-muted">-</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-[11px] text-text-muted dark:text-text-muted">
                    {execution.detection_rule_version_id && (
                      <div>Det vID: {execution.detection_rule_version_id}</div>
                    )}
                    {execution.playbook_version_id && (
                      <div>PB vID: {execution.playbook_version_id}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted dark:text-text-muted">
                    {execution.started_at
                      ? new Date(execution.started_at).toLocaleString()
                      : '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => setSelectedExecution(execution.id)}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
