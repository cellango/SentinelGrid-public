'use client';

import React from 'react';
import clsx from 'clsx';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  defaultMarketingPlanKey,
  isMarketingPlanKey,
  marketingPlans,
  type MarketingPlanKey,
} from '@/lib/marketing/packages';

export function PlanTierSelector() {
  const { planTier, setPlanTierOverride } = useAuth();
  const storedOverride =
    typeof window !== 'undefined' ? localStorage.getItem('plan_tier_override') : null;
  const active = isMarketingPlanKey(storedOverride)
    ? storedOverride
    : isMarketingPlanKey(planTier)
      ? planTier
      : defaultMarketingPlanKey;

  // If the backend provided a plan and no override is set, don't prompt the user to choose again.
  if (planTier && !storedOverride) {
    return null;
  }

  return (
    <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
      <div className="flex items-center justify-between mb-3 gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.12em] text-cyan-300/80">Plan</p>
          <h3 className="text-lg font-semibold text-slate-100">Choose your package</h3>
          <p className="text-sm text-slate-400">
            Applies instantly for UI gating; contact us to change billing.
          </p>
        </div>
        {storedOverride && (
          <button
            className="text-xs px-3 py-1 rounded-full border border-slate-700 text-slate-300 hover:border-cyan-400"
            onClick={() => setPlanTierOverride(null)}
          >
            Clear override
          </button>
        )}
      </div>
      <div className="grid md:grid-cols-3 gap-3">
        {marketingPlans.map((plan) => {
          const selected = active === plan.key;
          return (
            <button
              key={plan.key}
              onClick={() => setPlanTierOverride(plan.key as MarketingPlanKey)}
              className={clsx(
                'relative text-left rounded-xl border-2 p-4 transition-all',
                selected
                  ? 'border-cyan-500 bg-cyan-500/10 shadow-lg shadow-cyan-500/20'
                  : 'border-slate-800 bg-slate-900/40 hover:border-cyan-500/60'
              )}
            >
              {plan.badge && (
                <span className="absolute -top-3 right-3 text-[10px] px-2 py-1 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold">
                  {plan.badge}
                </span>
              )}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-100">{plan.name}</p>
                  <p className="text-xs text-slate-400">{plan.subtitle}</p>
                  <p className="mt-2 text-[11px] font-medium uppercase tracking-[0.14em] text-cyan-300">
                    {plan.priceLabel}
                  </p>
                </div>
                {selected && (
                  <span className="text-xs px-2 py-1 rounded-full bg-cyan-500/20 text-cyan-200 border border-cyan-500/40">
                    Active
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
