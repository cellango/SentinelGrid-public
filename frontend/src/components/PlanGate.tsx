'use client';

import React from 'react';
import { useAuth } from '@/lib/providers/AuthProvider';
import Link from 'next/link';
import { getPlanTierRank, type PlanTier } from '@/lib/product/catalog';

type Props = {
  requiredTier?: PlanTier;
  title?: string;
  description?: string;
  ctaHref?: string;
  ctaLabel?: string;
  children: React.ReactNode;
};

export function PlanGate({
  requiredTier = 'protect_defend_comply',
  title = 'Upgrade to access this area',
  description = 'Upgrade to the right plan to unlock this area.',
  ctaHref = '/#plans',
  ctaLabel = 'View plans',
  children,
}: Props) {
  const { planTier } = useAuth();
  const override =
    typeof window !== 'undefined'
      ? localStorage.getItem('plan_tier_override') || localStorage.getItem('plan_tier')
      : null;
  const allowed = getPlanTierRank(override || planTier) >= getPlanTierRank(requiredTier);

  if (allowed) return <>{children}</>;

  return (
    <div className="p-6">
      <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-6 max-w-3xl">
        <h2 className="text-2xl font-semibold text-amber-100 mb-2">{title}</h2>
        <p className="text-amber-50/80 text-sm mb-4">{description}</p>
        <div className="flex gap-3">
          <Link
            href={ctaHref}
            className="px-4 py-2 rounded-full bg-cyan-400 text-slate-900 text-sm font-semibold hover:bg-cyan-300"
          >
            {ctaLabel}
          </Link>
          <a
            href="mailto:sales@sentinelgrid.ai?subject=Enable%20Comply%20tier"
            className="px-4 py-2 rounded-full border border-amber-400 text-amber-100 text-sm font-semibold hover:border-amber-300"
          >
            Talk to us
          </a>
        </div>
      </div>
    </div>
  );
}
