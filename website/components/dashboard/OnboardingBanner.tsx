'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { getOnboardingStatus, OnboardingStatus } from '@/lib/api/onboarding';

export default function OnboardingBanner() {
  const router = useRouter();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    async function loadStatus() {
      try {
        const onboardingStatus = await getOnboardingStatus();
        setStatus(onboardingStatus);
        
        // Check if user dismissed banner
        const dismissedKey = `onboarding_banner_dismissed_${onboardingStatus.onboarding_completed}`;
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
      const dismissedKey = `onboarding_banner_dismissed_${status.onboarding_completed}`;
      localStorage.setItem(dismissedKey, 'true');
      setDismissed(true);
    }
  };

  const handleContinue = () => {
    if (status) {
      // Determine which step to go to
      const idpDone = status.step_idp_completed ?? status.idp_connected;
      const cloudDone = status.step_cloud_completed ?? status.cloud_connected;
      const endpointDone = status.step_endpoint_completed ?? status.endpoint_deployed;
      const gitDone = status.step_git_completed ?? status.git_connected;

      let step = 1;
      if (!idpDone) step = 1;
      else if (!cloudDone) step = 2;
      else if (!endpointDone) step = 3;
      else if (!gitDone) step = 4;

      router.push(`/onboarding?step=${step}`);
    }
  };

  if (loading || !status || dismissed || status.onboarding_completed) {
    return null;
  }

  // Calculate progress
  const steps = [
    status.step_idp_completed ?? status.idp_connected,
    status.step_cloud_completed ?? status.cloud_connected,
    status.step_endpoint_completed ?? status.endpoint_deployed,
    status.step_git_completed ?? status.git_connected,
  ];
  const completedSteps = steps.filter(Boolean).length;
  const progress = (completedSteps / 4) * 100;

  return (
    <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-xl p-4 md:p-6 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-2xl">🚀</span>
            <h3 className="text-lg font-semibold text-cyan-300">Complete Your Setup</h3>
          </div>
          <p className="text-sm text-slate-300 mb-4">
            Finish setting up SentinelGrid to get the most out of your security monitoring.
            {completedSteps > 0 && (
              <span className="ml-2 text-cyan-400">
                {completedSteps} of 4 steps completed ({Math.round(progress)}%)
              </span>
            )}
          </p>
          
          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex gap-1 mb-2">
              {[1, 2, 3, 4].map((stepNum) => (
                <div
                  key={stepNum}
                  className={`flex-1 h-2 rounded ${
                    steps[stepNum - 1]
                      ? 'bg-green-500'
                      : stepNum <= completedSteps + 1
                      ? 'bg-cyan-500'
                      : 'bg-slate-700'
                  }`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>Identity</span>
              <span>Cloud</span>
              <span>Endpoint</span>
              <span>Git</span>
            </div>
          </div>

          {/* Missing Steps */}
          <div className="flex flex-wrap gap-2 mb-4">
            {!steps[0] && (
              <span className="text-xs px-2 py-1 bg-slate-800 rounded border border-slate-700">
                ⚠️ Connect Identity Provider
              </span>
            )}
            {!steps[1] && (
              <span className="text-xs px-2 py-1 bg-slate-800 rounded border border-slate-700">
                ⚠️ Connect Cloud
              </span>
            )}
            {!steps[2] && (
              <span className="text-xs px-2 py-1 bg-slate-800 rounded border border-slate-700">
                ⚠️ Deploy Endpoint Protection
              </span>
            )}
            {!steps[3] && (
              <span className="text-xs px-2 py-1 bg-slate-800 rounded border border-slate-700">
                ⚠️ Connect Git Repositories
              </span>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleContinue}
              className="inline-flex items-center justify-center rounded-full px-4 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Continue Setup →
            </button>
            <button
              onClick={handleDismiss}
              className="text-sm text-slate-400 hover:text-slate-200"
            >
              Dismiss
            </button>
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

