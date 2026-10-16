'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listAlerts,
  getSIEMStats,
  updateAlert,
  type Alert,
  type AlertListResponse,
  getSourceHealth,
  type SourceHealth,
} from '@/lib/api/siem';
import { describePlaybookExecution, playbooksApi } from '@/lib/api/playbooks';
import Link from 'next/link';
import { useSearchParams, useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import MitreFilter from './components/MitreFilter';
import { PlaybooksView } from '../playbooks/PlaybooksView';
import { toast } from 'react-hot-toast';
import HealthBadge from '@/components/ui/HealthBadge';
import SeverityBadge from '@/components/ui/SeverityBadge';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import EmptyState from '@/components/ui/EmptyState';
import { TableSkeleton } from '@/components/ui/Skeleton';
import VirtualList from '@/components/ui/VirtualList';
import DownstreamAssigneePicker from '@/components/assignment/DownstreamAssigneePicker';
import { useAuth } from '@/lib/providers/AuthProvider';
import { buildAlertGraphHref } from '@/lib/security/graph-context';
import { createOptimisticEntityHandlers } from '@/lib/react-query/optimisticEntity';

type DecoratedAlert = Alert & {
  category?: string;
  mitre_tactic?: string;
  mitre_technique?: string;
  control_tags?: string[];
  asset?: string;
  asset_id?: string;
  user?: string;
  assignee?: string;
  recommended_playbook?: string;
  control_gap?: 'covered' | 'partial' | 'gap';
};

export default function AlertsPage() {
  console.log('🔍 AlertsPage component rendering');
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user } = useAuth();
  const [severityTab, setSeverityTab] = useState<'all' | 'critical' | 'high' | 'medium' | 'low'>('all');
  const [domainTab, setDomainTab] = useState<'all' | 'identity' | 'endpoint' | 'cloud' | 'email' | 'network'>('all');
  const [mitreFilter, setMitreFilter] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<'all' | string>('all');
  const [selectedTactics, setSelectedTactics] = useState<Set<string>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkMessage, setBulkMessage] = useState<string | null>(null);
  const [showBulkAssign, setShowBulkAssign] = useState(false);
  const [activeTab, setActiveTab] = useState<'detections' | 'response'>('detections');
  const [edrFilter, setEdrFilter] = useState<'all' | 'wazuh' | 'openedr' | 'velociraptor'>('all');
  const [needsAuth, setNeedsAuth] = useState(false);
  const queryClient = useQueryClient();

  const { data: alerts, isLoading: alertsLoading, error: alertsError } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => listAlerts({ limit: 50, offset: 0 }),
  });

  const { data: stats, error: statsError } = useQuery({
    queryKey: ['siem-stats'],
    queryFn: () => getSIEMStats(),
  });
  const { data: sourceHealth, error: sourceHealthError } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  useEffect(() => {
    if (sourceHealthError) {
      const err: any = sourceHealthError;
      const status = err?.response?.status || err?.status;
      if (status === 401 || status === 403) setNeedsAuth(true);
    }
  }, [sourceHealthError]);

  const bulkMutation = useMutation({
    mutationFn: async (payload: { status?: Alert['status']; assigned_to?: string; comments?: string }) => {
      const ids = Array.from(selectedIds);
      await Promise.all(ids.map((id) => updateAlert(id, payload)));
    },
    onSuccess: () => {
      setBulkMessage('Bulk action applied');
      setSelectedIds(new Set());
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
    onError: (err: any) => {
      setBulkMessage(err?.message || 'Bulk action failed');
    },
  });

  useEffect(() => {
    if (selectedIds.size === 0) {
      setShowBulkAssign(false);
    }
  }, [selectedIds]);

  const runPlaybookMutation = useMutation({
    mutationFn: async ({ playbookId, alertId }: { playbookId: string; alertId: string }) =>
      playbooksApi.execute(playbookId, 'alert', alertId, { alert_id: alertId }),
    onSuccess: (response) => {
      toast.success(describePlaybookExecution(response));
    },
    onError: (err: any) => {
      toast.error(err?.message || 'Playbook run failed');
    },
  });

  const alertActionMutation = useMutation({
    mutationFn: async ({
      alertId,
      payload,
    }: {
      alertId: string;
      payload: Partial<Pick<Alert, 'status' | 'assigned_to' | 'due_date'> & { comments?: string }>;
    }) => updateAlert(alertId, payload),
    ...createOptimisticEntityHandlers<
      Alert,
      AlertListResponse,
      {
        alertId: string;
        payload: Partial<Pick<Alert, 'status' | 'assigned_to' | 'due_date'> & { comments?: string }>;
      },
      Alert
    >({
      queryClient,
      listQueryKey: ['alerts'],
      detailQueryKey: (alertId) => ['alert', alertId],
      mutationLabel: ({ alertId }) => `update alert ${alertId}`,
      getEntityId: ({ alertId }) => alertId,
      getOptimisticEntity: (alert, variables, optimisticUpdatedAt) => ({
        ...alert,
        ...variables.payload,
        updated_at: optimisticUpdatedAt,
      }),
      getListItems: (list) => list.alerts || [],
      setListItems: (list, alerts) => ({ ...list, alerts }),
      onError: (error, variables) => {
        toast.error(error?.message || `Failed to update alert ${variables.alertId}.`);
      },
    }),
  });

  console.log('🔍 AlertsPage state:', {
    alertsLoading,
    alertsCount: alerts?.alerts?.length,
    alertsError: alertsError?.message,
    statsError: statsError?.message
  });

  // Tab sync with URL (?tab=response)
  useEffect(() => {
    const tabParam = (searchParams.get('tab') || '').toLowerCase();
    if (tabParam === 'response') {
      setActiveTab('response');
    } else {
      setActiveTab('detections');
    }
  }, [searchParams]);

  // Deep-link support: if alert_id provided, jump to detail
  useEffect(() => {
    const alertId = searchParams.get('alert_id');
    if (alertId) {
      router.push(`/dashboard/alerts/${alertId}`);
    }
  }, [router, searchParams]);

  const mitreLink = (val?: string) => {
    if (!val) return undefined;
    const tech = val.match(/T\d{4}/i)?.[0];
    if (tech) return `https://attack.mitre.org/techniques/${tech.toUpperCase()}`;
    const tactic = val.match(/TA\d{4}/i)?.[0];
    if (tactic) return `https://attack.mitre.org/tactics/${tactic.toUpperCase()}`;
    return undefined;
  };

  const controlLink = (control?: string) =>
    control ? `/dashboard/compliance?control=${encodeURIComponent(control)}` : undefined;

  const filterTerm = searchParams.get('search')
    || searchParams.get('user_id')
    || searchParams.get('principal')
    || searchParams.get('asset_id')
    || searchParams.get('investigate_user')
    || '';

  const sourceAlerts = (alerts?.alerts || []) as DecoratedAlert[];
  const hasLiveAlerts = sourceAlerts.length > 0;

  const filteredItems = useMemo(() => {
    if (!sourceAlerts) return [];
    const term = filterTerm.toLowerCase();
    const edrClause =
      edrFilter === 'all'
        ? null
        : edrFilter === 'wazuh'
        ? 'sentinelguard-wazuh'
        : edrFilter === 'openedr'
        ? 'sentinelguard-openedr'
        : 'sentinelguard-velociraptor';

    const deriveDomain = (alert: DecoratedAlert): string => {
      if (alert.user_id) return 'identity';
      if (alert.asset || alert.asset_id) return 'endpoint';
      if (alert.source?.toLowerCase().includes('cloud')) return 'cloud';
      if (alert.category?.toLowerCase().includes('phish')) return 'email';
      return 'other';
    };

    const tacticSet = selectedTactics;

    return sourceAlerts
      .map((a) => a as DecoratedAlert)
      .filter((a) => {
        // search term filter
        if (
          term &&
          !(a.title?.toLowerCase().includes(term) ||
            a.description?.toLowerCase().includes(term) ||
            a.severity?.toLowerCase().includes(term))
        ) {
          return false;
        }
        // severity tab filter
        const sev = (a.severity || (a as any).raw_severity) as DecoratedAlert['severity'];
        if (severityTab !== 'all' && sev !== severityTab) return false;
        if (edrClause) {
          const src = ((a as any).edr_source || (a as any)?.raw_payload?.edr_source || '').toLowerCase();
          if (src !== edrClause) return false;
        }
        // domain tab filter
        const domain = deriveDomain(a);
        if (domainTab !== 'all' && domain !== domainTab) return false;
        // category filter
        if (selectedCategory !== 'all' && (a.category || '').toLowerCase() !== selectedCategory.toLowerCase()) {
          return false;
        }
        // MITRE tactic chip filter
        if (tacticSet.size > 0) {
          const mt = (a.mitre_tactic || '').toLowerCase();
          const match = Array.from(tacticSet).some((tac) => mt.includes(tac.toLowerCase()));
          if (!match) return false;
        }
        // MITRE filter (advanced)
        if (mitreFilter) {
          const mf = mitreFilter.toLowerCase();
          if (
            !(a.mitre_tactic?.toLowerCase().includes(mf) ||
              a.mitre_technique?.toLowerCase().includes(mf))
          ) {
            return false;
          }
        }
        return true;
      });
  }, [alerts?.alerts, filterTerm, severityTab, domainTab, mitreFilter, selectedCategory, selectedTactics]);

  const handleTabChange = (tab: 'detections' | 'response') => {
    setActiveTab(tab);
    const params = new URLSearchParams(searchParams.toString());
    if (tab === 'detections') {
      params.delete('tab');
    } else {
      params.set('tab', tab);
    }
    const qs = params.toString();
    router.replace(qs ? `/dashboard/alerts?${qs}` : '/dashboard/alerts');
  };

  const handleBulkAssignmentSave = async (assignedTo: string) => {
    await bulkMutation.mutateAsync({ assigned_to: assignedTo });
  };

  const handleInlineAlertUpdate = async (
    alert: DecoratedAlert,
    payload: Partial<Pick<Alert, 'status' | 'assigned_to' | 'due_date'> & { comments?: string }>,
    successMessage: string
  ) => {
    await alertActionMutation.mutateAsync({ alertId: alert.id, payload });
    toast.success(successMessage);
  };

  const renderMobileAlertCard = (alert: DecoratedAlert) => {
    const recommendedId =
      (alert as any).recommended_playbook_id ||
      (alert as any)?.raw_payload?.sg?.playbook_id ||
      (alert as any)?.raw_payload?.recommended_playbook_id;
    const launchingThisAlert =
      runPlaybookMutation.isPending &&
      runPlaybookMutation.variables?.alertId === alert.id;
    const assigningToCurrentUser =
      Boolean(user?.email) &&
      ((alert as any).assigned_to || '').toLowerCase() === user?.email.toLowerCase();
    const acknowledgingThisAlert =
      alertActionMutation.isPending &&
      alertActionMutation.variables?.alertId === alert.id;
    const alreadyAcknowledged =
      alert.status === 'acknowledged' || alert.status === 'investigating';
    const ruleId =
      (alert as any).detection_rule_id ||
      (alert as any).rule_id ||
      (alert as any)?.raw_payload?.sg?.rule_id ||
      (alert as any)?.raw_payload?.rule_id;

    return (
      <article className="rounded-xl border border-surface-card-border bg-surface-card p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <SeverityBadge severity={(alert.severity || (alert as any).raw_severity || 'low') as any} />
              <span className="rounded-full border border-border px-2 py-1 text-[11px] text-text-muted">
                {alert.category || 'Uncategorized'}
              </span>
            </div>
            <h2 className="text-base font-semibold text-text-main">{alert.title}</h2>
            <p className="mt-1 text-sm text-text-muted">{alert.description}</p>
          </div>
          <input
            type="checkbox"
            className="mt-1 min-h-[20px] min-w-[20px] rounded border-border bg-transparent"
            aria-label={`Select alert: ${alert.title}`}
            checked={selectedIds.has(alert.id)}
            onChange={(e) => {
              const next = new Set(selectedIds);
              if (e.target.checked) {
                next.add(alert.id);
              } else {
                next.delete(alert.id);
              }
              setSelectedIds(next);
            }}
          />
        </div>

        <div className="mt-3 grid grid-cols-2 gap-3 text-xs text-text-muted" aria-live="polite" aria-atomic="true">
          <div>
            <div className="uppercase tracking-wide">Status</div>
            <div className="mt-1 text-sm text-text-main">{alert.status}</div>
          </div>
          <div>
            <div className="uppercase tracking-wide">Time</div>
            <div className="mt-1 text-sm text-text-main">
              {new Date(alert.detection_time || alert.created_at || alert.timestamp || Date.now()).toLocaleString()}
            </div>
          </div>
          <div>
            <div className="uppercase tracking-wide">Asset / User</div>
            <div className="mt-1 text-sm text-text-main">
              {alert.asset_id || alert.user_id || (alert as any).user_identifier || '—'}
            </div>
          </div>
          <div>
            <div className="uppercase tracking-wide">Rule</div>
            <div className="mt-1 text-sm text-text-main">{ruleId || '—'}</div>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() =>
              void handleInlineAlertUpdate(
                alert,
                { status: 'acknowledged' },
                'Alert marked in progress.'
              )
            }
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary disabled:opacity-50"
            disabled={acknowledgingThisAlert || alreadyAcknowledged}
          >
            {acknowledgingThisAlert && alertActionMutation.variables?.payload.status === 'acknowledged'
              ? 'Updating…'
              : alreadyAcknowledged
                ? 'In progress'
                : 'Acknowledge'}
          </button>
          <button
            type="button"
            onClick={() => {
              if (!user?.email) {
                toast.error('Your account does not expose an assignable email.');
                return;
              }
              void handleInlineAlertUpdate(
                alert,
                { assigned_to: user.email },
                `Assigned alert to ${user.email}.`
              );
            }}
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary disabled:opacity-50"
            disabled={!user?.email || acknowledgingThisAlert || assigningToCurrentUser}
          >
            {acknowledgingThisAlert && alertActionMutation.variables?.payload.assigned_to === user?.email
              ? 'Assigning…'
              : assigningToCurrentUser
                ? 'Assigned to me'
                : 'Assign to me'}
          </button>
          <button
            type="button"
            onClick={() => {
              if (!recommendedId) {
                toast.error('No recommended playbook available to run');
                return;
              }
              runPlaybookMutation.mutate({ playbookId: recommendedId, alertId: alert.id });
            }}
            className="inline-flex min-h-[44px] items-center rounded-lg bg-primary px-3 py-2 text-sm font-medium text-slate-950 transition-all hover:brightness-110 disabled:opacity-50"
            disabled={launchingThisAlert}
          >
            {launchingThisAlert ? 'Launching…' : 'Run playbook'}
          </button>
          <Link
            href={`/dashboard/alerts/${alert.id}`}
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
          >
            Open alert
          </Link>
          <Link
            href={buildAlertGraphHref(alert.id, {
              sourceLabel: 'Back to alert queue',
              sourceHref: '/dashboard/alerts',
            })}
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
          >
            Open graph
          </Link>
        </div>
      </article>
    );
  };

  if (alertsLoading && activeTab === 'detections') {
    return (
      <div className="p-6">
        <Breadcrumbs />
        <h1 className="text-2xl font-bold text-text-main mb-4">Detections &amp; Response</h1>
        <TableSkeleton rows={6} columns={8} />
      </div>
    );
  }

  return (
    <div className="p-6">
      <Breadcrumbs />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-main mb-2">Detections &amp; Response</h1>
        <p className="text-text-muted">Monitor detections, recommended responses, and control coverage</p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-muted">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
          <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
          <HealthBadge label="Baseline sensor" status={sourceHealth?.wazuh} />
          <HealthBadge label="Behavioral telemetry" status={sourceHealth?.openedr} />
          <HealthBadge label="Hunt/collections" status={sourceHealth?.velociraptor} />
          {needsAuth && (
            <Link href="/login" className="text-primary underline">
              Session expired? Sign in again.
            </Link>
          )}
        </div>
      </div>

      <div className="flex gap-2 mb-4" role="tablist" aria-label="Alert view mode">
        {[
          { key: 'detections', label: 'Detections' },
          { key: 'response', label: 'Response' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => handleTabChange(tab.key as 'detections' | 'response')}
            role="tab"
            aria-selected={activeTab === tab.key}
            className={clsx(
              'px-4 py-2.5 min-h-[44px] rounded-lg text-sm font-semibold border transition-colors',
              activeTab === tab.key
                ? 'border-primary/60 text-primary bg-primary/10'
                : 'border-transparent text-text-muted hover:text-text-main hover:border-border'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'response' ? (
        <div className="bg-surface-card rounded-xl border border-surface-card-border">
          <PlaybooksView />
        </div>
      ) : (
        <>
      <div className="flex flex-wrap gap-2 mb-4">
        {['all', 'wazuh', 'openedr', 'velociraptor'].map((key) => (
          <button
            key={key}
            onClick={() => setEdrFilter(key as any)}
            className={clsx(
              'px-4 py-2.5 min-h-[44px] rounded-full text-sm border transition-colors',
              edrFilter === key ? 'bg-primary text-white border-primary' : 'bg-slate-800 text-text-muted border-slate-700 hover:border-primary/50 hover:text-text-main'
            )}
            title="Filter by endpoint telemetry source"
          >
            {key === 'all' ? 'All sources' : key === 'wazuh' ? 'Baseline' : key === 'openedr' ? 'Behavioral' : 'Hunts'}
          </button>
        ))}
      </div>
      {/* Bulk actions */}
      {selectedIds.size > 0 && (
        <div className="mb-4 flex flex-wrap items-center gap-3 bg-surface-card border border-surface-card-border rounded-xl px-4 py-3">
          <div className="text-sm text-text-main">
            {selectedIds.size} selected
          </div>
          <div className="flex items-center gap-2 text-xs">
            <button
              className="px-3 py-1.5 rounded bg-primary text-slate-950 text-sm font-semibold hover:brightness-110"
              onClick={() => setShowBulkAssign((current) => !current)}
              disabled={bulkMutation.isPending}
            >
              {showBulkAssign ? 'Hide assignment' : 'Assign selected'}
            </button>
            <button
              className="px-3 py-1.5 rounded border border-primary/40 text-primary text-sm hover:bg-primary/10"
              onClick={() => bulkMutation.mutate({ status: 'acknowledged' })}
              disabled={bulkMutation.isPending}
            >
              Mark In Progress
            </button>
            <button
              className="px-3 py-1.5 rounded border border-amber-500/40 text-amber-300 text-sm hover:bg-amber-500/10"
              onClick={() => bulkMutation.mutate({ comments: 'tag:needs_review' })}
              disabled={bulkMutation.isPending}
            >
              Tag: Needs Review
            </button>
          </div>
          {bulkMessage && <div className="text-xs text-text-muted">{bulkMessage}</div>}
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto text-xs text-text-muted hover:text-text-main"
          >
            Clear selection
          </button>
          {showBulkAssign && (
            <div className="w-full rounded-xl border border-surface-card-border bg-[rgba(15,23,42,0.42)] p-4">
              <DownstreamAssigneePicker
                currentValue={undefined}
                onSave={handleBulkAssignmentSave}
                saving={bulkMutation.isPending}
                title="Bulk assignment"
                description="Search the downstream directory and apply the selected assignee identifier to every selected alert."
                saveLabel="Assign selected alerts"
                compact
                successMessageBuilder={(selectedLabel, assignedTo) =>
                  `Assigned ${selectedIds.size} selected alerts${selectedLabel ? ` to ${selectedLabel}` : ` to ${assignedTo}`}.`
                }
              />
            </div>
          )}
        </div>
      )}

      {stats && (
        <div className="grid gap-4 md:grid-cols-4 mb-6" aria-live="polite" aria-atomic="true">
          <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
            <div className="text-sm text-text-muted mb-1">Total Alerts</div>
            <div className="text-2xl font-bold text-text-main">{stats.alerts_count}</div>
          </div>
          <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
            <div className="text-sm text-text-muted mb-1">Critical</div>
            <div className="text-2xl font-bold text-red-500">
              {stats.alerts_by_severity?.critical || 0}
            </div>
          </div>
          <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
            <div className="text-sm text-text-muted mb-1">High</div>
            <div className="text-2xl font-bold text-orange-500">
              {stats.alerts_by_severity?.high || 0}
            </div>
          </div>
          <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
            <div className="text-sm text-text-muted mb-1">Open</div>
            <div className="text-2xl font-bold text-primary">
              {stats.alerts_by_status?.open || 0}
            </div>
          </div>
        </div>
      )}

      <div className="md:hidden mb-4" aria-live="polite" aria-atomic="true">
        {filteredItems.length > 0 ? (
          <VirtualList
            items={filteredItems}
            estimateSize={320}
            className="max-h-[calc(100vh-18rem)] space-y-0"
            getItemKey={(index) => filteredItems[index].id}
            renderItem={(alert) => (
              <div className="pb-3">
                {renderMobileAlertCard(alert)}
              </div>
            )}
          />
        ) : (
          <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
            <EmptyState
              variant={hasLiveAlerts ? 'no-results' : 'no-data'}
              title={hasLiveAlerts ? 'No alerts match these filters' : 'No live alerts yet'}
              description={
                hasLiveAlerts
                  ? 'Adjust the current filters to review more detections.'
                  : 'The alert queue stays empty until connected systems send real detections for this tenant.'
              }
            />
          </div>
        )}
      </div>

      <div className="hidden md:block bg-surface-card rounded-xl border border-surface-card-border overflow-hidden">
        <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-surface-card">
          <div className="flex items-center gap-1 text-xs text-text-muted">
            Severity:
            {(['all', 'critical', 'high', 'medium', 'low'] as const).map((sev) => (
              <button
                key={sev}
                onClick={() => setSeverityTab(sev)}
                className={clsx(
                  'px-2 py-1 rounded border text-xs',
                  severityTab === sev
                    ? 'border-primary/50 text-primary bg-primary/10'
                    : 'border-transparent text-text-muted hover:text-text-main hover:border-border'
                )}
              >
                {sev === 'all' ? 'All' : sev.toUpperCase()}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 text-xs text-text-muted">
            Domain:
            {(['all', 'identity', 'endpoint', 'cloud', 'email', 'network'] as const).map((dom) => (
              <button
                key={dom}
                onClick={() => setDomainTab(dom)}
                className={clsx(
                  'px-2 py-1 rounded border text-xs capitalize',
                  domainTab === dom
                    ? 'border-primary/50 text-primary bg-primary/10'
                    : 'border-transparent text-text-muted hover:text-text-main hover:border-border'
                )}
              >
                {dom}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1 text-xs text-text-muted">
            Category:
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-surface-input border border-border-faint rounded px-2 py-1 text-text-main text-xs focus:outline-none focus:border-primary/50"
            >
              <option value="all">All</option>
              {Array.from(
                new Set(
                  sourceAlerts
                    .map((a) => (a as DecoratedAlert).category)
                    .filter(Boolean)
                )
              ).map((cat) => (
                <option key={cat as string} value={cat as string}>
                  {cat as string}
                </option>
              ))}
            </select>
          </div>
          <MitreFilter
            alerts={sourceAlerts}
            selectedTactics={selectedTactics}
            setSelectedTactics={setSelectedTactics}
            mitreFilter={mitreFilter}
            setMitreFilter={setMitreFilter}
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full" aria-label="Security alerts and detections">
            <caption className="sr-only">Security alerts with severity, MITRE mapping, and response actions</caption>
            <thead className="bg-surface-card-border border-b border-surface-card">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  <input
                    type="checkbox"
                    className="rounded border-border bg-transparent min-w-[20px] min-h-[20px]"
                    aria-label={selectedIds.size === filteredItems.length ? 'Deselect all alerts' : 'Select all alerts'}
                    checked={filteredItems.length > 0 && selectedIds.size === filteredItems.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedIds(new Set(filteredItems.map((a) => a.id)));
                      } else {
                        setSelectedIds(new Set());
                      }
                    }}
                  />
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Severity
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Title
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Category / Domain
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  MITRE
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Control
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Asset / User
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Time
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Rule
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                  Response
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-card">
              {filteredItems && filteredItems.length > 0 ? (
                filteredItems.map((alert) => (
                  <tr key={alert.id} className="hover:bg-surface-hover">
                <td className="px-4 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    className="rounded border-border bg-transparent min-w-[20px] min-h-[20px]"
                    aria-label={`Select alert: ${alert.title}`}
                    checked={selectedIds.has(alert.id)}
                    onChange={(e) => {
                      const next = new Set(selectedIds);
                      if (e.target.checked) {
                        next.add(alert.id);
                      } else {
                        next.delete(alert.id);
                      }
                      setSelectedIds(next);
                    }}
                  />
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 text-xs font-semibold rounded ${
                      (alert.severity || (alert as any).raw_severity) === 'critical'
                        ? 'bg-red-500/20 text-red-500'
                        : (alert.severity || (alert as any).raw_severity) === 'high'
                            ? 'bg-orange-500/20 text-orange-500'
                            : (alert.severity || (alert as any).raw_severity) === 'medium'
                            ? 'bg-yellow-500/20 text-yellow-500'
                            : 'bg-blue-500/20 text-blue-500'
                        }`}
                      >
                        {(alert.severity || (alert as any).raw_severity || '').toUpperCase()}
                      </span>
                    </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-text-main">{alert.title}</div>
                  <div className="text-sm text-text-muted">{alert.description}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs text-text-main font-semibold capitalize">
                      {alert.category || 'Uncategorized'}
                    </span>
                    <span className="text-[11px] text-text-muted capitalize">
                      {alert.user_id || (alert as any).user_identifier ? 'Identity' : alert.asset_id ? 'Endpoint' : 'Other'}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                  {alert.mitre_tactic || alert.mitre_technique ? (
                    <div className="flex flex-col text-xs">
                  {alert.mitre_tactic && (
                    <a
                      href={mitreLink(alert.mitre_tactic) || '#'}
                      target={mitreLink(alert.mitre_tactic) ? '_blank' : undefined}
                      rel="noreferrer"
                      title="View MITRE tactic details"
                      className="hover:text-primary"
                    >
                      {alert.mitre_tactic}
                    </a>
                  )}
                  {alert.mitre_technique && (
                    <span className="text-text-muted">
                      <a
                        href={mitreLink(alert.mitre_technique) || '#'}
                        target={mitreLink(alert.mitre_technique) ? '_blank' : undefined}
                        rel="noreferrer"
                        title="View MITRE technique details"
                        className="hover:text-primary"
                      >
                        {alert.mitre_technique}
                      </a>
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-text-muted text-xs">—</span>
              )}
            </td>
            <td className="px-6 py-4 whitespace-nowrap">
              <div className="flex flex-wrap gap-1">
                {(alert.control_tags || []).length > 0 ? (
                  alert.control_tags!.map((ct) => (
                    <Link
                      href={controlLink(ct) || '#'}
                      key={ct}
                      title="View control coverage details"
                      className="px-2 py-1 rounded bg-success-soft text-[11px] text-green-400 border border-green-500/20 hover:bg-success-soft-hover"
                    >
                      {ct}
                    </Link>
                  ))
                ) : (
                  <span className="text-text-muted text-xs">—</span>
                )}
                {alert.control_gap && alert.control_gap !== 'covered' && (
                  <Link
                    href="/dashboard/compliance?gap=true"
                    className="px-2 py-1 rounded bg-amber-500/15 text-[11px] text-amber-300 border border-amber-500/30 hover:bg-amber-500/25"
                    title="View coverage gaps and remediation guidance"
                  >
                    Gap
                  </Link>
                )}
              </div>
            </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                  <div className="flex flex-col gap-0.5">
                    {alert.asset_id && <span className="text-xs">Asset: {alert.asset_id}</span>}
                    {(alert.user_id || (alert as any).user_identifier) && (
                      <span className="text-xs text-text-muted">User: {alert.user_id || (alert as any).user_identifier}</span>
                    )}
                    {!alert.asset_id && !(alert.user_id || (alert as any).user_identifier) && (
                      <span className="text-text-muted text-xs">—</span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs font-semibold rounded bg-primary/20 text-primary">
                    {alert.status}
                  </span>
                  {(alert as any).assigned_to && (
                    <div className="text-[11px] text-text-muted mt-1">Assignee: {(alert as any).assigned_to}</div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                  {new Date(alert.detection_time || alert.created_at || alert.timestamp || Date.now()).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                  {(() => {
                    const ruleId =
                      (alert as any).detection_rule_id ||
                      (alert as any).rule_id ||
                      (alert as any)?.raw_payload?.sg?.rule_id ||
                      (alert as any)?.raw_payload?.rule_id;
                    const ruleName =
                      (alert as any)?.raw_payload?.rule_name ||
                      (alert as any)?.rule_name ||
                      (alert as any)?.title;
                    return ruleId ? (
                      <Link
                        href={`/dashboard/siem/detection-rules/${ruleId}`}
                        className="text-primary hover:text-primary/80 text-sm"
                        title="View detection rule"
                      >
                        {ruleName || ruleId}
                      </Link>
                    ) : (
                      <span className="text-text-muted text-xs">—</span>
                    );
                  })()}
                  {(alert as any).detection_rule_version_id && (
                    <div className="text-[11px] text-text-muted">
                      vID: {(alert as any).detection_rule_version_id}
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <div className="flex items-center gap-2">
                    {alert.recommended_playbook ? (
                      <span className="px-2 py-1 text-[11px] rounded bg-primary/15 text-primary border border-primary/30">
                        {alert.recommended_playbook}
                      </span>
                    ) : (
                      <span className="text-text-muted text-xs">—</span>
                    )}
                    {(alert as any).playbook_version_id && (
                      <span className="text-[11px] text-text-muted">
                        pVID: {(alert as any).playbook_version_id}
                      </span>
                    )}
                    {(() => {
                      const recommendedId =
                        (alert as any).recommended_playbook_id ||
                        (alert as any)?.raw_payload?.sg?.playbook_id ||
                        (alert as any)?.raw_payload?.recommended_playbook_id;
                      const launchingThisAlert =
                        runPlaybookMutation.isPending &&
                        runPlaybookMutation.variables?.alertId === alert.id;
                      const assigningToCurrentUser =
                        Boolean(user?.email) &&
                        ((alert as any).assigned_to || '').toLowerCase() === user?.email.toLowerCase();
                      const acknowledgingThisAlert =
                        alertActionMutation.isPending &&
                        alertActionMutation.variables?.alertId === alert.id;
                      const alreadyAcknowledged =
                        alert.status === 'acknowledged' || alert.status === 'investigating';

                      return (
                        <>
                          <button
                            type="button"
                            onClick={() =>
                              void handleInlineAlertUpdate(
                                alert,
                                { status: 'acknowledged' },
                                'Alert marked in progress.'
                              )
                            }
                            className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                            disabled={acknowledgingThisAlert || alreadyAcknowledged}
                            title={alreadyAcknowledged ? 'Alert is already in progress' : 'Acknowledge alert'}
                          >
                            {acknowledgingThisAlert && alertActionMutation.variables?.payload.status === 'acknowledged'
                              ? 'Updating...'
                              : alreadyAcknowledged
                                ? 'In progress'
                                : 'Acknowledge'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (!user?.email) {
                                toast.error('Your account does not expose an assignable email.');
                                return;
                              }
                              void handleInlineAlertUpdate(
                                alert,
                                { assigned_to: user.email },
                                `Assigned alert to ${user.email}.`
                              );
                            }}
                            className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                            disabled={!user?.email || acknowledgingThisAlert || assigningToCurrentUser}
                            title={assigningToCurrentUser ? 'Alert is already assigned to you' : 'Assign alert to me'}
                          >
                            {acknowledgingThisAlert &&
                            alertActionMutation.variables?.payload.assigned_to === user?.email
                              ? 'Assigning...'
                              : assigningToCurrentUser
                                ? 'Assigned to me'
                                : 'Assign to me'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              if (!recommendedId) {
                                toast.error('No recommended playbook available to run');
                                return;
                              }
                              runPlaybookMutation.mutate({ playbookId: recommendedId, alertId: alert.id });
                            }}
                            className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                            disabled={launchingThisAlert}
                            title={recommendedId ? 'Run recommended playbook' : 'No playbook to run'}
                          >
                            {launchingThisAlert ? 'Launching...' : 'Run playbook'}
                          </button>
                          <Link
                            href={`/dashboard/alerts/${alert.id}`}
                            className="text-primary hover:text-primary/80 text-sm"
                          >
                            Open alert
                          </Link>
                          <Link
                            href={buildAlertGraphHref(alert.id, {
                              sourceLabel: 'Back to alert queue',
                              sourceHref: '/dashboard/alerts',
                            })}
                            className="text-primary hover:text-primary/80 text-sm"
                          >
                            Open graph
                          </Link>
                        </>
                      );
                    })()}
                  </div>
                </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={11} className="px-6 py-12 text-center text-text-muted">
                    {hasLiveAlerts
                      ? 'No alerts match the current filters.'
                      : 'No live alerts have been ingested for this tenant yet.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
      </div>
    </div>
        </>
      )}
    </div>
  );
}
