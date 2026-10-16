'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import StepIdP from './StepIdP';
import StepCloudConnection from './StepCloudConnection';
import StepEndpointAgent from './StepEndpointAgent';
import StepGitSecurity from './StepGitSecurity';
import StepTicketing from './StepTicketing';

type Step = 1 | 2 | 3 | 4 | 5;

interface OnboardingWizardProps {
  initialStep?: Step;
  onComplete?: () => void;
}

export default function OnboardingWizard({
  initialStep = 1,
  onComplete,
}: OnboardingWizardProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>(initialStep);
  const [completedSteps, setCompletedSteps] = useState<Set<Step>>(new Set());
  const [enableGitStep, setEnableGitStep] = useState<boolean>(true);
  const [ticketingChoice, setTicketingChoice] = useState<'sentinelgrid' | 'jira' | 'servicenow'>('sentinelgrid');

  // Load progress from localStorage or API
  useEffect(() => {
    // TODO: Fetch onboarding progress from API
    const savedProgress = localStorage.getItem('onboarding_progress');
    if (savedProgress) {
      try {
        const progress = JSON.parse(savedProgress);
        if (progress.completedSteps) {
          setCompletedSteps(new Set(progress.completedSteps));
        }
        if (progress.currentStep && progress.currentStep >= 1 && progress.currentStep <= 4) {
          setStep(progress.currentStep as Step);
        }
      } catch (e) {
        console.error('Error loading onboarding progress:', e);
      }
    }
    // Read signup flags for branching
    const storedEnableAppSec = localStorage.getItem('signup_enable_appsec');
    if (storedEnableAppSec !== null) {
      setEnableGitStep(storedEnableAppSec !== 'false');
    }
    const storedTicketing = (localStorage.getItem('signup_ticketing') as 'sentinelgrid' | 'jira' | 'servicenow') || 'sentinelgrid';
    setTicketingChoice(storedTicketing);
  }, []);

  const saveProgress = (currentStep: Step, completed: Step[]) => {
    const progress = {
      currentStep,
      completedSteps: completed,
      lastUpdated: new Date().toISOString(),
    };
    localStorage.setItem('onboarding_progress', JSON.stringify(progress));
    // TODO: Save to API
  };

  const handleStepComplete = (stepNumber: Step) => {
    const newCompleted = new Set(completedSteps);
    newCompleted.add(stepNumber);
    setCompletedSteps(newCompleted);
    
    // Save progress
    saveProgress(stepNumber, Array.from(newCompleted));
    
    // Move to next step
    const maxStep: Step = 5;
    if (stepNumber < maxStep) {
      setStep((stepNumber + 1) as Step);
    } else {
      // All steps complete
      handleComplete();
    }
  };

  const handleComplete = () => {
    // Mark onboarding as complete
    localStorage.removeItem('onboarding_progress');
    // TODO: Update API to mark onboarding as complete
    
    if (onComplete) {
      onComplete();
    } else {
      router.push('/dashboard');
    }
  };

  const handleSkip = (stepNumber: Step) => {
    // Allow skipping steps
    const maxStep: Step = 5;
    if (stepNumber < maxStep) {
      setStep((stepNumber + 1) as Step);
    } else {
      handleComplete();
    }
  };

  const goToStep = (stepNumber: Step) => {
    setStep(stepNumber);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {[1, 2, 3, 4, 5].map((stepNum) => (
              <React.Fragment key={stepNum}>
                <button
                  onClick={() => goToStep(stepNum as Step)}
                  className={`
                    flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all
                    ${
                      step === stepNum
                        ? 'border-cyan-400 bg-cyan-400 text-slate-950'
                        : completedSteps.has(stepNum as Step)
                        ? 'border-green-500 bg-green-500 text-white'
                        : 'border-slate-600 text-slate-400'
                    }
                  `}
                >
                  {completedSteps.has(stepNum as Step) ? (
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    stepNum
                  )}
                </button>
                {stepNum < 4 && (
                  <div
                    className={`flex-1 h-1 mx-2 ${
                      completedSteps.has((stepNum + 1) as Step) || step > stepNum
                        ? 'bg-green-500'
                        : 'bg-slate-600'
                    }`}
                  />
                )}
              </React.Fragment>
            ))}
          </div>
          <div className="flex justify-between text-xs text-slate-400">
            <span className={step >= 1 ? 'text-cyan-400' : ''}>Identity</span>
            <span className={step >= 2 ? 'text-cyan-400' : ''}>Cloud</span>
            <span className={step >= 3 ? 'text-cyan-400' : ''}>Endpoint</span>
            <span className={step >= 4 ? 'text-cyan-400' : ''}>Git</span>
            <span className={step >= 5 ? 'text-cyan-400' : ''}>Ticketing</span>
          </div>
        </div>

        {/* Step Content */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl">
          {step === 1 && (
            <StepIdP
              onNext={() => handleStepComplete(1)}
              onSkip={() => handleSkip(1)}
            />
          )}
          {step === 2 && (
            <StepCloudConnection
              onNext={() => handleStepComplete(2)}
              onBack={() => setStep(1)}
              onSkip={() => handleSkip(2)}
            />
          )}
          {step === 3 && (
            <StepEndpointAgent
              onNext={() => handleStepComplete(3)}
              onBack={() => setStep(2)}
              onSkip={() => handleSkip(3)}
            />
          )}
          {step === 4 && enableGitStep && (
            <StepGitSecurity
              onNext={() => handleStepComplete(4)}
              onBack={() => setStep(3)}
              onSkip={() => handleSkip(4)}
            />
          )}
          {step === 4 && !enableGitStep && (
            <StepTicketing
              ticketingChoice={ticketingChoice}
              onNext={() => handleStepComplete(4)}
              onBack={() => setStep(3)}
              onSkip={() => handleSkip(4)}
            />
          )}
          {step === 5 && enableGitStep && (
            <StepTicketing
              ticketingChoice={ticketingChoice}
              onNext={() => handleStepComplete(5)}
              onBack={() => setStep(4)}
              onSkip={() => handleSkip(5)}
            />
          )}
        </div>
      </div>
    </div>
  );
}

