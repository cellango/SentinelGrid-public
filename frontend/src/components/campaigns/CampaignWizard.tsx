/**
 * Campaign Wizard Component
 * Multi-step form for creating audit campaigns
 */

'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateCampaign } from '@/lib/hooks/useCampaigns';
import { useRouter } from 'next/navigation';
import { format } from 'date-fns';

// Form schema
const campaignSchema = z.object({
  name: z.string().min(1, 'Name is required').max(255, 'Name too long'),
  description: z.string().optional(),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
  reviewer_type: z.enum(['self', 'manager', 'admin']),
  auto_revoke_days: z.number().int().min(0).optional(),
  entitlement_patterns: z.array(z.string()).optional(),
}).refine((data) => {
  if (data.start_date && data.end_date) {
    return new Date(data.end_date) > new Date(data.start_date);
  }
  return true;
}, {
  message: 'End date must be after start date',
  path: ['end_date'],
});

type CampaignFormData = z.infer<typeof campaignSchema>;

interface CampaignWizardProps {
  tenantId: string; // TODO: Get from context
}

const steps = [
  { id: 1, name: 'Basic Info', description: 'Campaign name and dates' },
  { id: 2, name: 'Scope', description: 'Entitlement patterns' },
  { id: 3, name: 'Reviewer', description: 'Who reviews' },
  { id: 4, name: 'Auto-Revoke', description: 'Auto-revocation settings' },
  { id: 5, name: 'Review', description: 'Review and create' },
];

