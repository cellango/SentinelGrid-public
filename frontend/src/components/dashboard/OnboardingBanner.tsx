'use client';

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { getOnboardingStatus, OnboardingStatus } from '@/lib/api/onboarding';
import { enableDetectionRules } from '@/lib/api/onboarding';
import { loadSampleLogs } from '@/lib/api/siem';
import { buildOnboardingActivationSummary } from '@/lib/onboarding/activation';
import { getOnboardingIdpMeta, getPreferredOnboardingIdp } from '@/lib/onboarding/idp';
import {
  recordOnboardingBannerDismissed,
  recordOnboardingCtaClick,
  syncOnboardingMetricsFromStatus,
} from '@/lib/onboarding/metrics';
import { isPeopleReady } from '@/lib/onboarding/steps';
import { useAuth } from '@/lib/providers/AuthProvider';
import { toast } from 'react-hot-toast';

export default function OnboardingBanner() {
  const { tenantId } = useAuth();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);
  const [loadingSamples, setLoadingSamples] = useState(false);
  const [enablingRules, setEnablingRules] = useState(false);

  useEffect(() => {
    async function loadStatus() {
      try {
        const onboardingStatus = await getOnboardingStatus();
        setStatus(onboardingStatus);
        syncOnboardingMetricsFromStatus(onboardingStatus);

        // Check if user dismissed banner
        const version = onboardingStatus.status_version || `${onboardingStatus.onboarding_completed}_${onboardingStatus.last_incomplete_step_id || 'none'}_${onboardingStatus.access_profile_ready ? 'ap1' : 'ap0'}_${onboardingStatus.birthright_ready ? 'br1' : 'br0'}`;
        const dismissedKey = `onboarding_banner_dismissed_${version}`;
        const isDismissed = localStorage.getItem(dismissedKey) === 'true';
        setDismissed(isDismissed);
      } catch (error) {
        console.error('Error loading onboarding status:', error);
      } finally {
        setLoading(false);
      }
    }

    loadStatus();
  }, []);

  const handleDismiss = () => {
    if (status) {
      const version = status.status_version || `${status.onboarding_completed}_${status.last_incomplete_step_id || 'none'}_${status.access_profile_ready ? 'ap1' : 'ap0'}_${status.birthright_ready ? 'br1' : 'br0'}`;
      const dismissedKey = `onboarding_banner_dismissed_${version}`;
      localStorage.setItem(dismissedKey, 'true');
      recordOnboardingBannerDismissed({
        source: 'dashboard_banner',
        progressPct: summary.progressPct,
      });
      setDismissed(true);
    }
  };

  const [dismissedAnnouncements, setDismissedAnnouncements] = useState<Set<string>>(new Set());

  const dismissAnnouncement = (id: string) => {
    if (!status) return;
    const version = status.status_version || 'v0';
    const key = `announcement_${id}_${version}`;
    localStorage.setItem(key, 'true');
    setDismissedAnnouncements((prev) => new Set(prev).add(id));
  };

  const announcements = useMemo(() => {
    if (!status?.announcements) return [];
    const version = status.status_version || 'v0';
    return status.announcements.filter((a) => {
      const key = `announcement_${a.id}_${version}`;
      return localStorage.getItem(key) !== 'true' && !dismissedAnnouncements.has(a.id);
    });
  }, [status?.announcements, status?.status_version, dismissedAnnouncements]);

  const summary = useMemo(() => buildOnboardingActivationSummary(status), [status]);
  const preferredIdp = getPreferredOnboardingIdp(status);
  const idpMeta = getOnboardingIdpMeta(preferredIdp);

  const servicesSelected = status?.services_selected || {};
  const trustProfile = status?.trust_profile || servicesSelected?.trustProfile;
  const trustEnabled = trustProfile?.enabled === true;
  const trustFrameworks = Array.isArray(trustProfile?.frameworks) ? trustProfile.frameworks : [];
  const trustDriver = trustProfile?.primaryDriver as string | undefined;
  const trustTimeline = trustProfile?.targetTimeline as string | undefined;

  const formatTrustLabel = (value?: string) => {
    if (!value) return null;
    const labels: Record<string, string> = {
      soc2: 'SOC 2',
      hipaa: 'HIPAA',
      pci_dss: 'PCI DSS',
      iso27001: 'ISO 27001',
      customer_questionnaires: 'Customer questionnaires',
      audit: 'formal audit',
      customer_security_review: 'customer security review',
      renewal_pressure: 'renewal or procurement pressure',
      board_reporting: 'board or leadership reporting',
      exploratory: 'exploratory planning',
      '30_days': 'next 30 days',
      '60_days': 'next 60 days',
      '90_days': 'next 90 days',
      this_quarter: 'this quarter',
    };
    return labels[value] || value.replace(/_/g, ' ');
  };

  const overallComplete = status?.overall_complete ?? status?.onboarding_completed;
  const peopleReady = isPeopleReady(status);

  // Calculate progress
  const totalSteps = summary.totalSteps || 1;
  const completedSteps = summary.completedSteps;
  const progress = summary.progressPct;
  const coverageProgressLabel = `${completedSteps} of ${totalSteps} integrations connected`;

  if (loading || !status || dismissed || (overallComplete && peopleReady)) {
    return null;
  }

  const handleLoadSamples = async () => {
    setLoadingSamples(true);
    try {
      await Promise.all([
        loadSampleLogs('auth'),
        loadSampleLogs('cloud'),
        loadSampleLogs('endpoint'),
      ]);
      toast.success('Loaded sample identity, cloud, and endpoint telemetry.');
    } catch (error: any) {
      toast.error(error?.message || 'Failed to load sample telemetry.');
    } finally {
      setLoadingSamples(false);
    }
  };

  const handleEnableQuickStart = async () => {
    if (!tenantId) {
      toast.error('No tenant is selected for quick-start detections.');
      return;
    }
    setEnablingRules(true);
    try {
      const result = await enableDetectionRules({
        tenant_id: tenantId,
        rule_keys: ['failed_logins', 'new_admin', 'suspicious_cloud'],
      });
      toast.success(`Enabled ${result.rules_enabled.length} quick-start detection rules.`);
    } catch (error: any) {
      toast.error(error?.message || 'Failed to enable quick-start detections.');
    } finally {
      setEnablingRules(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-xl p-4 md:p-6 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🚀</span>
            <h3 className="text-lg font-semibold text-cyan-300">First-Run Checklist</h3>
          </div>
          <p className="text-sm text-slate-300 mb-4">
            Fastest path to first value: connect {idpMeta.shortLabel}, then AWS, then finish endpoint coverage.
            {completedSteps > 0 && (
              <span className="ml-2 text-cyan-400">
                {completedSteps} of {totalSteps} steps completed ({progress}%)
              </span>
            )}
          </p>

          <div className="mb-4 rounded-xl border border-cyan-500/20 bg-slate-950/40 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.14em] text-cyan-300">Current next step</p>
                <p className="mt-1 text-sm font-semibold text-slate-100">
                  {summary.nextStepLabel || 'Continue setup'}
                </p>
                {summary.nextStepDescription && (
                  <p className="mt-1 text-sm text-slate-300">{summary.nextStepDescription}</p>
                )}
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className={`rounded-full border px-3 py-1 ${status?.idp_connected ? 'border-green-500/40 text-green-300' : 'border-cyan-500/40 text-cyan-300'}`}>
                  {idpMeta.shortLabel} {status?.idp_connected ? 'connected' : 'recommended'}
                </span>
                <span className={`rounded-full border px-3 py-1 ${status?.cloud_connected ? 'border-green-500/40 text-green-300' : 'border-cyan-500/40 text-cyan-300'}`}>
                  AWS {status?.cloud_connected ? 'connected' : 'recommended'}
                </span>
                <span className={`rounded-full border px-3 py-1 ${summary.coreConnectorsReady ? 'border-green-500/40 text-green-300' : 'border-slate-700 text-slate-300'}`}>
                  {summary.coreConnectorsReady ? 'First findings unlocked' : 'First findings after core connectors'}
                </span>
                {trustEnabled && (
                  <span className="rounded-full border border-violet-500/40 px-3 py-1 text-violet-200">
                    Trust workflow enabled
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="mb-4">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-400">
              <span>{coverageProgressLabel}</span>
              <span>{progress}% coverage</span>
            </div>
            <div className="flex gap-1 mb-2">
              {summary.items.map((item, idx) => (
                <div
                  key={idx}
                  className={`flex-1 h-2 rounded ${
                    item.done
                      ? 'bg-green-500'
                      : idx <= completedSteps
                      ? 'bg-cyan-500'
                      : 'bg-slate-700'
                  }`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              {summary.items.map((item) => (
                <span key={item.id} className="capitalize">
                  {item.label}
                </span>
              ))}
            </div>
          </div>

          <div className="mb-4 rounded-xl border border-primary/15 bg-slate-950/45 p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">First-value shortcuts</p>
                <p className="mt-1 text-sm font-semibold text-slate-100">
                  See a populated queue before every connector is ready
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  Load sample telemetry to preview how the queue behaves, then enable the top quick-start detections for login abuse, new admins, and suspicious cloud activity.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleLoadSamples}
                  disabled={loadingSamples}
                  className="inline-flex min-h-[44px] items-center justify-center rounded-full border border-border-strong px-4 py-2 text-sm font-medium text-slate-100 transition-colors hover:border-primary disabled:opacity-60"
                >
                  {loadingSamples ? 'Loading samples…' : 'Load sample telemetry'}
                </button>
                <button
                  type="button"
                  onClick={handleEnableQuickStart}
                  disabled={enablingRules || !tenantId}
                  className="inline-flex min-h-[44px] items-center justify-center rounded-full bg-primary px-4 py-2 text-sm font-semibold text-slate-950 transition-all hover:brightness-110 disabled:opacity-60"
                >
                  {enablingRules ? 'Enabling detections…' : 'Enable quick-start detections'}
                </button>
              </div>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-3 mb-4">
            {summary.pendingItems.slice(0, 3).map((item) => (
              <div key={item.id} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-100">{item.label}</p>
                  {item.recommended && (
                    <span className="rounded-full border border-cyan-500/30 px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-cyan-300">
                      Recommended
                    </span>
                  )}
                </div>
                <p className="mt-2 text-xs leading-5 text-slate-300">{item.description}</p>
              </div>
            ))}
          </div>

          {trustEnabled && (
            <div className="mb-4 rounded-xl border border-violet-500/20 bg-violet-500/5 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.14em] text-violet-300">Trust profile</p>
                  <p className="mt-1 text-sm font-semibold text-slate-100">
                    {trustFrameworks.length > 0
                      ? `Focused on ${trustFrameworks
                          .map((item: string) => formatTrustLabel(item))
                          .filter(Boolean)
                          .join(', ')}`
                      : 'Define the frameworks that matter first'}
                  </p>
                  <p className="mt-1 text-sm text-slate-300">
                    {trustDriver
                      ? `Primary driver: ${formatTrustLabel(trustDriver)}`
                      : 'Capture whether this is for an audit, customer review, or another trust motion.'}
                    {trustTimeline ? ` Target timeline: ${formatTrustLabel(trustTimeline)}.` : ''}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link
                    href="/dashboard/compliance"
                    className="inline-flex items-center justify-center rounded-full border border-violet-500/30 px-4 py-2 text-sm font-medium text-violet-200 hover:border-violet-400 hover:text-violet-100"
                  >
                    Open compliance
                  </Link>
                  <Link
                    href="/dashboard/compliance/reports"
                    className="inline-flex items-center justify-center rounded-full border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:border-violet-400"
                  >
                    Reporting
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Announcements */}
          {announcements.length > 0 && (
            <div className="space-y-2 mb-4">
              {announcements.map((a) => (
                <div key={a.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2">
                  <div>
                    <div className="text-sm font-semibold text-slate-100">{a.title || 'Notice'}</div>
                    <div className="text-xs text-slate-300">{a.body}</div>
                  </div>
                  <button
                    className="text-xs text-slate-400 hover:text-slate-200"
                    onClick={() => dismissAnnouncement(a.id)}
                  >
                    Dismiss
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2 items-center flex-wrap">
            <Link
              href={summary.targetHref}
              onClick={() =>
                recordOnboardingCtaClick({
                  source: 'dashboard_banner',
                  target: summary.targetHref,
                  stepId: summary.nextStepId,
                })
              }
              className="inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              {summary.nextStepLabel ? `Continue with ${summary.nextStepLabel}` : 'Continue setup'} →
            </Link>
            <button
              onClick={handleDismiss}
              className="text-sm text-slate-400 hover:text-slate-200"
            >
              Dismiss
            </button>
            {/* Health badges summary */}
            <div className="flex items-center gap-2 text-xs text-slate-400">
              {servicesSelected?.cloud !== false && (
                <span className={`px-2 py-1 rounded-full border ${status.cloud_connected ? 'border-green-500 text-green-300' : 'border-yellow-500 text-yellow-300'}`}>
                  Cloud {status.cloud_connected ? 'Healthy' : 'Pending'}
                </span>
              )}
              {servicesSelected?.appsec && (
                <span className={`px-2 py-1 rounded-full border ${status.appsec_connected ? 'border-green-500 text-green-300' : 'border-yellow-500 text-yellow-300'}`}>
                  AppSec {status.appsec_connected ? 'Healthy' : 'Pending'}
                </span>
              )}
              {servicesSelected?.git && (
                <span className={`px-2 py-1 rounded-full border ${status.git_connected ? 'border-green-500 text-green-300' : 'border-yellow-500 text-yellow-300'}`}>
                  Git {status.git_connected ? 'Healthy' : 'Pending'}
                </span>
              )}
              {servicesSelected?.aiShield && (
                <span className={`px-2 py-1 rounded-full border ${status.ai_connected ? 'border-green-500 text-green-300' : 'border-yellow-500 text-yellow-300'}`}>
                  AI {status.ai_connected ? 'Healthy' : 'Pending'}
                </span>
              )}
              {servicesSelected?.socManaged === false && (
                <span className={`px-2 py-1 rounded-full border ${status.ticketing_connected ? 'border-green-500 text-green-300' : 'border-yellow-500 text-yellow-300'}`}>
                  Ticketing {status.ticketing_connected ? 'Healthy' : 'Pending'}
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={handleDismiss}
          className="text-slate-400 hover:text-slate-200"
          aria-label="Dismiss"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
