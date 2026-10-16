/**
 * Security Snapshot Panel Component
 * Displays overall security posture and risk level
 */

'use client';

import { SecuritySnapshot } from '@/lib/api/orchestrator';
import clsx from 'clsx';

interface SecuritySnapshotPanelProps {
  snapshot: SecuritySnapshot;
}

export default function SecuritySnapshotPanel({ snapshot }: SecuritySnapshotPanelProps) {
  const { ai_analysis } = snapshot;

  const getPostureColor = (posture: string) => {
    switch (posture.toLowerCase()) {
      case 'good':
        return 'text-green-500';
      case 'needs attention':
        return 'text-yellow-500';
      case 'at risk':
        return 'text-red-500';
      default:
        return 'text-text-muted';
    }
  };

  const getRiskBadgeColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'low':
        return 'bg-green-500/20 text-green-500 border-green-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-500 border-orange-500/30';
      case 'critical':
        return 'bg-red-500/20 text-red-500 border-red-500/30';
      default:
        return 'bg-surface-card text-text-muted border-surface-card-border';
    }
  };

  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-text-main">Security Posture</h2>
        <span className="text-xs text-text-muted">
          Updated {new Date(snapshot.generated_at).toLocaleTimeString()}
        </span>
      </div>

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div>
          <div className="text-sm text-text-muted mb-1">Security Posture</div>
          <div className={`text-3xl font-bold ${getPostureColor(ai_analysis.posture)}`}>
            {ai_analysis.posture}
          </div>
        </div>
        <div>
          <div className="text-sm text-text-muted mb-1">Risk Level</div>
          <span
            className={clsx(
              'inline-block px-4 py-2 rounded-full text-sm font-semibold border',
              getRiskBadgeColor(ai_analysis.risk_level)
            )}
          >
            {ai_analysis.risk_level.toUpperCase()}
          </span>
        </div>
      </div>

      {ai_analysis.summary && (
        <div className="mt-4 p-4 bg-surface-overlay rounded-lg border border-surface-card-border">
          <div className="text-sm font-semibold text-text-main mb-2">Summary</div>
          <p className="text-sm text-text-muted">{ai_analysis.summary}</p>
        </div>
      )}
    </div>
  );
}

