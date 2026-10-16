"use client";

import { useMemo, useState } from "react";
import {
  defaultRoiInputs,
  estimateRoi,
  type RoiInputs,
} from "@/lib/marketing/roi";
import {
  aiShieldAddon,
  marketingPlans,
  type MarketingPlanKey,
} from "@/lib/marketing/packages";
import { TrackedLink } from "@/components/marketing/TrackedLink";

type RoiCalculatorProps = {
  source: string;
  compact?: boolean;
};

function currency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function signedCurrency(value: number) {
  const prefix = value >= 0 ? "" : "-";
  return `${prefix}${currency(Math.abs(value))}`;
}

function wholePercent(value: number) {
  return `${Math.round(value)}%`;
}

export function RoiCalculator({ source, compact = false }: RoiCalculatorProps) {
  const [inputs, setInputs] = useState<RoiInputs>(defaultRoiInputs);

  const estimate = useMemo(() => estimateRoi(inputs), [inputs]);

  const sectionPadding = compact ? "py-0" : "py-20";

  return (
    <section className={`${sectionPadding} px-6`}>
      <div
        className={`${compact ? "max-w-none" : "max-w-7xl mx-auto"} rounded-[32px] border border-border bg-bg-alt/80 p-8 md:p-10`}
      >
        <div className="grid gap-8 lg:grid-cols-[0.95fr,1.05fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              ROI model
            </p>
            <h2 className="text-3xl font-semibold tracking-tight text-text-main">
              Compare point-tool spend and operating drag against one package.
            </h2>
            <p className="mt-4 text-sm leading-6 text-text-muted">
              This model is intentionally simple. It lets a buyer or seller compare current point-tool
              spend, operator overhead, and external reporting cost against the current SentinelGrid
              package model with explicit assumptions.
            </p>

            <div className="mt-6 grid gap-4">
              <div>
                <label
                  htmlFor={`${source}-current-tools`}
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70"
                >
                  Current number of security tools
                </label>
                <input
                  id={`${source}-current-tools`}
                  type="number"
                  min={1}
                  value={inputs.currentTools}
                  onChange={(event) =>
                    setInputs((current) => ({
                      ...current,
                      currentTools: Number(event.target.value) || 1,
                    }))
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
                />
              </div>

              <div>
                <label
                  htmlFor={`${source}-monthly-spend`}
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70"
                >
                  Current monthly security-tool spend
                </label>
                <input
                  id={`${source}-monthly-spend`}
                  type="number"
                  min={0}
                  step={50}
                  value={inputs.currentMonthlySpend}
                  onChange={(event) =>
                    setInputs((current) => ({
                      ...current,
                      currentMonthlySpend: Number(event.target.value) || 0,
                    }))
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
                />
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label
                    htmlFor={`${source}-operator-hours`}
                    className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70"
                  >
                    Monthly hours spent across triage, handoffs, and reporting
                  </label>
                  <input
                    id={`${source}-operator-hours`}
                    type="number"
                    min={0}
                    step={1}
                    value={inputs.monthlyOperatorHours}
                    onChange={(event) =>
                      setInputs((current) => ({
                        ...current,
                        monthlyOperatorHours: Number(event.target.value) || 0,
                      }))
                    }
                    className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
                  />
                </div>
                <div>
                  <label
                    htmlFor={`${source}-hourly-rate`}
                    className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70"
                  >
                    Loaded hourly rate for the primary operator
                  </label>
                  <input
                    id={`${source}-hourly-rate`}
                    type="number"
                    min={0}
                    step={5}
                    value={inputs.operatorHourlyRate}
                    onChange={(event) =>
                      setInputs((current) => ({
                        ...current,
                        operatorHourlyRate: Number(event.target.value) || 0,
                      }))
                    }
                    className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor={`${source}-external-cost`}
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70"
                >
                  Monthly external reporting, evidence, or consulting cost
                </label>
                <input
                  id={`${source}-external-cost`}
                  type="number"
                  min={0}
                  step={50}
                  value={inputs.externalReportingMonthlyCost}
                  onChange={(event) =>
                    setInputs((current) => ({
                      ...current,
                      externalReportingMonthlyCost: Number(event.target.value) || 0,
                    }))
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
                />
              </div>

              <div>
                <label
                  htmlFor={`${source}-target-plan`}
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70"
                >
                  Target SentinelGrid package
                </label>
                <select
                  id={`${source}-target-plan`}
                  value={inputs.targetPlan}
                  onChange={(event) =>
                    setInputs((current) => ({
                      ...current,
                      targetPlan: event.target.value as MarketingPlanKey,
                    }))
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/60 px-4 py-3 text-text-main"
                >
                  {marketingPlans.map((plan) => (
                    <option key={plan.key} value={plan.key}>
                      {plan.name}
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex items-start gap-3 rounded-2xl border border-border bg-bg/80 px-4 py-4 text-sm text-text-main/80">
                <input
                  type="checkbox"
                  checked={inputs.includeAiShield}
                  onChange={(event) =>
                    setInputs((current) => ({
                      ...current,
                      includeAiShield: event.target.checked,
                    }))
                  }
                  className="mt-1"
                />
                <span>
                  Include <span className="font-medium text-text-main">{aiShieldAddon.name}</span> at{" "}
                  {aiShieldAddon.priceLabel.toLowerCase()} in the comparison.
                </span>
              </label>
            </div>
          </div>

          <div className="space-y-5">
            <div className="rounded-[28px] border border-cyan-500/20 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 p-6">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    Estimated annual delta
                  </p>
                  <h3 className="mt-2 text-3xl font-semibold text-text-main">
                    {signedCurrency(estimate.annualSavings)}
                  </h3>
                </div>
                <span className="rounded-full border border-border-muted bg-bg/40 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text-main/80">
                  {wholePercent(estimate.savingsPercent)} modeled change
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-text-main/80">
                Compared with the current inputs, moving to <span className="font-medium text-text-main">{estimate.packageName}</span> is
                modeled to recover about <span className="font-medium text-text-main">{Math.round(estimate.recoveredHoursPerMonth)} hours per month</span> of coordination and reporting overhead.
              </p>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-bg/80 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                  Current model
                </p>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex items-center justify-between gap-4 text-text-muted">
                    <span>Tool spend</span>
                    <span className="font-medium text-text-main">
                      {currency(estimate.currentAnnualToolSpend)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-text-muted">
                    <span>Operator overhead</span>
                    <span className="font-medium text-text-main">
                      {currency(estimate.currentAnnualOperatorCost)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-text-muted">
                    <span>External reporting cost</span>
                    <span className="font-medium text-text-main">
                      {currency(estimate.currentAnnualExternalCost)}
                    </span>
                  </div>
                  <div className="border-t border-border pt-3 flex items-center justify-between gap-4 text-text-main/80">
                    <span>Estimated annual total</span>
                    <span className="text-lg font-semibold text-text-main">
                      {currency(estimate.currentAnnualTotal)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-bg/80 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                  SentinelGrid model
                </p>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex items-center justify-between gap-4 text-text-muted">
                    <span>Subscription cost</span>
                    <span className="font-medium text-text-main">
                      {currency(estimate.sentinelGridAnnualSubscription)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-text-muted">
                    <span>Remaining operator overhead</span>
                    <span className="font-medium text-text-main">
                      {currency(estimate.sentinelGridAnnualOperatorCost)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4 text-text-muted">
                    <span>Package modeled</span>
                    <span className="font-medium text-text-main">{estimate.packageName}</span>
                  </div>
                  <div className="border-t border-border pt-3 flex items-center justify-between gap-4 text-text-main/80">
                    <span>Estimated annual total</span>
                    <span className="text-lg font-semibold text-text-main">
                      {currency(estimate.sentinelGridAnnualTotal)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-bg/80 p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                Assumptions behind this model
              </p>
              <ul className="mt-4 space-y-3">
                {estimate.assumptions.map((item) => (
                  <li key={item} className="flex gap-3 text-sm leading-6 text-text-muted">
                    <span className="mt-0.5 text-cyan-400">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href="/pricing"
                eventName="marketing_nav_click"
                eventProps={{ source, target: "pricing" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Review package pricing
              </TrackedLink>
              <TrackedLink
                href={`/demo?plan=${inputs.targetPlan}`}
                eventName="marketing_cta_click"
                eventProps={{
                  source,
                  target: "demo",
                  plan: inputs.targetPlan,
                  include_ai_shield: inputs.includeAiShield,
                }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Book a pricing review
              </TrackedLink>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
