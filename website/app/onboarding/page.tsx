'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import OnboardingWizard from '@/components/onboarding/OnboardingWizard';
import { getOnboardingStatus } from '@/lib/api/onboarding';

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-950 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div>
        </div>
      }
    >
      <OnboardingPageContent />
    </Suspense>
  );
}

function OnboardingPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [initialStep, setInitialStep] = useState<1 | 2 | 3 | 4>(1);

  useEffect(() => {
    async function loadOnboardingStatus() {
      try {
        const status = await getOnboardingStatus();
        
        // Determine initial step based on what's completed
        // Use both old and new field names for compatibility
        const idpDone = status.step_idp_completed ?? status.idp_connected;
        const cloudDone = status.step_cloud_completed ?? status.cloud_connected;
        const endpointDone = status.step_endpoint_completed ?? status.endpoint_deployed;
        const gitDone = status.step_git_completed ?? status.git_connected;
        
        if (!idpDone) {
          setInitialStep(1);
        } else if (!cloudDone) {
          setInitialStep(2);
        } else if (!endpointDone) {
          setInitialStep(3);
        } else if (!gitDone) {
          setInitialStep(4);
        } else {
          // All steps complete, redirect to dashboard
          router.push('/dashboard');
          return;
        }
        
        // Check for step query parameter
        const stepParam = searchParams.get('step');
        if (stepParam) {
          const stepNum = parseInt(stepParam, 10);
          if (stepNum >= 1 && stepNum <= 4) {
            setInitialStep(stepNum as 1 | 2 | 3 | 4);
          }
        }
      } catch (error) {
        console.error('Error loading onboarding status:', error);
        // Continue with default step 1
      } finally {
        setLoading(false);
      }
    }

    loadOnboardingStatus();
  }, [router, searchParams]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
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
