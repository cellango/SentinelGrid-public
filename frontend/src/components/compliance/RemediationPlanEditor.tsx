/**
 * Remediation Plan Editor Component
 * Create/edit remediation plans for findings
 */

'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  createRemediationPlan,
  RemediationPlan,
} from '@/lib/api/compliance-remediation';
import { toast } from 'react-hot-toast';

interface RemediationPlanEditorProps {
  findingId: string;
  findingType: 'iam_finding' | 'posture_finding';
  onExecute: (playbookId?: string) => void;
}

export default function RemediationPlanEditor({
  findingId,
  findingType,
  onExecute,
}: RemediationPlanEditorProps) {
  const queryClient = useQueryClient();
  const [plan, setPlan] = useState<RemediationPlan | null>(null);
  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string>('');

  // Get or create remediation plan
  const { data: planData, isLoading } = useQuery({
    queryKey: ['remediation-plan', findingId, findingType],
    queryFn: () => createRemediationPlan(findingId, findingType),
    enabled: !!findingId,
  });

  useEffect(() => {
    if (planData) {
      setPlan(planData.plan);
    }
  }, [planData]);

  const createPlanMutation = useMutation({
    mutationFn: (customSteps?: RemediationPlan['steps']) =>
      createRemediationPlan(findingId, findingType, customSteps),
    onSuccess: (data) => {
      setPlan(data.plan);
      queryClient.invalidateQueries({ queryKey: ['remediation-plan', findingId, findingType] });
      toast.success('Remediation plan created');
    },
    onError: (error: any) => {
      toast.error(`Failed to create plan: ${error.message}`);
    },
  });

  const handleCreatePlan = () => {
    createPlanMutation.mutate(undefined);
  };

  const handleExecute = () => {
    onExecute(selectedPlaybookId || undefined);
  };

  if (isLoading) {
    return (
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
        <div className="text-sm text-text-muted dark:text-text-muted">Loading remediation plan...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Remediation Plan */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border dark:border-surface-card-border p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-main">
            Remediation Plan
          </h2>
          {!plan && (
            <button
              onClick={handleCreatePlan}
              disabled={createPlanMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {createPlanMutation.isPending ? 'Creating...' : 'Create Plan'}
            </button>
          )}
        </div>

        {plan ? (
          <div className="space-y-4">
            <div>
              <p className="text-sm text-text-muted dark:text-text-muted mb-2">
                Estimated Time: {plan.estimated_time}
              </p>
              <p className="text-sm text-text-muted dark:text-text-muted mb-2">
                Complexity: {plan.complexity}
              </p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-text-muted dark:text-text-muted mb-2">
                Remediation Steps
              </h3>
              <ol className="list-decimal list-inside space-y-2">
                {plan.steps.map((step) => (
                  <li key={step.step} className="text-sm text-text-main">
                    <span className="font-medium">{step.action}:</span> {step.description}
                  </li>
                ))}
              </ol>
            </div>

            {/* Playbook Selection */}
            <div>
              <label className="block text-sm font-medium text-text-muted dark:text-text-muted mb-2">
                Select Playbook (optional)
              </label>
              <input
                type="text"
                value={selectedPlaybookId}
                onChange={(e) => setSelectedPlaybookId(e.target.value)}
                placeholder="Enter playbook ID"
                className="w-full px-3 py-2 border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-bg-alt dark:border-border dark:text-white"
              />
            </div>

            {/* Execute Button */}
            <button
              onClick={handleExecute}
              className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              Execute Remediation
            </button>
          </div>
        ) : (
          <div className="text-center py-8 text-text-muted dark:text-text-muted">
            <p className="text-sm">No remediation plan created yet</p>
            <p className="text-xs mt-1">Click "Create Plan" to generate a remediation plan</p>
          </div>
        )}
      </div>
    </div>
  );
}

