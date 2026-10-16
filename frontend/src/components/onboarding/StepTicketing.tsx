'use client';

import Link from 'next/link';
import React, { useEffect, useMemo, useState } from 'react';
import {
  type TicketAssigneeIdentifierType,
  type TicketingAssigneeSearchResult,
  connectTicketing,
  recheckHealth,
  searchTicketingAssignees,
  type TicketAssignmentMode,
  type TicketingConnectionRequest,
  type TicketingProvider,
} from '@/lib/api/onboarding';
import { recordOnboardingCtaClick } from '@/lib/onboarding/metrics';

interface StepTicketingProps {
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  initialHealth?: any;
}

type TicketingHealth = {
  status?: 'healthy' | 'degraded' | 'unknown' | 'unreachable';
  checked_at?: string | null;
  message?: string | null;
  warnings?: string[];
  provider?: string | null;
};

const PROVIDER_OPTIONS: Array<{
  id: TicketingProvider;
  title: string;
  eyebrow: string;
  description: string;
}> = [
  {
    id: 'internal',
    title: 'SentinelGrid queue',
    eyebrow: 'Fastest path',
    description:
      'Keep triage inside SentinelGrid and optionally fan out notifications to Slack while the team gets established.',
  },
  {
    id: 'jira',
    title: 'Jira',
    eyebrow: 'Most common',
    description:
      'Route findings into a Jira project so owners can work from the same backlog they already use for engineering and IT.',
  },
  {
    id: 'servicenow',
    title: 'ServiceNow',
    eyebrow: 'ITSM workflow',
    description:
      'Use when the security handoff needs to land in an established ServiceNow incident or service-management process.',
  },
];

const ASSIGNMENT_OPTIONS: Array<{
  id: TicketAssignmentMode;
  label: string;
  description: string;
}> = [
  {
    id: 'service_owner',
    label: 'Service owner',
    description: 'Best default for SMBs. Route incidents to the owner SentinelGrid maps to the affected service.',
  },
  {
    id: 'project_default',
    label: 'Project default',
    description: 'Let Jira or ServiceNow apply the queue or assignment group defaults configured in that system.',
  },
  {
    id: 'named_owner',
    label: 'Named owner',
    description: 'Always hand off to a specific person or shared queue while the team is still small.',
  },
];

const ISSUE_TYPE_DEFAULTS: Record<TicketingProvider, string> = {
  internal: 'Incident',
  jira: 'Incident',
  servicenow: 'Security Incident',
};

const URL_PLACEHOLDERS: Record<Exclude<TicketingProvider, 'internal'>, string> = {
  jira: 'https://your-domain.atlassian.net',
  servicenow: 'https://your-instance.service-now.com',
};

const ASSIGNEE_IDENTIFIER_DEFAULTS: Record<TicketingProvider, TicketAssigneeIdentifierType> = {
  internal: 'username',
  jira: 'account_id',
  servicenow: 'username',
};

const ASSIGNEE_IDENTIFIER_OPTIONS: Record<
  TicketingProvider,
  Array<{
    id: TicketAssigneeIdentifierType;
    label: string;
    description: string;
  }>
> = {
  internal: [
    {
      id: 'username',
      label: 'Queue name',
      description: 'Use a queue or owner label when SentinelGrid is the primary workflow.',
    },
  ],
  jira: [
    {
      id: 'account_id',
      label: 'Account ID',
      description: 'Recommended for Jira Cloud. Use the Atlassian accountId for the owner.',
    },
    {
      id: 'email',
      label: 'Email',
      description: 'Useful for some Jira Server/Data Center setups. Jira Cloud may reject it.',
    },
    {
      id: 'username',
      label: 'Username',
      description: 'Use only if your Jira deployment still supports name-based assignment.',
    },
  ],
  servicenow: [
    {
      id: 'username',
      label: 'Username',
      description: 'Recommended default. Use the ServiceNow user_name for the owner.',
    },
    {
      id: 'sys_id',
      label: 'sys_id',
      description: 'Use the ServiceNow user sys_id when that is the cleanest internal identifier.',
    },
  ],
};

const ASSIGNEE_PLACEHOLDERS: Record<TicketingProvider, Record<string, string>> = {
  internal: {
    username: 'SECOPS-L1',
  },
  jira: {
    account_id: '712020:8f3f3cde-1234-4567-89ab-123456789abc',
    email: 'owner@company.com',
    username: 'jira.username',
  },
  servicenow: {
    username: 'secops.user',
    sys_id: '6816f79cc0a8016401c5a33be04be441',
  },
};

