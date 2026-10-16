'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import OnboardingWizard from '@/components/onboarding/OnboardingWizard';
import { getOnboardingStatus } from '@/lib/api/onboarding';
import { useAuth } from '@/lib/providers/AuthProvider';
import { firstIncompleteIndex, isPeopleReady, normalizeOnboardingSteps } from '@/lib/onboarding/steps';

export default function OnboardingPage() {
  const router = useRouter();
  const { isAuthenticated, hydrated } = useAuth();
  const [loading, setLoading] = useState(true);
  const [initialStep, setInitialStep] = useState<number>(1);

  useEffect(() => {
    // Require login before onboarding
    if (!hydrated) return;
    if (!isAuthenticated) {
      router.push('/login?redirect=/dashboard');
      return;
    }

    // Redirect authenticated users into the dashboard where OnboardingBanner
    // provides inline onboarding within the full product shell.
    router.push('/dashboard');
    return;

    async function loadOnboardingStatus() {
      try {
        const status = await getOnboardingStatus();
        const steps = normalizeOnboardingSteps(status);
        const allDone = steps.length > 0 && steps.every((s) => s.done);
        const peopleReady = isPeopleReady(status);
        const onboardingDone = status.overall_complete ?? status.onboarding_completed;
        if (allDone && onboardingDone && peopleReady) {
          router.push('/dashboard');
          return;
        }

        const defaultStep = (steps.length > 0 ? firstIncompleteIndex(steps) : 0) + 1;
        let nextStep = defaultStep;

        // Check for step query parameter
        if (typeof window !== 'undefined') {
          const params = new URLSearchParams(window.location.search);
          const stepParam = params.get('step');
          if (stepParam) {
            const stepNum = parseInt(stepParam, 10);
            if (!Number.isNaN(stepNum) && stepNum >= 1) {
              const maxStep = steps.length > 0 ? steps.length : defaultStep;
              if (stepNum <= maxStep) {
                nextStep = stepNum;
              }
            }
          }
        }

        setInitialStep(nextStep);
      } catch (error) {
        console.error('Error loading onboarding status:', error);
        // Continue with default step 1
      } finally {
        setLoading(false);
      }
    }

    loadOnboardingStatus();
  }, [router, isAuthenticated, hydrated]);

  if (!hydrated || loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  return (
    <OnboardingWizard
      initialStep={initialStep}
      onComplete={() => {
        router.push('/dashboard');
      }}
    />
  );
}
