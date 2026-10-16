'use client';

import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import DownstreamAssigneePicker from '@/components/assignment/DownstreamAssigneePicker';
import {
  addHoursFromNow,
  formatIssueDueDate,
  getIssueSlaLabel,
  getIssueSlaState,
  toDateTimeLocalInputValue,
} from '@/lib/issues/sla';

interface IssueOwnershipSlaPanelProps {
  issueLabel: string;
  currentOwner?: string | null;
  currentDueDate?: string | null;
  onOwnerSave: (assignedTo: string) => Promise<void>;
  onDueDateSave: (dueDate: string | null) => Promise<void>;
  ownerSaving?: boolean;
  dueDateSaving?: boolean;
  assignmentTitle?: string;
  assignmentDescription?: string;
  assignmentSaveLabel?: string;
  dueDateTitle?: string;
  dueDateDescription?: string;
}

function slaTone(state: ReturnType<typeof getIssueSlaState>) {
  switch (state) {
    case 'overdue':
      return 'border-rose-500/40 bg-rose-500/15 text-rose-200';
    case 'due_soon':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-200';
    case 'on_track':
      return 'border-emerald-500/40 bg-emerald-500/15 text-emerald-200';
    default:
      return 'border-slate-500/30 bg-slate-500/10 text-slate-200';
  }
}

function buildPresetOptions(issueLabel: string) {
  const lower = issueLabel.toLowerCase();
  if (lower.includes('incident')) {
    return [
      { label: '2h', hours: 2 },
      { label: '8h', hours: 8 },
      { label: '24h', hours: 24 },
      { label: '72h', hours: 72 },
    ];
  }
  if (lower.includes('alert')) {
    return [
      { label: '1h', hours: 1 },
      { label: '4h', hours: 4 },
      { label: '24h', hours: 24 },
      { label: '72h', hours: 72 },
    ];
  }
  return [
    { label: '4h', hours: 4 },
    { label: '24h', hours: 24 },
    { label: '72h', hours: 72 },
    { label: '7d', hours: 24 * 7 },
  ];
}

export default function IssueOwnershipSlaPanel({
  issueLabel,
  currentOwner,
  currentDueDate,
  onOwnerSave,
  onDueDateSave,
  ownerSaving = false,
  dueDateSaving = false,
  assignmentTitle = 'Ownership',
  assignmentDescription = 'Set the operator or downstream owner who is accountable for moving this issue forward.',
  assignmentSaveLabel = 'Save owner',
  dueDateTitle = 'SLA target',
  dueDateDescription = 'Set a due date so the team can see which issues are overdue, due soon, or safely on track.',
}: IssueOwnershipSlaPanelProps) {
  const [dueDateInput, setDueDateInput] = useState(toDateTimeLocalInputValue(currentDueDate));
  const [dueDateMessage, setDueDateMessage] = useState<string | null>(null);
  const [dueDateError, setDueDateError] = useState<string | null>(null);
  const slaState = useMemo(() => getIssueSlaState(currentDueDate), [currentDueDate]);
  const slaLabel = useMemo(() => getIssueSlaLabel(currentDueDate), [currentDueDate]);
  const presets = useMemo(() => buildPresetOptions(issueLabel), [issueLabel]);

  useEffect(() => {
    setDueDateInput(toDateTimeLocalInputValue(currentDueDate));
    setDueDateMessage(null);
    setDueDateError(null);
  }, [currentDueDate]);

  const handleDueDateSave = async (nextDueDate: string | null) => {
    try {
      setDueDateMessage(null);
      setDueDateError(null);
      await onDueDateSave(nextDueDate);
      setDueDateMessage(nextDueDate ? 'SLA target updated.' : 'SLA target cleared.');
    } catch (error: any) {
      setDueDateError(error?.message || 'Failed to update SLA target.');
    }
  };

  return (
    <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-main">Ownership and SLA</h2>
          <p className="mt-1 text-sm text-text-muted">
            Keep {issueLabel.toLowerCase()} work accountable with one owner and one visible target.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
            {currentOwner || 'Unassigned'}
          </span>
          <span
            className={clsx(
              'rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.12em]',
              slaTone(slaState)
            )}
          >
            {slaLabel}
          </span>
        </div>
      </div>

      <div className="mt-6 grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.72)] p-4">
          <DownstreamAssigneePicker
            currentValue={currentOwner}
            onSave={onOwnerSave}
            saving={ownerSaving}
            title={assignmentTitle}
            description={assignmentDescription}
            saveLabel={assignmentSaveLabel}
            successMessageBuilder={(selectedLabel) =>
              `${issueLabel} ownership updated${selectedLabel ? ` to ${selectedLabel}` : ''}.`
            }
          />
        </div>

        <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.72)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            {dueDateTitle}
          </p>
          <p className="mt-1 text-sm text-text-muted">{dueDateDescription}</p>

          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {presets.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => {
                  setDueDateInput(toDateTimeLocalInputValue(addHoursFromNow(preset.hours)));
                  setDueDateMessage(null);
                  setDueDateError(null);
                }}
                className="rounded-lg border border-[rgba(148,163,184,0.18)] bg-[rgba(15,23,42,0.85)] px-3 py-2 text-sm text-text-main hover:border-primary/40"
              >
                Set {preset.label}
              </button>
            ))}
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-text-main mb-1">Due date and time</label>
            <input
              type="datetime-local"
              value={dueDateInput}
              onChange={(event) => {
                setDueDateInput(event.target.value);
                setDueDateMessage(null);
                setDueDateError(null);
              }}
              className="w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.85)] px-3 py-2 text-sm text-text-main"
            />
            <p className="mt-2 text-xs text-text-muted">
              Current target: {formatIssueDueDate(currentDueDate)}
            </p>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                const nextDueDate = dueDateInput ? new Date(dueDateInput).toISOString() : null;
                void handleDueDateSave(nextDueDate);
              }}
              disabled={dueDateSaving || (!dueDateInput && !currentDueDate)}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-bg disabled:opacity-60"
            >
              {dueDateSaving ? 'Saving...' : 'Save SLA target'}
            </button>
            <button
              type="button"
              onClick={() => {
                setDueDateInput('');
                void handleDueDateSave(null);
              }}
              disabled={dueDateSaving || !currentDueDate}
              className="rounded-lg border border-[rgba(148,163,184,0.2)] px-4 py-2 text-sm font-medium text-text-main disabled:opacity-60"
            >
              Clear target
            </button>
          </div>

          {dueDateMessage && <p className="mt-3 text-xs text-green-300">{dueDateMessage}</p>}
          {dueDateError && <p className="mt-3 text-xs text-red-300">{dueDateError}</p>}
        </div>
      </div>
    </div>
  );
}