export function CampaignWizard({ tenantId }: CampaignWizardProps) {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const createCampaign = useCreateCampaign();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = useForm<CampaignFormData>({
    resolver: zodResolver(campaignSchema),
    mode: 'onChange',
    defaultValues: {
      reviewer_type: 'self',
      entitlement_patterns: [],
    },
  });

  const watchedValues = watch();

  const onSubmit = async (data: CampaignFormData) => {
    try {
      const campaign = await createCampaign.mutateAsync({
        tenant_id: tenantId,
        name: data.name,
        description: data.description || undefined,
        start_date: new Date(data.start_date).toISOString(),
        end_date: new Date(data.end_date).toISOString(),
        reviewer_type: data.reviewer_type,
        auto_revoke_days: data.auto_revoke_days,
        entitlement_patterns: data.entitlement_patterns,
      });
      router.push(`/dashboard/campaigns/${campaign.id}`);
    } catch (error) {
      // Error handled by mutation hook (toast notification)
    }
  };

  const nextStep = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const isStepValid = (step: number): boolean => {
    switch (step) {
      case 1:
        return !!(watchedValues.name && watchedValues.start_date && watchedValues.end_date);
      case 2:
        return true; // Optional step
      case 3:
        return !!watchedValues.reviewer_type;
      case 4:
        return true; // Optional step
      default:
        return true;
    }
  };

  // Get minimum end date (day after start date)
  const minEndDate = watchedValues.start_date
    ? format(new Date(new Date(watchedValues.start_date).getTime() + 86400000), "yyyy-MM-dd")
    : '';

  return (
    <div className="max-w-4xl mx-auto">
      {/* Progress Steps */}
      <div className="mb-8">
        <nav aria-label="Progress">
          <ol className="flex items-center">
            {steps.map((step, stepIdx) => (
              <li key={step.id} className={`relative ${stepIdx !== steps.length - 1 ? 'pr-8 sm:pr-20' : ''}`}>
                <div className="flex items-center">
                  <div
                    className={`relative flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                      step.id < currentStep
                        ? 'border-blue-600 bg-blue-600'
                        : step.id === currentStep
                        ? 'border-blue-600 bg-surface-card'
                        : 'border-border bg-surface-card'
                    }`}
                  >
                    {step.id < currentStep ? (
                      <svg className="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      <span
                        className={`text-sm font-medium ${
                          step.id === currentStep ? 'text-blue-600' : 'text-text-muted'
                        }`}
                      >
                        {step.id}
                      </span>
                    )}
                  </div>
                  <div className="ml-4 min-w-0 flex-1">
                    <p className={`text-sm font-medium ${step.id <= currentStep ? 'text-blue-600' : 'text-text-muted'}`}>
                      {step.name}
                    </p>
                    <p className="text-sm text-text-muted">{step.description}</p>
                  </div>
                </div>
                {stepIdx !== steps.length - 1 && (
                  <div className="absolute top-5 left-5 -ml-px h-0.5 w-full bg-border-muted" aria-hidden="true">
                    <div
                      className={`h-full ${step.id < currentStep ? 'bg-blue-600' : 'bg-border-muted'}`}
                      style={{ width: step.id < currentStep ? '100%' : '0%' }}
                    />
                  </div>
                )}
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {/* Form Steps */}
      <form onSubmit={handleSubmit(onSubmit)} className="bg-surface-card shadow-sm rounded-lg p-6">
        {/* Step 1: Basic Info */}
        {currentStep === 1 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text-main mb-4">Basic Information</h2>
              <p className="text-sm text-text-muted mb-6">
                Provide a name and description for your audit campaign, and set the start and end dates.
              </p>
            </div>

            <div>
              <label htmlFor="name" className="block text-sm font-medium text-text-muted mb-1">
                Campaign Name <span className="text-red-500">*</span>
              </label>
              <input
                {...register('name')}
                type="text"
                id="name"
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., Q4 2025 Access Review"
              />
              {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>}
            </div>

            <div>
              <label htmlFor="description" className="block text-sm font-medium text-text-muted mb-1">
                Description
              </label>
              <textarea
                {...register('description')}
                id="description"
                rows={4}
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Optional description of the campaign..."
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="start_date" className="block text-sm font-medium text-text-muted mb-1">
                  Start Date <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('start_date')}
                  type="date"
                  id="start_date"
                  min={format(new Date(), 'yyyy-MM-dd')}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.start_date && <p className="mt-1 text-sm text-red-600">{errors.start_date.message}</p>}
              </div>

              <div>
                <label htmlFor="end_date" className="block text-sm font-medium text-text-muted mb-1">
                  End Date <span className="text-red-500">*</span>
                </label>
                <input
                  {...register('end_date')}
                  type="date"
                  id="end_date"
                  min={minEndDate || format(new Date(), 'yyyy-MM-dd')}
                  className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {errors.end_date && <p className="mt-1 text-sm text-red-600">{errors.end_date.message}</p>}
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Scope Selection */}
        {currentStep === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text-main mb-4">Scope Selection</h2>
              <p className="text-sm text-text-muted mb-6">
                Optionally filter which entitlements are included in this campaign using entitlement patterns.
                Leave empty to include all entitlements.
              </p>
            </div>

            <div>
              <label htmlFor="entitlement_patterns" className="block text-sm font-medium text-text-muted mb-1">
                Entitlement Patterns (Optional)
              </label>
              <p className="text-xs text-text-muted mb-2">
                Enter patterns like: <code className="bg-bg-alt px-1 rounded">incident:*:write</code> or{' '}
                <code className="bg-bg-alt px-1 rounded">alert:*:*</code>
              </p>
              <textarea
                id="entitlement_patterns"
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                rows={6}
                placeholder="incident:*:write&#10;alert:*:*&#10;sensitive_data:*:*"
                onChange={(e) => {
                  const patterns = e.target.value
                    .split('\n')
                    .map((p) => p.trim())
                    .filter((p) => p.length > 0);
                  setValue('entitlement_patterns', patterns, { shouldValidate: true });
                }}
              />
              {watchedValues.entitlement_patterns && watchedValues.entitlement_patterns.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm text-text-muted">Patterns:</p>
                  <ul className="list-disc list-inside text-sm text-text-muted mt-1">
                    {watchedValues.entitlement_patterns.map((pattern, idx) => (
                      <li key={idx}>{pattern}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 3: Reviewer Configuration */}
        {currentStep === 3 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text-main mb-4">Reviewer Configuration</h2>
              <p className="text-sm text-text-muted mb-6">
                Choose who will be responsible for certifying entitlements in this campaign.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-muted mb-3">
                Reviewer Type <span className="text-red-500">*</span>
              </label>
              <div className="space-y-3">
                {[
                  { value: 'self', label: 'Self', description: 'Users certify their own entitlements' },
                  { value: 'manager', label: 'Manager', description: 'Managers certify their team members\' entitlements' },
                  { value: 'admin', label: 'Admin', description: 'Administrators certify all entitlements' },
                ].map((option) => (
                  <label
                    key={option.value}
                    className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                      watchedValues.reviewer_type === option.value
                        ? 'border-blue-600 bg-blue-50'
                        : 'border-surface-card-border hover:border-border'
                    }`}
                  >
                    <input
                      {...register('reviewer_type')}
                      type="radio"
                      value={option.value}
                      className="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500"
                    />
                    <div className="ml-3">
                      <div className="text-sm font-medium text-text-main">{option.label}</div>
                      <div className="text-sm text-text-muted">{option.description}</div>
                    </div>
                  </label>
                ))}
              </div>
              {errors.reviewer_type && <p className="mt-1 text-sm text-red-600">{errors.reviewer_type.message}</p>}
            </div>
          </div>
        )}

        {/* Step 4: Auto-Revoke Settings */}
        {currentStep === 4 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text-main mb-4">Auto-Revoke Settings</h2>
              <p className="text-sm text-text-muted mb-6">
                Configure automatic revocation of entitlements that are not certified by the deadline.
              </p>
            </div>

            <div>
              <label htmlFor="auto_revoke_days" className="block text-sm font-medium text-text-muted mb-1">
                Auto-Revoke Days (Optional)
              </label>
              <p className="text-xs text-text-muted mb-2">
                Number of days after the campaign end date to automatically revoke uncertified entitlements.
                Leave empty to disable auto-revocation.
              </p>
              <input
                {...register('auto_revoke_days', { valueAsNumber: true })}
                type="number"
                id="auto_revoke_days"
                min="0"
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="e.g., 7"
              />
              {errors.auto_revoke_days && (
                <p className="mt-1 text-sm text-red-600">{errors.auto_revoke_days.message}</p>
              )}
            </div>
          </div>
        )}

        {/* Step 5: Review & Create */}
        {currentStep === 5 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text-main mb-4">Review & Create</h2>
              <p className="text-sm text-text-muted mb-6">Review your campaign settings before creating.</p>
            </div>

            <div className="bg-surface-hover rounded-lg p-6 space-y-4">
              <div>
                <span className="text-sm font-medium text-text-muted">Campaign Name:</span>
                <p className="text-sm text-text-main mt-1">{watchedValues.name}</p>
              </div>

              {watchedValues.description && (
                <div>
                  <span className="text-sm font-medium text-text-muted">Description:</span>
                  <p className="text-sm text-text-main mt-1">{watchedValues.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-sm font-medium text-text-muted">Start Date:</span>
                  <p className="text-sm text-text-main mt-1">
                    {watchedValues.start_date ? format(new Date(watchedValues.start_date), 'PPP') : '-'}
                  </p>
                </div>
                <div>
                  <span className="text-sm font-medium text-text-muted">End Date:</span>
                  <p className="text-sm text-text-main mt-1">
                    {watchedValues.end_date ? format(new Date(watchedValues.end_date), 'PPP') : '-'}
                  </p>
                </div>
              </div>

              <div>
                <span className="text-sm font-medium text-text-muted">Reviewer Type:</span>
                <p className="text-sm text-text-main mt-1 capitalize">{watchedValues.reviewer_type}</p>
              </div>

              {watchedValues.entitlement_patterns && watchedValues.entitlement_patterns.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-text-muted">Entitlement Patterns:</span>
                  <ul className="list-disc list-inside text-sm text-text-main mt-1">
                    {watchedValues.entitlement_patterns.map((pattern, idx) => (
                      <li key={idx} className="font-mono">{pattern}</li>
                    ))}
                  </ul>
                </div>
              )}

              {watchedValues.auto_revoke_days && (
                <div>
                  <span className="text-sm font-medium text-text-muted">Auto-Revoke:</span>
                  <p className="text-sm text-text-main mt-1">{watchedValues.auto_revoke_days} days after end date</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="mt-8 flex justify-between">
          <button
            type="button"
            onClick={prevStep}
            disabled={currentStep === 1}
            className="px-4 py-2 border border-border rounded-md text-sm font-medium text-text-muted hover:bg-surface-hover disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          {currentStep < steps.length ? (
            <button
              type="button"
              onClick={nextStep}
              disabled={!isStepValid(currentStep)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          ) : (
            <button
              type="submit"
              disabled={!isValid || createCampaign.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createCampaign.isPending ? 'Creating...' : 'Create Campaign'}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

