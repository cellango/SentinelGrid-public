/**
 * Environment Validation Banner
 * Shows "Protected by SentinelGrid" status and validation information
 */

'use client';

import Link from 'next/link';
import type { OnboardingStatus } from '@/lib/api/onboarding';
import { buildOnboardingActivationSummary } from '@/lib/onboarding/activation';
import { getOnboardingIdpMeta, getPreferredOnboardingIdp } from '@/lib/onboarding/idp';
import { recordOnboardingCtaClick } from '@/lib/onboarding/metrics';

interface EnvironmentValidationBannerProps {
  onboardingStatus?: OnboardingStatus | null;
  loading?: boolean;
  hasError?: boolean;
}

export default function EnvironmentValidationBanner({
  onboardingStatus = null,
  loading = false,
  hasError = false,
}: EnvironmentValidationBannerProps) {
  const summary = buildOnboardingActivationSummary(onboardingStatus);
  const idpMeta = getOnboardingIdpMeta(getPreferredOnboardingIdp(onboardingStatus));
  const validationState: 'validating' | 'validated' | 'error' =
    hasError ? 'error' : summary.overallComplete && summary.peopleReady ? 'validated' : 'validating';
  const hoursUntilReports: number | null = summary.coreConnectorsReady ? 3 : null;
  const nextStepLabel = summary.nextStepLabel || 'Continue setup';

  if (loading) {
    return (
      <div className="mb-6 bg-gradient-to-r from-primary/10 to-secondary/10 border border-primary/30 rounded-2xl p-6 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-primary border-t-transparent"></div>
          <span className="text-text-muted">Checking validation status...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`mb-6 rounded-2xl p-6 backdrop-blur-md border transition-all duration-300 ${
        validationState === 'validated'
          ? 'bg-gradient-to-r from-green-500/10 to-emerald-500/10 border-green-500/30'
          : validationState === 'error'
          ? 'bg-gradient-to-r from-red-500/10 to-orange-500/10 border-red-500/30'
          : 'bg-gradient-to-r from-primary/10 to-secondary/10 border-primary/30'
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4 flex-1">
          {/* Icon/Badge */}
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${
              validationState === 'validated'
                ? 'bg-green-500/20 border border-green-500/30'
                : validationState === 'error'
                ? 'bg-red-500/20 border border-red-500/30'
                : 'bg-primary/20 border border-primary/30'
            }`}
          >
            {validationState === 'validated' ? (
              <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : validationState === 'error' ? (
              <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-primary animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            )}
          </div>

          {/* Content */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-semibold text-text-main">Protected by SentinelGrid</h3>
              {validationState === 'validated' && (
                <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs font-semibold rounded-full border border-green-500/30">
                  Validated
                </span>
              )}
            </div>

            {validationState === 'validated' ? (
              <p className="text-text-muted text-sm">
                All systems validated and monitoring active. {hoursUntilReports !== null && (
                  <span className="text-primary font-medium">
                    Expect your first security reports within {hoursUntilReports} {hoursUntilReports === 1 ? 'hour' : 'hours'}.
                  </span>
                )}
              </p>
            ) : validationState === 'error' ? (
              <p className="text-red-400 text-sm">
                Validation encountered an issue. Please check your integrations and try again.
              </p>
            ) : (
              <div className="space-y-2 text-sm text-text-muted">
                <p>
                  Fastest path to first value: connect {idpMeta.shortLabel} and AWS first, then
                  finish endpoint coverage.
                </p>
                {summary.nextStepDescription && (
                  <p className="text-slate-300">
                    Next up: <span className="font-medium text-primary">{nextStepLabel}</span>.{' '}
                    {summary.nextStepDescription}
                  </p>
                )}
                <div className="grid gap-3 pt-1 sm:grid-cols-3">
                  <div className="rounded-xl border border-primary/20 bg-slate-950/40 px-3 py-2">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-primary">Checklist</p>
                    <p className="mt-1 text-sm text-text-main">
                      {summary.completedSteps}/{summary.totalSteps || 1} complete
                    </p>
                  </div>
                  <div className="rounded-xl border border-primary/20 bg-slate-950/40 px-3 py-2">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-primary">Next step</p>
                    <p className="mt-1 text-sm text-text-main">{nextStepLabel}</p>
                  </div>
                  <div className="rounded-xl border border-primary/20 bg-slate-950/40 px-3 py-2">
                    <p className="text-[11px] uppercase tracking-[0.14em] text-primary">First value</p>
                    <p className="mt-1 text-sm text-text-main">
                      {summary.coreConnectorsReady ? 'Core connectors live' : `After AWS + ${idpMeta.shortLabel}`}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Action Button */}
        {validationState !== 'validated' && (
          <Link
            href={summary.targetHref}
            onClick={() =>
              recordOnboardingCtaClick({
                source: 'welcome_validation_banner',
                target: summary.targetHref,
                stepId: summary.nextStepId,
              })
            }
            className="px-4 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30 whitespace-nowrap"
          >
            Continue {nextStepLabel}
          </Link>
        )}
      </div>
    </div>
  );
}
