"use client";

import { useMemo, useState } from "react";
import {
  estimateOnboardingScenario,
  type EstimatorCloudProfile,
  type EstimatorEndpointProfile,
  type EstimatorIdentityProfile,
  type EstimatorReportingProfile,
} from "@/lib/marketing/onboardingEstimator";
import { TrackedLink } from "@/components/marketing/TrackedLink";

type OnboardingEstimatorProps = {
  source: string;
  compact?: boolean;
};

export function OnboardingEstimator({
  source,
  compact = false,
}: OnboardingEstimatorProps) {
  const [cloudProfile, setCloudProfile] = useState<EstimatorCloudProfile>("single");
  const [identityProfile, setIdentityProfile] =
    useState<EstimatorIdentityProfile>("microsoft_entra");
  const [endpointProfile, setEndpointProfile] =
    useState<EstimatorEndpointProfile>("none");
  const [reportingProfile, setReportingProfile] =
    useState<EstimatorReportingProfile>("standard");

  const estimate = useMemo(
    () =>
      estimateOnboardingScenario({
        cloudProfile,
        identityProfile,
        endpointProfile,
        reportingProfile,
      }),
    [cloudProfile, identityProfile, endpointProfile, reportingProfile]
  );

  return (
    <section className={`${compact ? "py-0" : "py-20"} px-6`}>
      <div className={`${compact ? "max-w-none" : "max-w-7xl mx-auto"} rounded-[32px] border border-border bg-bg-alt/80 p-8 md:p-10`}>
        <div className="grid gap-8 lg:grid-cols-[0.95fr,1.05fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Onboarding estimator
            </p>
            <h2 className="text-3xl font-semibold tracking-tight text-text-main">
              Estimate setup effort before you book or buy.
            </h2>
            <p className="mt-4 text-sm leading-6 text-text-muted">
              This estimator uses the standard SMB rollout assumptions already reflected in the
              package and onboarding docs. It is meant to set expectations, not to create a second
              pricing model.
            </p>

            <div className="mt-6 space-y-4">
              <div>
                <label htmlFor={`${source}-cloud`} className="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70 mb-2">
                  Cloud scope
                </label>
                <select
                  id={`${source}-cloud`}
                  value={cloudProfile}
                  onChange={(event) => setCloudProfile(event.target.value as EstimatorCloudProfile)}
                  className="w-full rounded-xl border border-border-muted bg-bg/70 px-4 py-3 text-sm text-text-main"
                >
                  <option value="single">One primary AWS or Azure environment</option>
                  <option value="two">Two cloud environments or accounts</option>
                  <option value="three_plus">Three or more environments / custom rollout</option>
                </select>
              </div>

              <div>
                <label htmlFor={`${source}-identity`} className="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70 mb-2">
                  Identity provider
                </label>
                <select
                  id={`${source}-identity`}
                  value={identityProfile}
                  onChange={(event) =>
                    setIdentityProfile(event.target.value as EstimatorIdentityProfile)
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/70 px-4 py-3 text-sm text-text-main"
                >
                  <option value="microsoft_entra">Microsoft 365 / Entra</option>
                  <option value="google_workspace">Google Workspace</option>
                  <option value="okta">Okta</option>
                  <option value="mixed">Mixed identity or not sure yet</option>
                </select>
              </div>

              <div>
                <label htmlFor={`${source}-endpoint`} className="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70 mb-2">
                  Endpoint coverage
                </label>
                <select
                  id={`${source}-endpoint`}
                  value={endpointProfile}
                  onChange={(event) =>
                    setEndpointProfile(event.target.value as EstimatorEndpointProfile)
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/70 px-4 py-3 text-sm text-text-main"
                >
                  <option value="none">No endpoint rollout in the first pass</option>
                  <option value="pilot">Pilot endpoint rollout</option>
                  <option value="full">Broad endpoint rollout now</option>
                </select>
              </div>

              <div>
                <label htmlFor={`${source}-reporting`} className="block text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70 mb-2">
                  Reporting scope
                </label>
                <select
                  id={`${source}-reporting`}
                  value={reportingProfile}
                  onChange={(event) =>
                    setReportingProfile(event.target.value as EstimatorReportingProfile)
                  }
                  className="w-full rounded-xl border border-border-muted bg-bg/70 px-4 py-3 text-sm text-text-main"
                >
                  <option value="standard">Standard reporting and weekly summaries</option>
                  <option value="audit_ready">Audit-ready evidence and compliance exports</option>
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-5">
            <div className="rounded-[28px] border border-cyan-500/20 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    Recommended package
                  </p>
                  <h3 className="mt-2 text-3xl font-semibold text-text-main">
                    {estimate.recommendedPlan.name}
                  </h3>
                </div>
                <span className="rounded-full border border-border-muted bg-bg/40 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text-main/80">
                  {estimate.recommendedPlan.priceLabel}
                </span>
              </div>
              <p className="mt-4 text-sm leading-6 text-text-main/80">
                {estimate.recommendedPlan.subtitle}
              </p>
              <div className="mt-5 grid gap-4 md:grid-cols-2">
                <div className="rounded-2xl border border-border bg-bg/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                    Estimated setup
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-text-main">
                    {estimate.setupWindow}
                  </p>
                </div>
                <div className="rounded-2xl border border-border bg-bg/60 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                    Likely first value
                  </p>
                  <p className="mt-2 text-2xl font-semibold text-text-main">
                    {estimate.firstValueWindow}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-bg/80 p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                Why this estimate looks like this
              </p>
              <div className="mt-4 space-y-3">
                {estimate.rationale.map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-border bg-bg-alt/90 px-4 py-3 text-sm text-text-main/80"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <div className="rounded-xl border border-border bg-bg/80 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                  Standard onboarding included
                </p>
                <ul className="mt-4 space-y-2">
                  {estimate.includedOnboarding.map((item) => (
                    <li key={item} className="flex gap-2 text-sm text-text-muted">
                      <span className="mt-0.5 text-cyan-400">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-xl border border-border bg-bg/80 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                  Assumptions behind the estimate
                </p>
                <ul className="mt-4 space-y-2">
                  {estimate.assumptions.map((item) => (
                    <li key={item} className="flex gap-2 text-sm text-text-muted">
                      <span className="mt-0.5 text-emerald-400">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <TrackedLink
                href={estimate.ctaHref}
                eventName="marketing_pricing_click"
                eventProps={{
                  source,
                  target: estimate.recommendedPath,
                  plan: estimate.recommendedPlanKey,
                }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                {estimate.ctaLabel}
              </TrackedLink>
              <TrackedLink
                href={`/walkthrough?plan=${estimate.recommendedPlanKey}`}
                eventName="marketing_pricing_click"
                eventProps={{ source, target: "walkthrough", plan: estimate.recommendedPlanKey }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Review the walkthrough first
              </TrackedLink>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
