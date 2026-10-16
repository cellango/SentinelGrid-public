'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import StepIdP from './StepIdP';
import StepCloudConnection from './StepCloudConnection';
import StepEndpointAgent from './StepEndpointAgent';
import StepGitSecurity from './StepGitSecurity';
import StepAIShield from './StepAIShield';
import StepAppSec from './StepAppSec';
import StepTicketing from './StepTicketing';
import StepTenantReadiness from './StepTenantReadiness';
import { getOnboardingStatus, type OnboardingStatus } from '@/lib/api/onboarding';
import {
  recordOnboardingCompleted,
  recordOnboardingStarted,
  recordOnboardingStepCompleted,
  recordOnboardingStepSkipped,
  recordOnboardingStepViewed,
  syncOnboardingMetricsFromStatus,
} from '@/lib/onboarding/metrics';
import { getOnboardingIdpMeta, getPreferredOnboardingIdp } from '@/lib/onboarding/idp';

type StepId = 'idp' | 'cloud' | 'endpoint' | 'git' | 'appsec' | 'ai' | 'ticketing' | 'tenant';

interface WizardStep {
  id: StepId;
  label: string;
}

interface ServicesSelected {
  cloud?: boolean;
  git?: boolean;
  appsec?: boolean;
  aiShield?: 'hosted' | 'self';
  socManaged?: boolean;
  trustProfile?: {
    enabled?: boolean;
  };
}

interface OnboardingWizardProps {
  initialStep?: number;
  onComplete?: () => void;
}

