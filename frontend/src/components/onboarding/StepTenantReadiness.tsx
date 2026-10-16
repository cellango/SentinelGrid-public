'use client';

import React, { useEffect, useState } from 'react';
import { saveTrustProfile, type OnboardingStatus, type TrustProfile } from '@/lib/api/onboarding';
import Link from 'next/link';

interface Props {
  status: OnboardingStatus | null;
  onRefresh: () => Promise<void> | void;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

const defaultTrustProfile: TrustProfile = {
  enabled: false,
  frameworks: [],
  primaryDriver: null,
  targetTimeline: null,
  needsQuestionnaireSupport: false,
  needsEvidenceExports: false,
  notes: '',
};

const frameworkOptions = [
  { value: 'soc2', label: 'SOC 2' },
  { value: 'hipaa', label: 'HIPAA' },
  { value: 'pci_dss', label: 'PCI DSS' },
  { value: 'iso27001', label: 'ISO 27001' },
  { value: 'customer_questionnaires', label: 'Customer questionnaires' },
];

const driverOptions = [
  { value: 'audit', label: 'Formal audit' },
  { value: 'customer_security_review', label: 'Customer security review' },
  { value: 'renewal_pressure', label: 'Renewal or procurement pressure' },
  { value: 'board_reporting', label: 'Board or leadership reporting' },
  { value: 'exploratory', label: 'Exploratory planning' },
];

const timelineOptions = [
  { value: '30_days', label: 'Next 30 days' },
  { value: '60_days', label: 'Next 60 days' },
  { value: '90_days', label: 'Next 90 days' },
  { value: 'this_quarter', label: 'This quarter' },
  { value: 'exploratory', label: 'No fixed deadline yet' },
];

export default function StepTenantReadiness({ status, onRefresh, onNext, onBack, onSkip }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [trustError, setTrustError] = useState<string | null>(null);
  const [trustSaving, setTrustSaving] = useState(false);
  const [trustSaved, setTrustSaved] = useState(false);
  const peopleReady = (status?.access_profile_ready ?? false) && (status?.birthright_ready ?? false);
  const [trustProfile, setTrustProfile] = useState<TrustProfile>(defaultTrustProfile);

  useEffect(() => {
    const rawProfile = status?.trust_profile || status?.services_selected?.trustProfile;
    if (rawProfile && typeof rawProfile === 'object') {
      setTrustProfile({
        enabled: Boolean(rawProfile.enabled),
        frameworks: Array.isArray(rawProfile.frameworks) ? rawProfile.frameworks : [],
        primaryDriver: rawProfile.primaryDriver || null,
        targetTimeline: rawProfile.targetTimeline || null,
        needsQuestionnaireSupport: Boolean(rawProfile.needsQuestionnaireSupport),
        needsEvidenceExports: Boolean(rawProfile.needsEvidenceExports),
        notes: rawProfile.notes || '',
      });
      setTrustSaved(Boolean(rawProfile.enabled));
    } else {
      setTrustProfile(defaultTrustProfile);
      setTrustSaved(false);
    }
  }, [status?.trust_profile, status?.services_selected]);

  const trustProfileIncomplete =
    trustProfile.enabled &&
    (
      trustProfile.frameworks.length === 0 ||
      !trustProfile.primaryDriver ||
      !trustProfile.targetTimeline ||
      (!trustProfile.needsQuestionnaireSupport && !trustProfile.needsEvidenceExports)
    );

  const handleContinue = async () => {
    setError(null);
    if (!peopleReady) {
      setError('Complete the default access profile and at least one birthright rule, then refresh status.');
      return;
    }
    onNext();
  };

  const handleRefresh = async () => {
    try {
      await onRefresh();
      setError(null);
    } catch (e: any) {
      setError(e?.message || 'Failed to refresh readiness status');
    }
  };

  const toggleFramework = (framework: string) => {
    setTrustSaved(false);
    setTrustProfile((current) => ({
      ...current,
      enabled: true,
      frameworks: current.frameworks.includes(framework)
        ? current.frameworks.filter((item) => item !== framework)
        : [...current.frameworks, framework],
    }));
  };

  const handleSaveTrustProfile = async () => {
    setTrustError(null);
    if (
      trustProfile.enabled &&
      (
        trustProfile.frameworks.length === 0 ||
        !trustProfile.primaryDriver ||
        !trustProfile.targetTimeline ||
        (!trustProfile.needsQuestionnaireSupport && !trustProfile.needsEvidenceExports)
      )
    ) {
      setTrustError('Pick at least one framework, a primary driver, a target timeline, and at least one output before saving.');
      return;
    }

    try {
      setTrustSaving(true);
      await saveTrustProfile(trustProfile);
      await onRefresh();
      setTrustSaved(true);
    } catch (e: any) {
      setTrustError(e?.message || 'Failed to save trust profile');
    } finally {
      setTrustSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold mb-2">Tenant readiness</h2>
        <div className="flex items-center gap-3 flex-wrap">
          <p className="text-slate-300">
            Finish People &amp; Access setup so joiners get day-one access. Create a default access profile and at least one birthright rule.
          </p>
          <span
            className={`text-xs px-3 py-1 rounded-full border ${
              peopleReady ? 'border-green-500 text-green-300 bg-green-500/10' : 'border-amber-500 text-amber-200 bg-amber-500/10'
            }`}
          >
            {peopleReady ? 'Ready' : 'Pending'}
          </span>
        </div>
      </div>

      {!peopleReady && (
        <div className="bg-amber-500/10 border border-amber-400/40 rounded-lg p-3 text-sm text-amber-100">
          ⚠️ Tenant readiness is incomplete. Complete the steps in People &amp; Access, then refresh.
        </div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold text-slate-100">Default access profile</div>
            <div className="text-xs text-slate-300">Define baseline access for all joiners.</div>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <div className="font-semibold text-slate-100">Birthright rule</div>
            <div className="text-xs text-slate-300">Ensure every new hire gets day-one access.</div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 space-y-4">
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-100">Trust and compliance goals</h3>
            <p className="mt-1 text-sm text-slate-300">
              If you have audit pressure, customer questionnaires, or reporting deadlines, capture that here so SentinelGrid can point onboarding and reporting guidance at the right deliverables.
            </p>
          </div>
          <span
            className={`rounded-full border px-3 py-1 text-xs ${
              trustProfile.enabled
                ? trustProfileIncomplete
                  ? 'border-amber-500/50 bg-amber-500/10 text-amber-200'
                  : 'border-green-500/50 bg-green-500/10 text-green-200'
                : 'border-slate-700 text-slate-300'
            }`}
          >
            {trustProfile.enabled
              ? trustProfileIncomplete
                ? 'Trust profile incomplete'
                : 'Trust profile captured'
              : 'Optional'}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              setTrustSaved(false);
              setTrustProfile((current) => ({ ...current, enabled: true }));
            }}
            className={`rounded-full px-4 py-2 text-sm font-medium border ${
              trustProfile.enabled
                ? 'border-violet-400 bg-violet-400/10 text-violet-200'
                : 'border-slate-700 text-slate-300 hover:border-violet-400/40'
            }`}
          >
            We have trust or audit pressure
          </button>
          <button
            type="button"
            onClick={() => {
              setTrustSaved(false);
              setTrustError(null);
              setTrustProfile(defaultTrustProfile);
            }}
            className={`rounded-full px-4 py-2 text-sm font-medium border ${
              !trustProfile.enabled
                ? 'border-slate-500 bg-slate-800 text-slate-100'
                : 'border-slate-700 text-slate-300 hover:border-slate-500'
            }`}
          >
            Not a first-quarter priority
          </button>
        </div>

        {trustProfile.enabled && (
          <div className="space-y-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-300">Frameworks or pressure</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {frameworkOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleFramework(option.value)}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      trustProfile.frameworks.includes(option.value)
                        ? 'border-violet-400 bg-violet-400/10 text-violet-100'
                        : 'border-slate-700 bg-slate-950/40 text-slate-300 hover:border-violet-400/30'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-300">Primary driver</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {driverOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setTrustSaved(false);
                      setTrustProfile((current) => ({
                        ...current,
                        enabled: true,
                        primaryDriver: option.value,
                      }));
                    }}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      trustProfile.primaryDriver === option.value
                        ? 'border-violet-400 bg-violet-400/10 text-violet-100'
                        : 'border-slate-700 bg-slate-950/40 text-slate-300 hover:border-violet-400/30'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-300">Target timeline</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {timelineOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setTrustSaved(false);
                      setTrustProfile((current) => ({
                        ...current,
                        enabled: true,
                        targetTimeline: option.value,
                      }));
                    }}
                    className={`rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      trustProfile.targetTimeline === option.value
                        ? 'border-violet-400 bg-violet-400/10 text-violet-100'
                        : 'border-slate-700 bg-slate-950/40 text-slate-300 hover:border-violet-400/30'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-violet-300">Outputs you need first</p>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="flex items-start gap-3 rounded-lg border border-slate-700 bg-slate-950/40 p-4 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={trustProfile.needsQuestionnaireSupport}
                    onChange={(e) => {
                      setTrustSaved(false);
                      setTrustProfile((current) => ({
                        ...current,
                        enabled: true,
                        needsQuestionnaireSupport: e.target.checked,
                      }));
                    }}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block font-medium text-slate-100">Questionnaire support</span>
                    Capture that you need help answering customer security reviews and vendor questionnaires.
                  </span>
                </label>
                <label className="flex items-start gap-3 rounded-lg border border-slate-700 bg-slate-950/40 p-4 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    checked={trustProfile.needsEvidenceExports}
                    onChange={(e) => {
                      setTrustSaved(false);
                      setTrustProfile((current) => ({
                        ...current,
                        enabled: true,
                        needsEvidenceExports: e.target.checked,
                      }));
                    }}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="block font-medium text-slate-100">Evidence exports and reports</span>
                    Tell SentinelGrid that early reporting, evidence capture, and audit-facing exports matter right away.
                  </span>
                </label>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-[0.14em] text-violet-300" htmlFor="trust-notes">
                Notes
              </label>
              <textarea
                id="trust-notes"
                value={trustProfile.notes || ''}
                onChange={(e) => {
                  setTrustSaved(false);
                  setTrustProfile((current) => ({
                    ...current,
                    enabled: true,
                    notes: e.target.value,
                  }));
                }}
                rows={3}
                placeholder="Examples: SOC 2 readiness this quarter, repeated customer questionnaires, audit evidence for board review."
                className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
              />
            </div>

            {trustError && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
                {trustError}
              </div>
            )}
            {trustSaved && !trustError && (
              <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-200">
                Trust profile saved. SentinelGrid can now shape compliance prompts and reporting guidance around these goals.
              </div>
            )}

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleSaveTrustProfile}
                disabled={trustSaving}
                className="inline-flex items-center justify-center rounded-lg bg-violet-400 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-violet-300 disabled:opacity-60"
              >
                {trustSaving ? 'Saving…' : 'Save trust profile'}
              </button>
              <Link
                href="/dashboard/compliance"
                className="inline-flex items-center justify-center rounded-lg border border-violet-500/30 px-4 py-2 text-sm font-medium text-violet-200 hover:border-violet-400"
              >
                Open compliance dashboard
              </Link>
              <Link
                href="/dashboard/compliance/reports"
                className="inline-flex items-center justify-center rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:border-violet-400"
              >
                Open reports
              </Link>
            </div>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-3 items-center">
        <Link
          href="/dashboard/iam/people?show=readiness"
          className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 text-sm font-medium hover:bg-cyan-400"
        >
          Open People &amp; Access
        </Link>
        <button
          type="button"
          onClick={handleRefresh}
          className="px-3 py-2 rounded-lg border border-slate-700 text-sm text-slate-200 hover:border-cyan-400"
        >
          Refresh status
        </button>
        <button
          type="button"
          onClick={handleContinue}
          disabled={!peopleReady}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${
            peopleReady
              ? 'bg-green-500 text-slate-950 hover:bg-green-400'
              : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed'
          }`}
        >
          Mark complete
        </button>
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-slate-300 hover:text-white"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onSkip}
          className="text-sm text-slate-400 hover:text-white"
        >
          Skip
        </button>
      </div>
    </div>
  );
}
