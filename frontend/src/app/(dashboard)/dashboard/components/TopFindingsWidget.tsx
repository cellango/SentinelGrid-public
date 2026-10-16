/**
 * Top Findings Widget Component
 * Displays top security alerts/findings from snapshot
 */

'use client';

import { SecuritySnapshot } from '@/lib/api/orchestrator';
import Link from 'next/link';

interface TopFindingsWidgetProps {
  snapshot: SecuritySnapshot;
}

export default function TopFindingsWidget({ snapshot }: TopFindingsWidgetProps) {
  const { top_findings } = snapshot;

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-500/20 text-red-500 border-red-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-500 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'low':
        return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
      default:
        return 'bg-surface-card text-text-muted border-surface-card-border';
    }
  };

  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-text-main">Top Findings</h2>
        <Link
          href="/dashboard/alerts"
          className="text-sm text-primary hover:text-primary/80"
        >
          View all
        </Link>
      </div>

      {top_findings && top_findings.length > 0 ? (
        <div className="space-y-3">
          {top_findings.slice(0, 5).map((finding) => (
            <Link
              key={finding.id}
              href={`/dashboard/alerts/${finding.id}`}
              className="block p-3 rounded-lg border border-surface-card hover:border-primary/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-text-main">{finding.title}</span>
                <span
                  className={`px-2 py-0.5 text-xs font-semibold rounded border ${getSeverityColor(
                    finding.severity
                  )}`}
                >
                  {finding.severity}
                </span>
              </div>
              {finding.description && (
                <p className="text-xs text-text-muted line-clamp-2 mt-1">{finding.description}</p>
              )}
              {finding.created_at && (
                <p className="text-xs text-text-muted mt-1">
                  {new Date(finding.created_at).toLocaleString()}
                </p>
              )}
            </Link>
          ))}
        </div>
      ) : (
        <p className="text-text-muted text-sm">No findings to display</p>
      )}
    </div>
  );
}

