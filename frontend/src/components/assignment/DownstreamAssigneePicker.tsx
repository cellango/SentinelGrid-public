'use client';

import { useEffect, useState, type ReactNode } from 'react';
import {
  searchTicketingAssignees,
  type TicketAssigneeIdentifierType,
  type TicketingAssigneeSearchResult,
  type TicketingProvider,
} from '@/lib/api/onboarding';

const DIRECTORY_PROVIDER_LABELS: Record<TicketingProvider, string> = {
  internal: 'internal queue',
  jira: 'Jira',
  servicenow: 'ServiceNow',
};

function getAssigneeFieldLabel(
  provider?: TicketingProvider | null,
  identifierType?: TicketAssigneeIdentifierType | null
) {
  if (provider === 'jira') {
    if (identifierType === 'account_id') return 'Jira account ID';
    if (identifierType === 'email') return 'Jira assignee email';
    return 'Jira username';
  }
  if (provider === 'servicenow') {
    return identifierType === 'sys_id' ? 'ServiceNow sys_id' : 'ServiceNow username';
  }
  return 'Assignee';
}

function getAssigneePlaceholder(
  provider?: TicketingProvider | null,
  identifierType?: TicketAssigneeIdentifierType | null
) {
  if (provider === 'jira') {
    if (identifierType === 'account_id') {
      return '712020:8f3f3cde-1234-4567-89ab-123456789abc';
    }
    if (identifierType === 'email') {
      return 'owner@company.com';
    }
    return 'jira.username';
  }
  if (provider === 'servicenow') {
    return identifierType === 'sys_id'
      ? '6816f79cc0a8016401c5a33be04be441'
      : 'secops.user';
  }
  return 'owner@company.com';
}

export interface DownstreamAssigneePickerProps {
  currentValue?: string | null;
  onSave: (assignedTo: string) => Promise<void>;
  saving?: boolean;
  title?: string;
  description?: string;
  saveLabel?: string;
  searchPlaceholder?: string;
  helperText?: string;
  currentLabelPrefix?: string;
  secondaryActions?: ReactNode;
  compact?: boolean;
  searchLimit?: number;
  successMessageBuilder?: (selectedLabel: string | null, assignedTo: string) => string;
}