const ASSIGNEE_SEARCH_PLACEHOLDERS: Record<TicketingProvider, string> = {
  internal: 'Search is only available for external ticketing systems.',
  jira: 'Search Jira users by name or email',
  servicenow: 'Search ServiceNow users by name, username, or email',
};

function normalizeHealth(health?: any): TicketingHealth | null {
  if (!health || typeof health !== 'object') {
    return null;
  }

  return {
    status: health.status || 'unknown',
    checked_at: health.checked_at || health.checkedAt || null,
    message: health.message || null,
    warnings: Array.isArray(health.warnings) ? health.warnings : [],
    provider: health.provider || null,
  };
}

function statusStyles(status?: TicketingHealth['status']) {
  switch (status) {
    case 'healthy':
      return {
        wrapper: 'border-green-500/30 bg-green-500/10 text-green-200',
        badge: 'border-green-500/40 bg-green-500/15 text-green-300',
        label: 'Healthy',
      };
    case 'degraded':
      return {
        wrapper: 'border-yellow-500/30 bg-yellow-500/10 text-yellow-100',
        badge: 'border-yellow-500/40 bg-yellow-500/15 text-yellow-300',
        label: 'Needs attention',
      };
    case 'unreachable':
      return {
        wrapper: 'border-red-500/30 bg-red-500/10 text-red-100',
        badge: 'border-red-500/40 bg-red-500/15 text-red-300',
        label: 'Unreachable',
      };
    default:
      return {
        wrapper: 'border-slate-700 bg-slate-900/60 text-slate-200',
        badge: 'border-slate-600 bg-slate-800 text-slate-300',
        label: 'Not validated',
      };
  }
}