export default function OnboardingWizard({
  initialStep = 1,
  onComplete,
}: OnboardingWizardProps) {
  const router = useRouter();
  const [stepIndex, setStepIndex] = useState<number>(initialStep - 1);
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());
  const [servicesSelected, setServicesSelected] = useState<ServicesSelected>({
    cloud: true,
    git: true,
    socManaged: true,
  });
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);

  // Derive steps based on services selected; always include Identity
  const steps: WizardStep[] = useMemo(() => {
    const list: WizardStep[] = [{ id: 'idp', label: 'Identity' }];
    if (servicesSelected.cloud !== false) {
      list.push({ id: 'cloud', label: 'Cloud' });
      // Endpoint often rides with cloud; include if customer is managing their own SOC or we need agents
      list.push({ id: 'endpoint', label: 'Endpoint' });
    }
    if (servicesSelected.git) {
      list.push({ id: 'git', label: 'Git' });
    }
    if (servicesSelected.appsec) {
      list.push({ id: 'appsec', label: 'AppSec' });
    }
    if (servicesSelected.aiShield) {
      list.push({ id: 'ai', label: 'AI Shield' });
    }
    if (servicesSelected.socManaged === false) {
      list.push({ id: 'ticketing', label: 'Ticketing' });
    }
    // Always include tenant readiness as the last step so we keep a single CTA path
    list.push({ id: 'tenant', label: 'Tenant readiness' });
    // Ensure at least Identity exists
    return list;
  }, [servicesSelected]);

  const current = steps[stepIndex] || steps[0];
  const preferredIdp = getPreferredOnboardingIdp(status);
  const idpMeta = getOnboardingIdpMeta(preferredIdp);

  // Keep stepIndex in sync if initialStep or steps array changes
  useEffect(() => {
    const maxIdx = Math.max(0, steps.length - 1);
    const nextIdx = Math.min(initialStep - 1, maxIdx);
    setStepIndex(nextIdx >= 0 ? nextIdx : 0);
  }, [initialStep, steps.length]);

  const hydrateFromStatus = (resp: OnboardingStatus | null) => {
    if (!resp) return;
    setStatus(resp);
    syncOnboardingMetricsFromStatus(resp);
    const svc = (resp as any).services_selected as ServicesSelected | undefined;
    const isDemo =
      !svc ||
      (resp as any).tenant_slug === 'demo' ||
      (resp as any).tenant_name === 'Demo Company';
    const merged: ServicesSelected = {
      cloud: isDemo ? true : svc?.cloud !== false,
      git: isDemo ? true : svc?.git !== false, // default git ON unless explicitly disabled
      appsec: isDemo ? true : svc?.appsec,
      aiShield: isDemo ? 'hosted' : svc?.aiShield,
      socManaged: isDemo ? false : svc?.socManaged, // false => show ticketing step
    };
    setServicesSelected(merged);
    // Seed completed steps
    const done = new Set<StepId>();
    if (resp.steps && resp.steps.length > 0) {
      resp.steps.forEach((s) => {
        if (s.done) done.add(s.id as StepId);
      });
    }
    const peopleReady = resp.access_profile_ready === true && resp.birthright_ready === true;
    if (peopleReady) {
      done.add('tenant');
    }
    // Backfill based on legacy flags
    if (resp.idp_connected || resp.step_idp_completed) done.add('idp');
    if (resp.cloud_connected || resp.step_cloud_completed) done.add('cloud');
    if (resp.endpoint_deployed || resp.step_endpoint_completed) done.add('endpoint');
    if (resp.git_connected || resp.step_git_completed) done.add('git');
    setCompletedSteps(done);
    if (!(resp.idp_connected || resp.step_idp_completed)) {
      setStepIndex(0);
    }
    if (resp.onboarding_completed && peopleReady && onComplete) {
      onComplete();
    }
  };

  const refreshStatus = async () => {
    try {
      const resp = await getOnboardingStatus().catch(() => null);
      if (resp) {
        hydrateFromStatus(resp);
      }
    } catch {
      // ignore refresh errors in UI; banner will still show
    }
  };

  // Load onboarding status and signup-selected services
  useEffect(() => {
    const load = async () => {
      try {
        const resp = await getOnboardingStatus().catch(() => null);
        if (resp) {
          hydrateFromStatus(resp);
        }

        // Fallback: pull services_selected from signup localStorage
        if (!servicesSelected.cloud && typeof window !== 'undefined') {
          try {
            const stored = localStorage.getItem('signup_services');
            if (stored) {
              const parsed = JSON.parse(stored) as ServicesSelected;
              setServicesSelected(parsed);
            } else {
              // Default: enable cloud + git for core onboarding
              setServicesSelected({ cloud: true, git: true, socManaged: true });
            }
          } catch {
            setServicesSelected({ cloud: true, git: true, socManaged: true });
          }
        }
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [onComplete, servicesSelected.cloud, servicesSelected.git]);

  useEffect(() => {
    if (loading) return;
    recordOnboardingStarted({
      initialStep: initialStep,
      totalSteps: steps.length,
    });
  }, [loading, initialStep, steps.length]);

  useEffect(() => {
    if (loading || !current?.id) return;
    recordOnboardingStepViewed({
      stepId: current.id,
      stepIndex: stepIndex + 1,
      totalSteps: steps.length,
    });
  }, [loading, current?.id, stepIndex, steps.length]);

  const saveProgress = (currentIdx: number, completed: StepId[]) => {
    const progress = {
      currentStep: currentIdx,
      completedSteps: completed,
      lastUpdated: new Date().toISOString(),
    };
    localStorage.setItem('onboarding_progress', JSON.stringify(progress));
    // TODO: Save to API once available
  };

  const handleStepComplete = (stepId: StepId) => {
    recordOnboardingStepCompleted({
      stepId,
      stepIndex: stepIndex + 1,
      totalSteps: steps.length,
    });
    const newCompleted = new Set(completedSteps);
    newCompleted.add(stepId);
    setCompletedSteps(newCompleted);

    saveProgress(stepIndex, Array.from(newCompleted));

    // Advance
    if (stepIndex < steps.length - 1) {
      setStepIndex(stepIndex + 1);
    } else {
      handleComplete();
    }
  };

  const handleSkip = () => {
    const currentStepId = steps[stepIndex]?.id;
    if (currentStepId) {
      recordOnboardingStepSkipped({
        stepId: currentStepId,
        stepIndex: stepIndex + 1,
        totalSteps: steps.length,
      });
    }
    if (stepIndex < steps.length - 1) {
      setStepIndex(stepIndex + 1);
    } else {
      handleComplete();
    }
  };

  const handleComplete = () => {
    localStorage.removeItem('onboarding_progress');
    recordOnboardingCompleted({
      source: 'onboarding_wizard',
      totalSteps: steps.length,
    });
    if (onComplete) {
      onComplete();
    } else {
      router.push('/dashboard');
    }
  };

  const goToStep = (idx: number) => {
    if (idx >= 0 && idx < steps.length) {
      setStepIndex(idx);
    }
  };

  // Progress ring helper
  const isStepCompleted = (s: WizardStep) => completedSteps.has(s.id);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="mb-6 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
            Recommended first-day path
          </p>
          <h1 className="mt-2 text-xl font-semibold text-slate-100">
            Connect {idpMeta.shortLabel}, then a cloud target, then finish endpoint coverage.
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            That sequence gives SMB teams the fastest path to meaningful sign-in findings, posture issues, and guided remediation in the dashboard.
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {steps.map((s, idx) => (
              <React.Fragment key={s.id}>
                <button
                  onClick={() => goToStep(idx)}
                  className={`
                    flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all
                    ${
                      stepIndex === idx
                        ? 'border-cyan-400 bg-cyan-400 text-slate-950'
                        : isStepCompleted(s)
                        ? 'border-green-500 bg-green-500 text-white'
                        : 'border-slate-600 text-slate-400'
                    }
                  `}
                >
                  {isStepCompleted(s) ? (
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    idx + 1
                  )}
                </button>
                {idx < steps.length - 1 && (
                  <div
                    className={`flex-1 h-1 mx-2 ${
                      isStepCompleted(steps[idx + 1]) || stepIndex > idx ? 'bg-green-500' : 'bg-slate-600'
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
          <div className="flex justify-between text-xs text-slate-400">
            {steps.map((s, idx) => (
              <span key={s.id} className={stepIndex >= idx ? 'text-cyan-400' : ''}>
                {s.label}
              </span>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl">
          {loading && <p className="text-slate-400 text-sm">Loading onboarding status...</p>}
          {!loading && current?.id === 'idp' && (
            <StepIdP onNext={() => handleStepComplete('idp')} onSkip={handleSkip} />
          )}
          {!loading && current?.id === 'cloud' && (
            <StepCloudConnection
              onNext={() => handleStepComplete('cloud')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
            />
          )}
          {!loading && current?.id === 'endpoint' && (
            <StepEndpointAgent
              onNext={() => handleStepComplete('endpoint')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
            />
          )}
          {!loading && current?.id === 'git' && (
            <StepGitSecurity
              onNext={() => handleStepComplete('git')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
            />
          )}
          {!loading && current?.id === 'appsec' && (
            <StepAppSec
              onNext={() => handleStepComplete('appsec')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
              initialHealth={status?.appsec_health}
            />
          )}
          {!loading && current?.id === 'ai' && (
            <StepAIShield
              onNext={() => handleStepComplete('ai')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
              mode={servicesSelected.aiShield || 'hosted'}
              initialHealth={status?.ai_health}
            />
          )}
          {!loading && current?.id === 'ticketing' && (
            <StepTicketing
              onNext={() => handleStepComplete('ticketing')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
              initialHealth={status?.ticketing_health}
            />
          )}
          {!loading && current?.id === 'tenant' && (
            <StepTenantReadiness
              status={status}
              onRefresh={refreshStatus}
              onNext={() => handleStepComplete('tenant')}
              onBack={() => goToStep(Math.max(stepIndex - 1, 0))}
              onSkip={handleSkip}
            />
          )}
        </div>
      </div>
    </div>
  );
}