export default function DownstreamAssigneePicker({
  currentValue,
  onSave,
  saving = false,
  title = 'Assignment',
  description = 'Search the configured downstream directory, then save the real assignee identifier.',
  saveLabel = 'Save assignee',
  searchPlaceholder = 'Search by name, username, or email',
  helperText = 'This uses the customer-managed Jira or ServiceNow handoff configuration when available.',
  currentLabelPrefix = 'Current:',
  secondaryActions,
  compact = false,
  searchLimit = 8,
  successMessageBuilder,
}: DownstreamAssigneePickerProps) {
  const [assigneeInput, setAssigneeInput] = useState(currentValue || '');
  const [lookupQuery, setLookupQuery] = useState('');
  const [lookupResults, setLookupResults] = useState<TicketingAssigneeSearchResult[]>([]);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [selectedAssigneeLabel, setSelectedAssigneeLabel] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [directoryProvider, setDirectoryProvider] = useState<TicketingProvider | null>(null);
  const [directoryIdentifierType, setDirectoryIdentifierType] =
    useState<TicketAssigneeIdentifierType | null>(null);

  useEffect(() => {
    setAssigneeInput(currentValue || '');
    setSelectedAssigneeLabel(null);
    setSaveMessage(null);
    setSaveError(null);
  }, [currentValue]);

  useEffect(() => {
    const query = lookupQuery.trim();
    if (query.length === 0) {
      setLookupResults([]);
      setLookupError(null);
      return;
    }
    if (query.length < 2) {
      setLookupResults([]);
      setLookupError('Enter at least two characters to search the downstream ticket directory.');
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        setLookupLoading(true);
        setLookupError(null);
        const response = await searchTicketingAssignees({
          query,
          limit: searchLimit,
        });
        if (!cancelled) {
          setDirectoryProvider(response.provider);
          setDirectoryIdentifierType(response.assigneeIdentifierType);
          setLookupResults(response.results || []);
          if ((response.results || []).length === 0) {
            setLookupError('No matching downstream assignees were found.');
          }
        }
      } catch (error: any) {
        if (!cancelled) {
          setLookupResults([]);
          setLookupError(error.message || 'Assignee lookup failed');
        }
      } finally {
        if (!cancelled) {
          setLookupLoading(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [lookupQuery, searchLimit]);

  const handleAssigneeSelect = (result: TicketingAssigneeSearchResult) => {
    setAssigneeInput(result.value);
    setSelectedAssigneeLabel(result.label);
    setLookupQuery(result.label);
    setLookupResults([]);
    setLookupError(null);
  };

  const handleSave = async () => {
    try {
      const trimmed = assigneeInput.trim();
      setSaveMessage(null);
      setSaveError(null);
      await onSave(trimmed);
      setSaveMessage(
        successMessageBuilder
          ? successMessageBuilder(selectedAssigneeLabel, trimmed)
          : `Assignment updated${selectedAssigneeLabel ? ` to ${selectedAssigneeLabel}` : ''}.`
      );
    } catch (error: any) {
      setSaveError(error?.message || 'Failed to update assignment.');
    }
  };

  return (
    <div>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">{title}</p>
          <p className="mt-1 text-sm text-text-muted">{description}</p>
        </div>
        {directoryProvider && (
          <span className="inline-flex items-center rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-300">
            {DIRECTORY_PROVIDER_LABELS[directoryProvider]} lookup
          </span>
        )}
      </div>

      <div className={compact ? 'mt-4 space-y-4' : 'mt-4 grid gap-4 xl:grid-cols-[1fr,1fr]'}>
        <div>
          <label className="block text-sm font-medium text-text-main mb-1">
            Search downstream assignees
          </label>
          <input
            type="text"
            value={lookupQuery}
            onChange={(event) => setLookupQuery(event.target.value)}
            className="w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.85)] px-3 py-2 text-sm text-text-main"
            placeholder={searchPlaceholder}
          />
          <p className="mt-2 text-xs text-text-muted">{helperText}</p>

          {lookupLoading && (
            <div className="mt-3 rounded-lg border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.55)] px-3 py-2 text-sm text-text-muted">
              Searching downstream directory...
            </div>
          )}

          {lookupError && (
            <div className="mt-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-100">
              {lookupError}
            </div>
          )}

          {lookupResults.length > 0 && (
            <div className="mt-3 space-y-2 rounded-lg border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.55)] p-3">
              {lookupResults.map((result) => (
                <button
                  key={`${result.identifierType}:${result.value}`}
                  type="button"
                  onClick={() => handleAssigneeSelect(result)}
                  className="block w-full rounded-lg border border-[rgba(148,163,184,0.12)] bg-[rgba(15,23,42,0.72)] px-3 py-2 text-left transition-colors hover:border-cyan-500/40 hover:bg-cyan-500/5"
                >
                  <p className="text-sm font-medium text-text-main">{result.label}</p>
                  {result.description && (
                    <p className="mt-1 text-xs text-text-muted">{result.description}</p>
                  )}
                  <p className="mt-1 text-xs text-cyan-300">{result.value}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-text-main mb-1">
            {getAssigneeFieldLabel(directoryProvider, directoryIdentifierType)}
          </label>
          <input
            type="text"
            value={assigneeInput}
            onChange={(event) => {
              setSelectedAssigneeLabel(null);
              setSaveMessage(null);
              setSaveError(null);
              setAssigneeInput(event.target.value);
            }}
            className="w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.85)] px-3 py-2 text-sm text-text-main"
            placeholder={getAssigneePlaceholder(directoryProvider, directoryIdentifierType)}
          />
          {selectedAssigneeLabel && (
            <div className="mt-3 rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100">
              Selected <span className="font-medium">{selectedAssigneeLabel}</span> for assignment.
            </div>
          )}
          {directoryProvider === 'jira' && directoryIdentifierType === 'account_id' && (
            <p className="mt-2 text-xs text-text-muted">
              Jira Cloud assignment is most reliable when you store the Atlassian account ID.
            </p>
          )}
          {currentValue && (
            <p className="mt-2 text-xs text-text-muted">
              {currentLabelPrefix} {currentValue}
            </p>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={!assigneeInput.trim() || saving}
              className="px-4 py-2 bg-primary text-bg rounded-lg text-sm font-medium hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? 'Saving...' : saveLabel}
            </button>
            {secondaryActions}
          </div>

          {saveMessage && (
            <p className="mt-3 text-xs text-green-300">{saveMessage}</p>
          )}
          {saveError && (
            <p className="mt-3 text-xs text-red-300">{saveError}</p>
          )}
        </div>
      </div>
    </div>
  );
}
