'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getComplianceFrameworkSelections,
  updateComplianceFrameworkSelections,
  type ComplianceFrameworkSelectionOption,
  type ComplianceFrameworkSelectionStatus,
} from '@/lib/api/compliance';
import toast from 'react-hot-toast';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';

type DraftSelection = {
  selected: boolean;
  status: ComplianceFrameworkSelectionStatus;
  target_date?: string | null;
};

const SUPPORTED_REPORTS: Record<string, string> = {
  soc2: 'SOC 2 coverage and trust exports',
  iso27001: 'ISO 27001 starter pack',
  customer_questionnaires: 'Questionnaire assist',
};

function defaultStatus(option: ComplianceFrameworkSelectionOption): ComplianceFrameworkSelectionStatus {
  return option.runtime_support === 'readiness' ? 'active' : 'evaluating';
}

function supportLabel(value: string) {
  if (value === 'readiness') return 'readiness live';
  if (value === 'catalog') return 'catalog ready';
  if (value === 'starter') return 'starter pack';
  if (value === 'workflow') return 'workflow support';
  return value.replace(/_/g, ' ');
}

function supportClasses(value: string) {
  if (value === 'readiness') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (value === 'catalog') {
    return 'border-blue-200 bg-blue-50 text-blue-700';
  }
  if (value === 'starter' || value === 'workflow') {
    return 'border-amber-200 bg-amber-50 text-amber-700';
  }
  return 'border-border-faint bg-surface-hover text-text-muted';
}

function buildDraft(data: Awaited<ReturnType<typeof getComplianceFrameworkSelections>> | undefined) {
  const draft: Record<string, DraftSelection> = {};

  for (const option of data?.available_frameworks || []) {
    draft[option.framework_id] = {
      selected: false,
      status: defaultStatus(option),
      target_date: null,
    };
  }

  for (const selection of data?.items || []) {
    draft[selection.framework_id] = {
      selected: selection.status !== 'inactive',
      status: selection.status,
      target_date: selection.target_date || null,
    };
  }

  return draft;
}

function selectedCount(draft: Record<string, DraftSelection>) {
  return Object.values(draft).filter((item) => item.selected).length;
}