export default function StepTicketing({
  onNext,
  onBack,
  onSkip,
  initialHealth,
}: StepTicketingProps) {
  const [provider, setProvider] = useState<TicketingProvider>('internal');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<TicketingHealth | null>(normalizeHealth(initialHealth));
  const [form, setForm] = useState<TicketingConnectionRequest>({
    provider: 'internal',
    socManaged: false,
    issue_type: ISSUE_TYPE_DEFAULTS.internal,
    assignment_mode: 'service_owner',
    assignee_identifier_type: ASSIGNEE_IDENTIFIER_DEFAULTS.internal,
    auto_create_tickets: true,
    notify_slack: true,
    slack_channel: '#security-alerts',
  });
  const [assigneeQuery, setAssigneeQuery] = useState('');
  const [assigneeResults, setAssigneeResults] = useState<TicketingAssigneeSearchResult[]>([]);
  const [assigneeLookupLoading, setAssigneeLookupLoading] = useState(false);
  const [assigneeLookupError, setAssigneeLookupError] = useState<string | null>(null);
  const [selectedAssigneeLabel, setSelectedAssigneeLabel] = useState<string | null>(null);

  useEffect(() => {
    const normalized = normalizeHealth(initialHealth);
    setHealth(normalized);

    const initialProvider = normalized?.provider as TicketingProvider | undefined;
    if (initialProvider && PROVIDER_OPTIONS.some((option) => option.id === initialProvider)) {
      setProvider(initialProvider);
      setForm((current) => ({
        ...current,
        provider: initialProvider,
        issue_type:
          current.issue_type && current.issue_type !== ISSUE_TYPE_DEFAULTS[current.provider || 'internal']
            ? current.issue_type
            : ISSUE_TYPE_DEFAULTS[initialProvider],
        assignee_identifier_type:
          current.assignee_identifier_type &&
          current.assignee_identifier_type !== ASSIGNEE_IDENTIFIER_DEFAULTS[current.provider || 'internal']
            ? current.assignee_identifier_type
            : ASSIGNEE_IDENTIFIER_DEFAULTS[initialProvider],
      }));
    }
  }, [initialHealth]);

  const requiresExternalConfig = provider !== 'internal';
  const requiresNamedOwner = form.assignment_mode === 'named_owner';
  const slackEnabled = form.notify_slack === true;
  const selectedProvider = PROVIDER_OPTIONS.find((option) => option.id === provider) || PROVIDER_OPTIONS[0];
  const assigneeIdentifierType =
    form.assignee_identifier_type || ASSIGNEE_IDENTIFIER_DEFAULTS[provider];
  const assigneeOptions = ASSIGNEE_IDENTIFIER_OPTIONS[provider];
  const healthMeta = statusStyles(health?.status);

  const handoffSummary = useMemo(() => {
    const destination =
      provider === 'internal'
        ? 'SentinelGrid requests queue'
        : `${selectedProvider.title} ${form.project ? `(${form.project})` : 'queue'}`;
    const assignment =
      form.assignment_mode === 'named_owner'
        ? form.default_assignee || 'named owner'
        : form.assignment_mode === 'project_default'
        ? 'project defaults'
        : 'service owner mapping';

    return [
      form.auto_create_tickets ? `Auto-create ${form.issue_type || 'incident'} records in ${destination}.` : `Keep ${destination} ready for analyst-created tickets only.`,
      `Assign to ${assignment}.`,
      slackEnabled
        ? `Notify ${form.slack_channel || 'Slack'} when SentinelGrid opens or escalates a case.`
        : 'Keep collaboration in the ticketing system only.',
    ];
  }, [
    form.assignment_mode,
    form.auto_create_tickets,
    form.assignee_identifier_type,
    form.default_assignee,
    form.issue_type,
    form.project,
    form.slack_channel,
    provider,
    selectedProvider.title,
    slackEnabled,
  ]);

  const updateForm = (patch: Partial<TicketingConnectionRequest>) => {
    setForm((current) => ({ ...current, ...patch }));
  };

  useEffect(() => {
    if (!requiresNamedOwner || provider === 'internal') {
      setAssigneeQuery('');
      setAssigneeResults([]);
      setAssigneeLookupError(null);
      setSelectedAssigneeLabel(null);
    }
  }, [provider, requiresNamedOwner]);

  useEffect(() => {
    const query = assigneeQuery.trim();
    if (!requiresNamedOwner || provider === 'internal') {
      return;
    }
    if (query.length === 0) {
      setAssigneeResults([]);
      setAssigneeLookupError(null);
      return;
    }
    if (query.length < 2) {
      setAssigneeResults([]);
      setAssigneeLookupError('Enter at least two characters to search the downstream directory.');
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        setAssigneeLookupLoading(true);
        setAssigneeLookupError(null);
        const response = await searchTicketingAssignees({
          query,
          provider,
          url: form.url || undefined,
          project: form.project || undefined,
          api_key: form.api_key || undefined,
          assignee_identifier_type: assigneeIdentifierType,
          limit: 8,
        });
        if (!cancelled) {
          setAssigneeResults(response.results || []);
          if ((response.results || []).length === 0) {
            setAssigneeLookupError('No matching assignees were found for the selected identifier type.');
          }
        }
      } catch (err: any) {
        if (!cancelled) {
          setAssigneeResults([]);
          setAssigneeLookupError(err.message || 'Assignee lookup failed');
        }
      } finally {
        if (!cancelled) {
          setAssigneeLookupLoading(false);
        }
      }
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [
    assigneeIdentifierType,
    assigneeQuery,
    form.api_key,
    form.project,
    form.url,
    provider,
    requiresNamedOwner,
  ]);

  useEffect(() => {
    if (!form.default_assignee) {
      setSelectedAssigneeLabel(null);
    }
  }, [form.default_assignee]);

  const handleProviderSelect = (nextProvider: TicketingProvider) => {
    setProvider(nextProvider);
    setError(null);
    setHealth(null);
    setAssigneeQuery('');
    setAssigneeResults([]);
    setAssigneeLookupError(null);
    setSelectedAssigneeLabel(null);
    setForm((current) => {
      const issueTypeShouldChange =
        !current.issue_type || current.issue_type === ISSUE_TYPE_DEFAULTS[current.provider || 'internal'];

      return {
        ...current,
        provider: nextProvider,
        issue_type: issueTypeShouldChange
          ? ISSUE_TYPE_DEFAULTS[nextProvider]
          : current.issue_type,
        assignee_identifier_type:
          !current.assignee_identifier_type ||
          current.assignee_identifier_type === ASSIGNEE_IDENTIFIER_DEFAULTS[current.provider || 'internal']
            ? ASSIGNEE_IDENTIFIER_DEFAULTS[nextProvider]
            : current.assignee_identifier_type,
        url: nextProvider === 'internal' ? undefined : current.url,
        api_key: nextProvider === 'internal' ? undefined : current.api_key,
      };
    });

    recordOnboardingCtaClick({
      source: 'onboarding_ticketing_provider',
      target: nextProvider,
      stepId: 'ticketing',
    });
  };

  const handleAssigneeSelect = (result: TicketingAssigneeSearchResult) => {
    updateForm({ default_assignee: result.value });
    setSelectedAssigneeLabel(result.label);
    setAssigneeQuery(result.label);
    setAssigneeResults([]);
    setAssigneeLookupError(null);

    recordOnboardingCtaClick({
      source: 'onboarding_ticketing_assignee_lookup',
      target: result.value,
      stepId: 'ticketing',
    });
  };

  const validateResponse = (nextHealth: TicketingHealth | null, fallbackMessage: string) => {
    if (nextHealth?.status === 'healthy') {
      setError(null);
      onNext();
      return;
    }

    setError(
      nextHealth?.warnings?.[0] ||
        nextHealth?.message ||
        fallbackMessage
    );
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await connectTicketing({
        ...form,
        provider,
        socManaged: false,
        url: requiresExternalConfig ? form.url || undefined : undefined,
        project: form.project || undefined,
        api_key: requiresExternalConfig ? form.api_key || undefined : undefined,
        default_assignee: requiresNamedOwner ? form.default_assignee || undefined : undefined,
        assignee_identifier_type: requiresNamedOwner ? assigneeIdentifierType : undefined,
        slack_channel: slackEnabled ? form.slack_channel || undefined : undefined,
        slack_webhook_url: slackEnabled ? form.slack_webhook_url || undefined : undefined,
      });

      const nextHealth = normalizeHealth(response?.health) || {
        status: response?.status || 'unknown',
      };
      setHealth(nextHealth);
      validateResponse(
        nextHealth,
        response?.message || 'Ticketing settings were saved, but the handoff still needs attention.'
      );
    } catch (err: any) {
      setError(err.message || 'Failed to save ticketing settings');
      setHealth((current) =>
        current || {
          status: 'unreachable',
        }
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRecheck = async () => {
    setLoading(true);
    setError(null);

    try {
      recordOnboardingCtaClick({
        source: 'onboarding_ticketing_recheck',
        target: provider,
        stepId: 'ticketing',
      });

      const response = await recheckHealth('ticketing');
      const nextHealth = normalizeHealth(response?.health);
      setHealth(nextHealth);

      if (nextHealth?.status !== 'healthy') {
        setError(
          nextHealth?.warnings?.[0] ||
            nextHealth?.message ||
            'Ticketing handoff still needs attention.'
        );
      }
    } catch (err: any) {
      setError(err.message || 'Health check failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100">Ticketing and collaboration handoff</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
          Define where SentinelGrid should send high-signal incidents, who should own them, and
          whether the team also needs Slack notifications during the first week of rollout.
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        {PROVIDER_OPTIONS.map((option) => {
          const selected = provider === option.id;

          return (
            <button
              key={option.id}
              type="button"
              onClick={() => handleProviderSelect(option.id)}
              className={`rounded-2xl border p-4 text-left transition-all ${
                selected
                  ? 'border-cyan-400 bg-cyan-400/10 shadow-[0_0_0_1px_rgba(34,211,238,0.16)]'
                  : 'border-slate-800 bg-slate-950/40 hover:border-slate-700'
              }`}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                {option.eyebrow}
              </p>
              <h3 className="mt-3 text-lg font-semibold text-slate-100">{option.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-300">{option.description}</p>
            </button>
          );
        })}
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className={`rounded-2xl border px-4 py-3 ${healthMeta.wrapper}`}>
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] opacity-80">
              Handoff health
            </p>
            <p className="mt-1 text-sm font-medium">
              {health?.message ||
                (health?.status === 'healthy'
                  ? 'Ticketing handoff is ready for use.'
                  : 'Save the routing details and validate the integration.')}
            </p>
            {health?.checked_at && (
              <p className="mt-1 text-xs opacity-80">
                Last checked {new Date(health.checked_at).toLocaleString()}.
              </p>
            )}
          </div>
          <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${healthMeta.badge}`}>
            {healthMeta.label}
          </span>
        </div>
        {health?.warnings && health.warnings.length > 0 && (
          <ul className="mt-3 space-y-1 text-sm opacity-90">
            {health.warnings.map((warning) => (
              <li key={warning}>• {warning}</li>
            ))}
          </ul>
        )}
      </div>

      <form onSubmit={handleSubmit} className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <div className="space-y-5 rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
          {requiresExternalConfig && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {provider === 'jira' ? 'Jira base URL' : 'ServiceNow instance URL'}
                </label>
                <input
                  type="url"
                  required
                  value={form.url || ''}
                  onChange={(event) => updateForm({ url: event.target.value })}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                  placeholder={URL_PLACEHOLDERS[provider as Exclude<TicketingProvider, 'internal'>]}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {provider === 'jira' ? 'Project key' : 'Assignment group / queue'}
                </label>
                <input
                  type="text"
                  required
                  value={form.project || ''}
                  onChange={(event) => updateForm({ project: event.target.value })}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                  placeholder={provider === 'jira' ? 'SECOPS' : 'Security Operations'}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  API token or authorization value
                </label>
                <input
                  type="password"
                  required
                  value={form.api_key || ''}
                  onChange={(event) => updateForm({ api_key: event.target.value })}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                  placeholder="Bearer ... or Basic ..."
                />
              </div>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Issue type
              </label>
              <input
                type="text"
                value={form.issue_type || ''}
                onChange={(event) => updateForm({ issue_type: event.target.value })}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                placeholder={ISSUE_TYPE_DEFAULTS[provider]}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Ticket creation
              </label>
              <select
                value={form.auto_create_tickets ? 'auto' : 'manual'}
                onChange={(event) => updateForm({ auto_create_tickets: event.target.value === 'auto' })}
                className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
              >
                <option value="auto">Open tickets automatically</option>
                <option value="manual">Manual analyst triage</option>
              </select>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-slate-100">Assignment routing</p>
                <p className="mt-1 text-sm leading-6 text-slate-300">
                  Decide whether SentinelGrid should hand incidents to the service owner, keep the
                  downstream queue defaults, or always assign a named owner while the team is still small.
                </p>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {ASSIGNMENT_OPTIONS.map((option) => (
                <label
                  key={option.id}
                  className={`block rounded-xl border p-3 transition-colors ${
                    form.assignment_mode === option.id
                      ? 'border-cyan-400 bg-cyan-400/10'
                      : 'border-slate-800 bg-slate-950/40'
                  }`}
                >
                  <div className="flex gap-3">
                    <input
                      type="radio"
                      name="assignment-mode"
                      checked={form.assignment_mode === option.id}
                      onChange={() => updateForm({ assignment_mode: option.id })}
                      className="mt-1 h-4 w-4 border-slate-600 bg-slate-950 text-cyan-400 focus:ring-cyan-400"
                    />
                    <div>
                      <p className="text-sm font-medium text-slate-100">{option.label}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-300">{option.description}</p>
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {requiresNamedOwner && (
              <div className="mt-4">
                {provider !== 'internal' && (
                  <div className="mb-4 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1">
                        {provider === 'jira' ? 'Jira assignee identifier' : 'ServiceNow assignee identifier'}
                      </label>
                      <select
                        value={assigneeIdentifierType}
                        onChange={(event) =>
                          {
                            setSelectedAssigneeLabel(null);
                            setAssigneeResults([]);
                            updateForm({
                              assignee_identifier_type: event.target.value as TicketAssigneeIdentifierType,
                              default_assignee: undefined,
                            });
                          }
                        }
                        className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                      >
                        {assigneeOptions.map((option) => (
                          <option key={option.id} value={option.id}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <p className="mt-2 text-xs leading-5 text-slate-400">
                        {assigneeOptions.find((option) => option.id === assigneeIdentifierType)?.description}
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-slate-300 mb-1">
                        Search downstream directory
                      </label>
                      <input
                        type="text"
                        value={assigneeQuery}
                        onChange={(event) => setAssigneeQuery(event.target.value)}
                        className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                        placeholder={ASSIGNEE_SEARCH_PLACEHOLDERS[provider]}
                      />
                      <p className="mt-2 text-xs leading-5 text-slate-400">
                        Search first, then select a result to fill the identifier field automatically.
                      </p>
                    </div>

                    {assigneeLookupLoading && (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/40 px-3 py-2 text-sm text-slate-300">
                        Searching {selectedProvider.title} for matching assignees...
                      </div>
                    )}

                    {assigneeLookupError && (
                      <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-100">
                        {assigneeLookupError}
                      </div>
                    )}

                    {assigneeResults.length > 0 && (
                      <div className="space-y-2 rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                        {assigneeResults.map((result) => (
                          <button
                            key={`${result.identifierType}:${result.value}`}
                            type="button"
                            onClick={() => handleAssigneeSelect(result)}
                            className="block w-full rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-left transition-colors hover:border-cyan-400/60 hover:bg-cyan-400/5"
                          >
                            <p className="text-sm font-medium text-slate-100">{result.label}</p>
                            {result.description && (
                              <p className="mt-1 text-xs leading-5 text-slate-400">{result.description}</p>
                            )}
                            <p className="mt-1 text-xs text-cyan-300">{result.value}</p>
                          </button>
                        ))}
                      </div>
                    )}

                    {selectedAssigneeLabel && form.default_assignee && (
                      <div className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-sm text-cyan-100">
                        Selected <span className="font-medium">{selectedAssigneeLabel}</span> and filled the
                        {provider === 'jira' ? ' Jira' : ' ServiceNow'} assignee identifier below.
                      </div>
                    )}
                  </div>
                )}
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Default owner or queue
                </label>
                <input
                  type="text"
                  required
                  value={form.default_assignee || ''}
                  onChange={(event) => {
                    setSelectedAssigneeLabel(null);
                    updateForm({ default_assignee: event.target.value });
                  }}
                  className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                  placeholder={
                    ASSIGNEE_PLACEHOLDERS[provider][assigneeIdentifierType] ||
                    'security-team@company.com or SECOPS-L1'
                  }
                />
                {provider === 'jira' && assigneeIdentifierType === 'account_id' && (
                  <p className="mt-2 text-xs leading-5 text-slate-400">
                    Jira Cloud usually needs the Atlassian `accountId` for real assignee mapping.
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-slate-100">Slack collaboration</p>
                <p className="mt-1 text-sm leading-6 text-slate-300">
                  Optional, but useful for SMB teams that want incident notifications in a shared
                  channel before a formal SOC workflow is fully mature.
                </p>
              </div>
              <label className="inline-flex items-center gap-2 text-sm text-slate-200">
                <input
                  type="checkbox"
                  checked={slackEnabled}
                  onChange={(event) => updateForm({ notify_slack: event.target.checked })}
                  className="h-4 w-4 rounded border-slate-600 bg-slate-950 text-cyan-400 focus:ring-cyan-400"
                />
                Notify Slack
              </label>
            </div>

            {slackEnabled && (
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Slack channel
                  </label>
                  <input
                    type="text"
                    required
                    value={form.slack_channel || ''}
                    onChange={(event) => updateForm({ slack_channel: event.target.value })}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                    placeholder="#security-alerts"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">
                    Slack webhook URL
                  </label>
                  <input
                    type="password"
                    required
                    value={form.slack_webhook_url || ''}
                    onChange={(event) => updateForm({ slack_webhook_url: event.target.value })}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
                    placeholder="https://hooks.slack.com/services/..."
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              What SentinelGrid will do
            </p>
            <h3 className="mt-3 text-lg font-semibold text-slate-100">
              {selectedProvider.title} handoff preview
            </h3>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
              {handoffSummary.map((item) => (
                <li key={item} className="rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Operator flow
            </p>
            <h3 className="mt-3 text-lg font-semibold text-slate-100">
              Keep the first week simple
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              The best SMB rollout pattern is one queue for action, one backup notification
              channel, and clear ownership for high-signal incidents.
            </p>
            <div className="mt-4 space-y-3">
              <Link
                href="/dashboard/incidents"
                onClick={() =>
                  recordOnboardingCtaClick({
                    source: 'onboarding_ticketing_link',
                    target: '/dashboard/incidents',
                    stepId: 'ticketing',
                  })
                }
                className="block rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 hover:border-slate-700"
              >
                Review active incidents
              </Link>
              <Link
                href="/dashboard/requests"
                onClick={() =>
                  recordOnboardingCtaClick({
                    source: 'onboarding_ticketing_link',
                    target: '/dashboard/requests',
                    stepId: 'ticketing',
                  })
                }
                className="block rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm text-slate-200 hover:border-slate-700"
              >
                Review request workflow
              </Link>
            </div>
          </div>
        </aside>

        <div className="xl:col-span-2 flex justify-between pt-2">
          <button
            type="button"
            onClick={onBack}
            className="text-sm text-slate-300 hover:text-slate-100"
          >
            ← Back
          </button>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onSkip}
              className="text-sm text-slate-300 hover:text-slate-100"
            >
              Skip
            </button>
            <button
              type="button"
              onClick={handleRecheck}
              disabled={loading}
              className="inline-flex items-center justify-center rounded-full border border-cyan-400 px-5 py-2 text-sm font-medium text-cyan-300 transition-colors hover:bg-cyan-400/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Checking...' : 'Re-run health'}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save handoff settings'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
