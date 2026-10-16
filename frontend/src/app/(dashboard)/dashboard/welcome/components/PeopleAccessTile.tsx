/**
 * People & Access Snapshot Tile
 * Shows identity and access management summary
 */

'use client';

import Link from 'next/link';
import { PeopleAccessSnapshot } from '@/lib/api/dashboard';

interface PeopleAccessTileProps {
  peopleAccess: PeopleAccessSnapshot;
}

export default function PeopleAccessTile({ peopleAccess }: PeopleAccessTileProps) {
  const mfaPercentage = Math.round(peopleAccess.mfa_coverage_percent);

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 hover:border-primary/40 transition-all">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-text-main mb-1">People & Access</h3>
        <p className="text-sm text-text-muted">
          {peopleAccess.users_total} users • {peopleAccess.users_admins} admins
        </p>
      </div>

      <div className="space-y-3 mb-4">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-muted">MFA Coverage</span>
            <span className={`text-sm font-semibold ${mfaPercentage >= 80 ? 'text-green-400' : mfaPercentage >= 60 ? 'text-yellow-400' : 'text-red-400'}`}>
              {mfaPercentage}%
            </span>
          </div>
          <div className="h-2 bg-[rgba(15,23,42,0.9)] rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                mfaPercentage >= 80
                  ? 'bg-green-500/20 border-green-500/30'
                  : mfaPercentage >= 60
                  ? 'bg-yellow-500/20 border-yellow-500/30'
                  : 'bg-red-500/20 border-red-500/30'
              }`}
              style={{ width: `${mfaPercentage}%` }}
            />
          </div>
          {peopleAccess.mfa_missing_count > 0 && (
            <p className="text-xs text-text-muted mt-1">
              {peopleAccess.mfa_missing_count} {peopleAccess.mfa_missing_count === 1 ? 'user' : 'users'} missing MFA
            </p>
          )}
        </div>

        {peopleAccess.dormant_accounts_count > 0 && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-muted">Dormant accounts</span>
            <span className="text-sm font-semibold text-yellow-400">
              {peopleAccess.dormant_accounts_count}
            </span>
          </div>
        )}
      </div>

      {peopleAccess.fast_win && (
        <div className="bg-primary/10 border border-primary/20 rounded-xl p-3 mb-4">
          <p className="text-xs font-medium text-primary mb-1">Fast Win</p>
          <p className="text-sm text-text-main">{peopleAccess.fast_win.title}</p>
        </div>
      )}

      <div className="flex gap-2">
        <Link
          href="/dashboard/iam/people"
          className="flex-1 px-3 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30 text-center"
        >
          Manage People
        </Link>
        {peopleAccess.mfa_missing_count > 0 && (
          <button className="flex-1 px-3 py-2 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-xl hover:brightness-110 transition-all text-sm font-medium">
            Fix MFA
          </button>
        )}
      </div>
    </div>
  );
}

