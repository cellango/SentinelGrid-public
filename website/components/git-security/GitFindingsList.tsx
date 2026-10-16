'use client';

import React, { useState, useEffect } from 'react';
import { GitFinding, listFindings, updateFindingStatus } from '@/lib/api/git-scanning';

interface GitFindingsListProps {
  repoId?: string;
  onFindingSelect?: (finding: GitFinding) => void;
}

export default function GitFindingsList({
  repoId,
  onFindingSelect,
}: GitFindingsListProps) {
  const [findings, setFindings] = useState<GitFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({
    finding_type: '',
    severity: '',
    status: 'open',
  });

  useEffect(() => {
    fetchFindings();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repoId, page, filters]);

  async function fetchFindings() {
    try {
      setLoading(true);
      setError(null);
      const response = await listFindings(
        {
          repo_id: repoId,
          finding_type: filters.finding_type || undefined,
          severity: filters.severity || undefined,
          status: filters.status || undefined,
        },
        page,
        20
      );
      setFindings(response.findings);
      setTotal(response.total);
    } catch (err: any) {
      console.error('Error fetching findings:', err);
      setError(err.message || 'Failed to load findings');
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusUpdate(findingId: string, newStatus: string) {
    try {
      await updateFindingStatus(findingId, newStatus as any);
      // Refresh findings
      fetchFindings();
    } catch (err: any) {
      console.error('Error updating finding status:', err);
      alert(`Failed to update finding: ${err.message}`);
    }
  }

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-600',
      high: 'bg-orange-600',
      medium: 'bg-yellow-600',
      low: 'bg-blue-600',
      info: 'bg-gray-600',
    };
    return colors[severity] || 'bg-gray-600';
  };

  const getFindingTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      secret: '🔑',
      vulnerability: '⚠️',
      code_issue: '🐛',
      dependency_vulnerability: '📦',
    };
    return icons[type] || '📄';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading findings...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
        <button
          onClick={fetchFindings}
          className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-xs text-gray-600 mb-1">Finding Type</label>
          <select
            value={filters.finding_type}
            onChange={(e) => setFilters({ ...filters, finding_type: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All Types</option>
            <option value="secret">Secrets</option>
            <option value="vulnerability">Vulnerabilities</option>
            <option value="code_issue">Code Issues</option>
            <option value="dependency_vulnerability">Dependency Vulnerabilities</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs text-gray-600 mb-1">Severity</label>
          <select
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
            <option value="info">Info</option>
          </select>
        </div>
        <div className="flex-1">
          <label className="block text-xs text-gray-600 mb-1">Status</label>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="false_positive">False Positive</option>
            <option value="ignored">Ignored</option>
          </select>
        </div>
      </div>

      {/* Findings List */}
      {findings.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600">No findings found</p>
        </div>
      ) : (
        <div className="space-y-3">
          {findings.map((finding) => (
            <div
              key={finding.id}
              onClick={() => onFindingSelect?.(finding)}
              className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-xl">{getFindingTypeIcon(finding.finding_type)}</span>
                    <h4 className="font-semibold text-gray-900">{finding.title}</h4>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium text-white ${getSeverityColor(
                        finding.severity
                      )}`}
                    >
                      {finding.severity.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-500">
                      {finding.scanner_tool}
                    </span>
                  </div>
                  
                  {finding.description && (
                    <p className="text-sm text-gray-600 mb-2">{finding.description}</p>
                  )}
                  
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    {finding.file_path && (
                      <span>
                        📁 {finding.file_path}
                        {finding.line_number && `:${finding.line_number}`}
                      </span>
                    )}
                    {finding.commit_sha && (
                      <span>🔀 {finding.commit_sha.substring(0, 7)}</span>
                    )}
                    <span>🕒 {new Date(finding.detected_at).toLocaleDateString()}</span>
                  </div>
                </div>
                
                <div className="ml-4">
                  <select
                    value={finding.status}
                    onChange={(e) => handleStatusUpdate(finding.id, e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs border border-gray-300 rounded px-2 py-1"
                  >
                    <option value="open">Open</option>
                    <option value="resolved">Resolved</option>
                    <option value="false_positive">False Positive</option>
                    <option value="ignored">Ignored</option>
                  </select>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between pt-4 border-t">
          <div className="text-sm text-gray-600">
            Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, total)} of {total} findings
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page * 20 >= total}
              className="px-3 py-1 text-sm border border-gray-300 rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
