/**
 * Compliance Progress Component
 * Shows compliance readiness and progress
 */

'use client';

import Link from 'next/link';
import { planIncludesCompliance, type PlanTier } from '@/lib/product/catalog';

interface ComplianceProgressProps {
  complianceReadiness?: number; // 0-100
  packageType?: PlanTier;
}

export default function ComplianceProgress({ complianceReadiness = 0, packageType = 'protect' }: ComplianceProgressProps) {
  if (!planIncludesCompliance(packageType)) {
    return (
      <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
        <h3 className="text-lg font-semibold text-text-main mb-2">Compliance</h3>
        <p className="text-sm text-text-muted mb-4">
          Upgrade to Protect + Defend + Comply to track compliance readiness and generate reports.
        </p>
        <Link
          href="/dashboard/settings/billing"
          className="inline-block px-4 py-2 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-xl hover:brightness-110 transition-all text-sm font-medium"
        >
          Upgrade Plan
        </Link>
      </div>
    );
  }

  const getReadinessColor = (percent: number) => {
    if (percent >= 80) return 'text-green-400';
    if (percent >= 60) return 'text-yellow-400';
    if (percent >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  const getReadinessBgColor = (percent: number) => {
    if (percent >= 80) return 'bg-green-500/20 border-green-500/30';
    if (percent >= 60) return 'bg-yellow-500/20 border-yellow-500/30';
    if (percent >= 40) return 'bg-orange-500/20 border-orange-500/30';
    return 'bg-red-500/20 border-red-500/30';
  };

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-main">Compliance Status</h3>
        <Link
          href="/dashboard/compliance"
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          View details →
        </Link>
      </div>

      <div className="mb-4">
        <div className="flex items-baseline gap-2 mb-2">
          <span className={`text-3xl font-bold ${getReadinessColor(complianceReadiness)}`}>
            {complianceReadiness}%
          </span>
          <span className="text-text-muted">Complete</span>
        </div>
        <div className="h-3 bg-[rgba(15,23,42,0.9)] rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${getReadinessBgColor(complianceReadiness)}`}
            style={{ width: `${complianceReadiness}%` }}
          />
        </div>
      </div>

      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-text-muted">IAM Controls</span>
          <span className="text-text-main font-medium">60%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-text-muted">Logging & Monitoring</span>
          <span className="text-text-main font-medium">40%</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-text-muted">Change Management</span>
          <span className="text-text-main font-medium">30%</span>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-primary/10">
        <p className="text-xs text-text-muted mb-2">
          Finish these three items to bring IAM closer to compliance expectations.
        </p>
        <Link
          href="/dashboard/compliance"
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          View compliance map →
        </Link>
      </div>
    </div>
  );
}