export function FrameworkSelectionPanel({ editable }: { editable: boolean }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<Record<string, DraftSelection>>({});

  const { data, isLoading, error } = useQuery({
    queryKey: ['compliance-framework-selections'],
    queryFn: getComplianceFrameworkSelections,
  });

  useEffect(() => {
    setDraft(buildDraft(data));
  }, [data]);

  const options = data?.available_frameworks || [];
  const activeCount = selectedCount(draft);
  const selectedFrameworkNames = useMemo(
    () =>
      options
        .filter((option) => draft[option.framework_id]?.selected)
        .map((option) => option.framework_name),
    [draft, options]
  );

  const updateMutation = useMutation({
    mutationFn: async () => {
      const selections = options
        .filter((option) => draft[option.framework_id]?.selected)
        .map((option, index) => ({
          framework_id: option.framework_id,
          status: draft[option.framework_id]?.status || defaultStatus(option),
          priority: index + 1,
          target_date: draft[option.framework_id]?.target_date || null,
        }));

      if (selections.length === 0) {
        throw new Error('Select at least one framework.');
      }

      return updateComplianceFrameworkSelections({ selections });
    },
    onSuccess: (payload) => {
      setDraft(buildDraft(payload));
      queryClient.setQueryData(['compliance-framework-selections'], payload);
      queryClient.invalidateQueries({ queryKey: ['compliance-dashboard'] });
      toast.success('Framework selections saved.');
    },
    onError: (mutationError: any) => {
      toast.error(mutationError?.response?.data?.detail || mutationError?.message || 'Failed to save selections.');
    },
  });

  function toggleFramework(option: ComplianceFrameworkSelectionOption) {
    if (!editable) return;
    setDraft((current) => {
      const existing = current[option.framework_id] || {
        selected: false,
        status: defaultStatus(option),
        target_date: null,
      };

      return {
        ...current,
        [option.framework_id]: {
          ...existing,
          selected: !existing.selected,
          status: existing.status === 'inactive' ? defaultStatus(option) : existing.status,
        },
      };
    });
  }

  function updateStatus(option: ComplianceFrameworkSelectionOption, status: ComplianceFrameworkSelectionStatus) {
    if (!editable) return;
    setDraft((current) => ({
      ...current,
      [option.framework_id]: {
        selected: status !== 'inactive',
        target_date: current[option.framework_id]?.target_date || null,
        status,
      },
    }));
  }

  function updateTargetDate(option: ComplianceFrameworkSelectionOption, targetDate: string) {
    if (!editable) return;
    setDraft((current) => ({
      ...current,
      [option.framework_id]: {
        selected: true,
        status: current[option.framework_id]?.status || defaultStatus(option),
        target_date: targetDate || null,
      },
    }));
  }

  return (
    <section className="mb-8 rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-text-muted">Framework scope</p>
          <h2 className="mt-1 text-2xl font-bold text-text-main">Selected Frameworks</h2>
          <p className="mt-1 text-sm text-text-muted">
            {selectedFrameworkNames.length > 0
              ? selectedFrameworkNames.join(', ')
              : 'No framework selections loaded yet.'}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-border-faint bg-surface-hover px-3 py-1.5 text-sm text-text-muted">
            {activeCount} selected
          </span>
          {!editable ? (
            <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-700">
              <ExclamationTriangleIcon className="mr-1.5 h-4 w-4" />
              picker disabled
            </span>
          ) : null}
        </div>
      </div>

      {!editable ? (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Framework selections are shown read-only in this runtime. Enable the multi-framework rollout flag to edit scope.
        </div>
      ) : null}

      {isLoading ? (
        <div className="mt-5 rounded-lg border border-dashed border-border-faint p-5 text-sm text-text-muted">
          Loading framework selections...
        </div>
      ) : error ? (
        <div className="mt-5 rounded-lg border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
          Failed to load framework selections.
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-1 xl:grid-cols-2 gap-4">
          {options.map((option) => {
            const state = draft[option.framework_id] || {
              selected: false,
              status: defaultStatus(option),
              target_date: null,
            };
            const reportLabel = SUPPORTED_REPORTS[option.framework_id] || 'Report templates pending';
            const evidenceLabel =
              option.runtime_support === 'readiness'
                ? 'Readiness signals available'
                : 'Evidence requirements pending';

            return (
              <div
                key={option.framework_id}
                className={`rounded-lg border p-4 transition-colors ${
                  state.selected
                    ? 'border-primary/40 bg-primary/5'
                    : 'border-border-faint bg-surface-hover'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      aria-label={`Select ${option.framework_name}`}
                      checked={state.selected}
                      disabled={!editable}
                      onChange={() => toggleFramework(option)}
                      className="mt-1 h-4 w-4 rounded border-border-faint text-primary focus:ring-primary disabled:opacity-50"
                    />
                    <span className="min-w-0">
                      <span className="block text-base font-semibold text-text-main">{option.framework_name}</span>
                      <span className="mt-1 block text-sm text-text-muted">{option.description}</span>
                    </span>
                  </label>
                  {state.selected ? (
                    <CheckCircleIcon className="h-6 w-6 flex-shrink-0 text-primary" />
                  ) : (
                    <ClockIcon className="h-6 w-6 flex-shrink-0 text-text-muted" />
                  )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <span className={`rounded-full border px-2.5 py-1 font-medium ${supportClasses(option.runtime_support)}`}>
                    {supportLabel(option.runtime_support)}
                  </span>
                  <span className="rounded-full border border-border-faint bg-surface-card px-2.5 py-1 text-text-muted">
                    {option.control_count} controls
                  </span>
                  <span className="rounded-full border border-border-faint bg-surface-card px-2.5 py-1 text-text-muted">
                    {reportLabel}
                  </span>
                  <span className="rounded-full border border-border-faint bg-surface-card px-2.5 py-1 text-text-muted">
                    {evidenceLabel}
                  </span>
                </div>

                {state.selected ? (
                  <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div>
                      <label htmlFor={`${option.framework_id}-status`} className="mb-1 block text-xs text-text-muted">
                        Status
                      </label>
                      <select
                        id={`${option.framework_id}-status`}
                        value={state.status}
                        disabled={!editable}
                        onChange={(event) =>
                          updateStatus(option, event.target.value as ComplianceFrameworkSelectionStatus)
                        }
                        className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
                      >
                        <option value="active">Active</option>
                        <option value="evaluating">Evaluating</option>
                        <option value="inactive">Inactive</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor={`${option.framework_id}-target-date`} className="mb-1 block text-xs text-text-muted">
                        Target date
                      </label>
                      <input
                        id={`${option.framework_id}-target-date`}
                        type="date"
                        value={state.target_date || ''}
                        disabled={!editable}
                        onChange={(event) => updateTargetDate(option, event.target.value)}
                        className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-5 flex justify-end">
        <button
          type="button"
          disabled={!editable || updateMutation.isPending || activeCount === 0}
          onClick={() => updateMutation.mutate()}
          className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
        >
          {updateMutation.isPending ? <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" /> : null}
          Save framework scope
        </button>
      </div>
    </section>
  );
}

