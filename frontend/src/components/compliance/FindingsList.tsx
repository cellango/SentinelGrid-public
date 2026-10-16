/**
 * Findings List Component
 * List IAM and Posture findings with remediation capabilities
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { complianceClient } from '@/lib/api/client';
import FindingDetail from './FindingDetail';

interface Finding {
  id: string;
  finding_type: string;
  severity: string;
  description: string;
  status: string;
  remediation_status?: string;
  nist_control_id?: string;
  detected_at: string;
}

interface FindingsListProps {
  onSelectFinding?: (finding: { id: string; type: 'iam_finding' | 'posture_finding' } | null) => void;
  selectedFinding?: { id: string; type: 'iam_finding' | 'posture_finding' } | null;
}

export default function FindingsList({
  onSelectFinding,
  selectedFinding,
}: FindingsListProps) {
  const [findingType, setFindingType] = useState<'iam_finding' | 'posture_finding' | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Note: These endpoints would need to be created in IAM Agent and Posture Agent
  // For now, we'll use placeholder queries
  const { data: iamFindings, isLoading: iamLoading } = useQuery({
    queryKey: ['iam-findings'],
    queryFn: async () => {
      // Placeholder - would call IAM Agent API
      return [] as Finding[];
    },
  });

  const { data: postureFindings, isLoading: postureLoading } = useQuery({
    queryKey: ['posture-findings'],
    queryFn: async () => {
      // Placeholder - would call Posture Agent API
      return [] as Finding[];
    },
  });

  const allFindings = [
    ...(iamFindings || []).map(f => ({ ...f, type: 'iam_finding' as const })),
    ...(postureFindings || []).map(f => ({ ...f, type: 'posture_finding' as const })),
  ];

  const filteredFindings = allFindings.filter(finding => {
    if (findingType !== 'all' && finding.type !== findingType) return false;
    if (statusFilter !== 'all' && finding.remediation_status !== statusFilter) return false;
    return true;
  });

  const isLoading = iamLoading || postureLoading;

  if (selectedFinding) {
    return (
      <FindingDetail
        findingId={selectedFinding.id}
        findingType={selectedFinding.type}
        onBack={() => onSelectFinding?.(null)}
      />
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="bg-surface-card rounded-lg border border-surface-card-border p-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label htmlFor="finding-type-filter" className="block text-sm font-medium text-text-muted mb-1">
              Finding Type
            </label>
            <select
              id="finding-type-filter"
              value={findingType}
              onChange={(e) => setFindingType(e.target.value as any)}
              className="px-3 py-2.5 min-h-[44px] border border-border rounded-md bg-surface-input text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Findings</option>
              <option value="iam_finding">IAM Findings</option>
              <option value="posture_finding">Posture Findings</option>
            </select>
          </div>
          <div>
            <label htmlFor="status-filter" className="block text-sm font-medium text-text-muted mb-1">
              Remediation Status
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2.5 min-h-[44px] border border-border rounded-md bg-surface-input text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Findings Table */}
      {isLoading ? (
        <div className="text-center py-12 text-text-muted" role="status">
          <span>Loading findings...</span>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="bg-surface-card rounded-lg border border-surface-card-border p-12 text-center">
          <p className="text-text-muted">No findings found</p>
        </div>
      ) : (
        <div className="bg-surface-card rounded-lg border border-surface-card-border overflow-hidden">
          <table className="min-w-full divide-y divide-border">
            <caption className="sr-only">Security findings list with severity, description, and remediation status</caption>
            <thead className="bg-surface-card-border">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Type
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Severity
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Description
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Remediation Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  NIST Control
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-surface-card divide-y divide-border">
              {filteredFindings.map((finding) => (
                <tr
                  key={finding.id}
                  className="hover:bg-surface-hover cursor-pointer transition-colors"
                  onClick={() => onSelectFinding?.({ id: finding.id, type: finding.type })}
                  tabIndex={0}
                  role="row"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectFinding?.({ id: finding.id, type: finding.type });
                    }
                  }}
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                    {finding.type === 'iam_finding' ? 'IAM' : 'Posture'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        finding.severity === 'critical'
                          ? 'bg-red-500/20 text-red-400'
                          : finding.severity === 'high'
                          ? 'bg-orange-500/20 text-orange-400'
                          : finding.severity === 'medium'
                          ? 'bg-yellow-500/20 text-yellow-400'
                          : 'bg-blue-500/20 text-blue-400'
                      }`}
                    >
                      {finding.severity}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-text-main max-w-md truncate">
                    {finding.description}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded-full ${
                        finding.remediation_status === 'resolved'
                          ? 'bg-green-500/20 text-green-400'
                          : finding.remediation_status === 'in_progress'
                          ? 'bg-blue-500/20 text-blue-400'
                          : finding.remediation_status === 'failed'
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-slate-500/20 text-text-muted'
                      }`}
                    >
                      {finding.remediation_status || 'open'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                    {finding.nist_control_id || '-'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectFinding?.({ id: finding.id, type: finding.type });
                      }}
                      className="text-primary hover:text-primary/80 min-h-[44px] min-w-[44px] inline-flex items-center"
                    >
                      Open finding details
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
