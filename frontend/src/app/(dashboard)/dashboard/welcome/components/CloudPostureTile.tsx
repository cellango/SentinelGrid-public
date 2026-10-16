/**
 * Cloud & Posture Snapshot Tile
 * Shows cloud security posture summary
 */

'use client';

import Link from 'next/link';
import { CloudPostureSnapshot } from '@/lib/api/dashboard';

interface CloudPostureTileProps {
  cloudPosture: CloudPostureSnapshot;
}

export default function CloudPostureTile({ cloudPosture }: CloudPostureTileProps) {
  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 hover:border-primary/40 transition-all">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-text-main mb-1">Cloud Security</h3>
        <p className="text-sm text-text-muted">
          {cloudPosture.cloud_accounts_connected} {cloudPosture.cloud_accounts_connected === 1 ? 'account' : 'accounts'} connected
        </p>
      </div>

      <div className="space-y-3 mb-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-muted">Critical issues</span>
          <span className="text-lg font-bold text-red-400">{cloudPosture.critical_misconfigs}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-muted">High issues</span>
          <span className="text-lg font-bold text-orange-400">{cloudPosture.high_misconfigs}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-text-muted">Total issues</span>
          <span className="text-lg font-bold text-text-main">{cloudPosture.total_issues}</span>
        </div>
      </div>

      {cloudPosture.biggest_risk && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-3 mb-4">
          <p className="text-xs font-medium text-red-400 mb-1">Biggest Risk</p>
          <p className="text-sm text-text-main">{cloudPosture.biggest_risk.title}</p>
          <p className="text-xs text-text-muted mt-1">{cloudPosture.biggest_risk.description}</p>
        </div>
      )}

      <div className="flex gap-2">
        <Link
          href="/dashboard/compliance"
          className="flex-1 px-3 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30 text-center"
        >
          View Posture
        </Link>
        {cloudPosture.critical_misconfigs > 0 && (
          <button className="flex-1 px-3 py-2 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-xl hover:brightness-110 transition-all text-sm font-medium">
            Fix Top Issue
          </button>
        )}
      </div>
    </div>
  );
}

