'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import clsx from 'clsx';
import Link from 'next/link';
import {
  listIncidents,
  updateIncident,
  type Incident,
  type IncidentUpdatePayload,
} from '@/lib/api/incidents';
import { describePlaybookExecution, playbooksApi } from '@/lib/api/playbooks';
import { toast } from 'react-hot-toast';
import { getSourceHealth, type SourceHealth } from '@/lib/api/siem';
import HealthBadge from '@/components/ui/HealthBadge';
import StorySummaryInline from '@/components/operator/StorySummaryInline';
import VirtualList from '@/components/ui/VirtualList';
import { getIssueSlaLabel } from '@/lib/issues/sla';
import { buildIncidentGraphHref } from '@/lib/security/graph-context';
import { useAuth } from '@/lib/providers/AuthProvider';
import { createTicket } from '@/lib/api/tickets';
import { createOptimisticEntityHandlers } from '@/lib/react-query/optimisticEntity';

type IncidentPhase = 'New' | 'Analyzing' | 'Containment' | 'Eradication/Recovery' | 'Monitoring' | 'Closed';
type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low';

const severityColor = (sev: IncidentSeverity) =>
  sev === 'critical'
    ? 'bg-red-500/20 text-red-400'
    : sev === 'high'
    ? 'bg-orange-500/20 text-orange-400'
    : sev === 'medium'
    ? 'bg-yellow-500/20 text-yellow-400'
    : 'bg-blue-500/20 text-blue-300';

export default function IncidentsPage() {
  const queryClient = useQueryClient();
  const { tenantId, user } = useAuth();
  const [severityTab, setSeverityTab] = useState<'all' | IncidentSeverity>('all');
  const [phaseFilter, setPhaseFilter] = useState<'all' | IncidentPhase>('all');

  const { data: incidentsResp, isLoading } = useQuery({
    queryKey: ['incidents'],
    queryFn: () => listIncidents({ limit: 100 }),
  });
  const { data: sourceHealth } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });
  const incidents = incidentsResp?.items || [];

  const runPlaybookMutation = useMutation({
    mutationFn: async ({ playbookId, incidentId }: { playbookId: string; incidentId: string }) =>
      playbooksApi.execute(playbookId, 'incident', incidentId, { incident_id: incidentId }),
    onSuccess: (response) => toast.success(describePlaybookExecution(response)),
    onError: (err: any) => toast.error(err?.message || 'Playbook run failed'),
  });

  const incidentActionMutation = useMutation({
    mutationFn: async ({
      incidentId,
      updates,
    }: {
      incidentId: string;
      updates: IncidentUpdatePayload;
    }) => updateIncident(incidentId, updates),
    ...createOptimisticEntityHandlers<
      Incident,
      { items: Incident[]; total: number; limit?: number; offset?: number },
      {
        incidentId: string;
        updates: IncidentUpdatePayload;
      },
      Incident
    >({
      queryClient,
      listQueryKey: ['incidents'],
      detailQueryKey: (incidentId) => ['incident', incidentId],
      mutationLabel: ({ incidentId }) => `update incident ${incidentId}`,
      getEntityId: ({ incidentId }) => incidentId,
      getOptimisticEntity: (incident, variables, optimisticUpdatedAt) => {
        const { description, ...restUpdates } = variables.updates;
        return {
          ...incident,
          ...restUpdates,
          ...(description !== undefined && { description: description ?? undefined }),
          assignee: variables.updates.assigned_to ?? incident.assignee,
          assigned_to: variables.updates.assigned_to ?? incident.assigned_to,
          phase: variables.updates.phase ?? incident.phase,
          status: variables.updates.status ?? incident.status,
          updated_at: optimisticUpdatedAt,
        };
      },
      getListItems: (list) => list.items || [],
      setListItems: (list, items) => ({ ...list, items }),
      onError: (error, variables) => {
        toast.error(error?.message || `Failed to update incident ${variables.incidentId}.`);
      },
    }),
  });

  const createTicketMutation = useMutation({
    mutationFn: async ({ incident }: { incident: Incident }) =>
      createTicket(
        {
          title: `Respond to incident: ${incident.title}`,
          description: incident.description || `Operator handoff for incident ${incident.id}.`,
          severity: incident.severity,
          priority: incident.severity,
          category: 'incident_response',
          source: 'incident',
          alert_ids: (incident.related_detections || []).map((d) => d.id),
          assigned_to: incident.assigned_to || incident.assignee || user?.email || undefined,
          created_by: user?.email || undefined,
          incident_id: incident.id,
          incident_management_mode: 'linked_ticket',
        },
        tenantId || undefined
      ),
    onSuccess: (ticket, variables) => {
      queryClient.setQueryData<
        { items: Incident[]; total: number; limit?: number; offset?: number } | undefined
      >(['incidents'], (current) => {
        if (!current?.items) {
          return current;
        }

        return {
          ...current,
          items: current.items.map((incident) =>
            incident.id === variables.incident.id
              ? {
                  ...incident,
                  ticket_id: ticket.id,
                  external_ticket_id: ticket.external_id || incident.external_ticket_id,
                  external_ticket_provider: ticket.source || incident.external_ticket_provider,
                }
              : incident
          ),
        };
      });
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', variables.incident.id] });
      toast.success(`Remediation ticket ${ticket.id} created.`);
    },
    onError: (error: any) => {
      toast.error(error?.message || 'Failed to create remediation ticket.');
    },
  });

  const recommendedPlaybook = (inc: Incident) =>
    (inc as any)?.recommended_playbook ||
    (inc as any)?.recommended_playbook_id ||
    (inc as any)?.recommended_playbook_key ||
    (inc.raw_payload as any)?.recommended_playbook ||
    (inc.raw_payload as any)?.sg?.playbook_id ||
    (inc.raw_payload as any)?.playbook_id;

  const relatedRule = (inc: Incident) =>
    (inc as any)?.rule_id ||
    (inc.raw_payload as any)?.rule_id ||
    (inc.related_detections && inc.related_detections[0]?.id);

  const detectionVersion = (inc: Incident) =>
    (inc as any)?.detection_rule_version_id ||
    (inc.raw_payload as any)?.detection_rule_version_id ||
    (inc.raw_payload as any)?.sg?.detection_rule_version_id;

  const playbookVersion = (inc: Incident) =>
    (inc as any)?.playbook_version_id ||
    (inc.raw_payload as any)?.playbook_version_id ||
    (inc.raw_payload as any)?.sg?.playbook_version_id;

  const playbookId = (inc: Incident) =>
    (inc as any)?.playbook_id ||
    (inc.raw_payload as any)?.playbook_id ||
    (inc.raw_payload as any)?.sg?.playbook_id;

  const filtered = useMemo(() => {
    return incidents.filter((inc) => {
      const sev = (inc.severity || 'medium') as IncidentSeverity;
      const phase = ((inc as any).phase || inc.status || 'New') as IncidentPhase;
      if (severityTab !== 'all' && sev !== severityTab) return false;
      if (phaseFilter !== 'all' && phase !== phaseFilter) return false;
      return true;
    });
  }, [incidents, severityTab, phaseFilter]);

  const handleInlineIncidentUpdate = async (
    incident: Incident,
    updates: IncidentUpdatePayload,
    successMessage: string
  ) => {
    await incidentActionMutation.mutateAsync({
      incidentId: incident.id,
      updates,
    });
    toast.success(successMessage);
  };

  const renderMobileIncidentCard = (inc: Incident) => {
    const currentPhase = ((inc as any).phase || inc.status || 'New') as IncidentPhase;
    const containmentReached = currentPhase.toLowerCase() === 'containment';
    const assigningToCurrentUser =
      Boolean(user?.email) &&
      (inc.assigned_to || inc.assignee || '').toLowerCase() === user!.email.toLowerCase();
    const updatingThisIncident =
      incidentActionMutation.isPending &&
      incidentActionMutation.variables?.incidentId === inc.id;
    const assignmentPending =
      updatingThisIncident &&
      incidentActionMutation.variables?.updates.assigned_to === user?.email;
    const containmentPending =
      updatingThisIncident &&
      incidentActionMutation.variables?.updates.phase === 'Containment';
    const creatingTicketForIncident =
      createTicketMutation.isPending &&
      createTicketMutation.variables?.incident.id === inc.id;

    return (
      <article className="rounded-xl border border-surface-card-border bg-surface-card p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <span
              className={clsx(
                'inline-flex rounded-full px-2 py-1 text-xs font-semibold',
                severityColor((inc.severity as IncidentSeverity) || 'medium')
              )}
            >
              {(inc.severity || 'medium').toUpperCase()}
            </span>
            <h2 className="mt-3 text-base font-semibold text-text-main">{inc.title}</h2>
            <p className="mt-1 text-sm text-text-muted">{inc.description || 'No summary available.'}</p>
          </div>
          <span className="rounded-full border border-border px-2 py-1 text-[11px] text-text-muted">
            {currentPhase}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-xs text-text-muted" aria-live="polite" aria-atomic="true">
          <div>
            <div className="uppercase tracking-wide">Assignee</div>
            <div className="mt-1 text-sm text-text-main">{inc.assignee || 'Unassigned'}</div>
          </div>
          <div>
            <div className="uppercase tracking-wide">SLA</div>
            <div className="mt-1 text-sm text-text-main">
              {inc.due_date ? getIssueSlaLabel(inc.due_date) : inc.sla || '—'}
            </div>
          </div>
          <div>
            <div className="uppercase tracking-wide">Updated</div>
            <div className="mt-1 text-sm text-text-main">
              {inc.updated_at ? new Date(inc.updated_at).toLocaleString() : '—'}
            </div>
          </div>
          <div>
            <div className="uppercase tracking-wide">Ticket</div>
            <div className="mt-1 text-sm text-text-main">
              {inc.ticket_id || inc.external_ticket_id || 'Local'}
            </div>
          </div>
        </div>

        <StorySummaryInline summary={inc.story_summary} domains={inc.story_domains} className="mt-4" />

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              if (!user?.email) {
                toast.error('Your account does not expose an assignable email.');
                return;
              }
              void handleInlineIncidentUpdate(
                inc,
                { assigned_to: user.email },
                `Assigned incident to ${user.email}.`
              );
            }}
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary disabled:opacity-50"
            disabled={!user?.email || assignmentPending || assigningToCurrentUser}
          >
            {assignmentPending ? 'Assigning…' : assigningToCurrentUser ? 'Assigned to me' : 'Assign to me'}
          </button>
          <button
            type="button"
            onClick={() =>
              void handleInlineIncidentUpdate(
                inc,
                {
                  phase: 'Containment',
                  status: inc.status === 'closed' ? inc.status : 'in_progress',
                },
                'Incident moved to containment.'
              )
            }
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary disabled:opacity-50"
            disabled={containmentPending || containmentReached}
          >
            {containmentPending ? 'Updating…' : containmentReached ? 'Containment active' : 'Move to containment'}
          </button>
          {inc.ticket_id ? (
            <Link
              href={`/dashboard/tickets/${inc.ticket_id}`}
              className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
            >
              Open ticket
            </Link>
          ) : !inc.external_ticket_id ? (
            <button
              type="button"
              onClick={() => createTicketMutation.mutate({ incident: inc })}
              className="inline-flex min-h-[44px] items-center rounded-lg bg-primary px-3 py-2 text-sm font-medium text-slate-950 transition-all hover:brightness-110 disabled:opacity-50"
              disabled={creatingTicketForIncident}
            >
              {creatingTicketForIncident ? 'Creating ticket…' : 'Create ticket'}
            </button>
          ) : null}
          <Link
            href={`/dashboard/incidents/${inc.id}`}
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
          >
            Open incident
          </Link>
          <Link
            href={buildIncidentGraphHref(inc.id, {
              sourceLabel: 'Back to incident queue',
              sourceHref: '/dashboard/incidents',
            })}
            className="inline-flex min-h-[44px] items-center rounded-lg border border-border px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
          >
            Open graph
          </Link>
        </div>
      </article>
    );
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-main mb-2">Incidents</h1>
        <p className="text-text-muted">NIST-aligned incident workflow with ownership and ticketing.</p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-muted">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
          <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 bg-surface-card border border-surface-card-border rounded-xl px-4 py-3">
        <div className="flex items-center gap-2 text-xs text-text-muted">
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
        <div className="flex items-center gap-2 text-xs text-text-muted">
          Phase:
          <select
            value={phaseFilter}
            onChange={(e) => setPhaseFilter(e.target.value as any)}
            className="bg-[rgba(15,23,42,0.6)] border border-[rgba(255,255,255,0.06)] rounded px-2 py-1 text-text-main text-xs focus:outline-none focus:border-primary/50"
          >
            <option value="all">All phases</option>
            {(['New', 'Analyzing', 'Containment', 'Eradication/Recovery', 'Monitoring', 'Closed'] as IncidentPhase[]).map(
              (p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              )
            )}
          </select>
        </div>
      </div>

      <div className="md:hidden" aria-live="polite" aria-atomic="true">
        {filtered.length > 0 ? (
          <VirtualList
            items={filtered}
            estimateSize={300}
            className="max-h-[calc(100vh-16rem)]"
            getItemKey={(index) => filtered[index].id}
            renderItem={(incident) => (
              <div className="pb-3">
                {renderMobileIncidentCard(incident)}
              </div>
            )}
          />
        ) : (
          <div className="rounded-xl border border-surface-card-border bg-surface-card p-6 text-center text-text-muted">
            No incidents match your filters.
          </div>
        )}
      </div>

      <div className="hidden md:block bg-surface-card rounded-xl border border-surface-card-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-card-border border-b border-surface-card">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Severity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Phase</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Assignee</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">SLA</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Updated</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Ticket</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Rule / Detections</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Versions</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Response</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-card">
              {isLoading ? (
                <tr>
                  <td colSpan={11} className="px-6 py-6 text-center text-text-muted">
                    Loading incidents...
                  </td>
                </tr>
              ) : filtered.length > 0 ? (
                filtered.map((inc) => (
                  <tr key={inc.id} className="hover:bg-[rgba(15,23,42,0.5)]">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={clsx(
                          'px-2 py-1 text-xs font-semibold rounded',
                          severityColor((inc.severity as IncidentSeverity) || 'medium')
                        )}
                      >
                        {(inc.severity || 'medium').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-text-main">{inc.title}</div>
                      <div className="text-xs text-text-muted">{inc.id}</div>
                      <StorySummaryInline
                        summary={inc.story_summary}
                        domains={inc.story_domains}
                        className="mt-2"
                      />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                      {(inc as any).phase || inc.status || 'New'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                      {inc.assignee || <span className="text-text-muted">Unassigned</span>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                      {inc.due_date ? getIssueSlaLabel(inc.due_date) : inc.sla || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                      {inc.updated_at ? new Date(inc.updated_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                      {inc.external_ticket_id ? (
                        <span className="text-primary">
                          {inc.external_ticket_provider || 'ticket'}:{inc.external_ticket_id}
                        </span>
                      ) : inc.ticket_id ? (
                        <Link href={`/dashboard/tickets/${inc.ticket_id}`} className="text-primary hover:text-primary/80">
                          {inc.ticket_id}
                        </Link>
                      ) : (
                        <span className="text-text-muted">Local</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                      <div className="flex flex-col gap-1">
                        {relatedRule(inc) ? (
                          <Link
                            href={`/dashboard/siem/detection-rules/${relatedRule(inc)}`}
                            className="text-primary hover:text-primary/80 text-sm"
                            title="View originating rule"
                          >
                            {relatedRule(inc)}
                          </Link>
                        ) : (
                          <span className="text-text-muted text-xs">Rule: —</span>
                        )}
                        <div className="text-xs text-text-muted">
                          Detections: {Array.isArray((inc as any).related_detections) ? (inc as any).related_detections.length : 0}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-[11px] text-text-muted">
                      {detectionVersion(inc) && <div>Det vID: {detectionVersion(inc)}</div>}
                      {playbookVersion(inc) && <div>PB vID: {playbookVersion(inc)}</div>}
                      {playbookId(inc) && <div>PB ID: {playbookId(inc)}</div>}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-text-main">
                      <div className="flex items-center gap-2">
                        {recommendedPlaybook(inc) ? (
                          <span className="px-2 py-1 text-[11px] rounded bg-primary/15 text-primary border border-primary/30">
                            {recommendedPlaybook(inc)}
                          </span>
                        ) : (
                          <span className="text-text-muted text-xs">—</span>
                        )}
                        {recommendedPlaybook(inc) && (
                          <button
                            onClick={() => {
                              const pid = recommendedPlaybook(inc);
                              if (!pid) {
                                toast.error('No recommended playbook available to run');
                                return;
                              }
                              runPlaybookMutation.mutate({ playbookId: String(pid), incidentId: inc.id });
                            }}
                            className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                            disabled={runPlaybookMutation.isPending}
                            title="Run recommended playbook"
                          >
                            Launch playbook
                          </button>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {(() => {
                        const currentPhase = ((inc as any).phase || inc.status || 'New') as IncidentPhase;
                        const containmentReached = currentPhase.toLowerCase() === 'containment';
                        const assigningToCurrentUser =
                          Boolean(user?.email) &&
                          (inc.assigned_to || inc.assignee || '').toLowerCase() ===
                            user!.email.toLowerCase();
                        const updatingThisIncident =
                          incidentActionMutation.isPending &&
                          incidentActionMutation.variables?.incidentId === inc.id;
                        const assignmentPending =
                          updatingThisIncident &&
                          incidentActionMutation.variables?.updates.assigned_to === user?.email;
                        const containmentPending =
                          updatingThisIncident &&
                          incidentActionMutation.variables?.updates.phase === 'Containment';
                        const creatingTicketForIncident =
                          createTicketMutation.isPending &&
                          createTicketMutation.variables?.incident.id === inc.id;

                        return (
                          <div className="flex flex-wrap items-center gap-3">
                            <button
                              type="button"
                              onClick={() => {
                                if (!user?.email) {
                                  toast.error('Your account does not expose an assignable email.');
                                  return;
                                }
                                void handleInlineIncidentUpdate(
                                  inc,
                                  { assigned_to: user.email },
                                  `Assigned incident to ${user.email}.`
                                );
                              }}
                              className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                              disabled={!user?.email || assignmentPending || assigningToCurrentUser}
                              title={
                                assigningToCurrentUser
                                  ? 'Incident is already assigned to you'
                                  : 'Assign incident to me'
                              }
                            >
                              {assignmentPending
                                ? 'Assigning...'
                                : assigningToCurrentUser
                                  ? 'Assigned to me'
                                  : 'Assign to me'}
                            </button>
                            <button
                              type="button"
                              onClick={() =>
                                void handleInlineIncidentUpdate(
                                  inc,
                                  {
                                    phase: 'Containment',
                                    status: inc.status === 'closed' ? inc.status : 'in_progress',
                                  },
                                  'Incident moved to containment.'
                                )
                              }
                              className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                              disabled={containmentPending || containmentReached}
                              title={
                                containmentReached
                                  ? 'Incident is already in containment'
                                  : 'Move incident to containment'
                              }
                            >
                              {containmentPending
                                ? 'Updating...'
                                : containmentReached
                                  ? 'Containment active'
                                  : 'Move to containment'}
                            </button>
                            {inc.ticket_id ? (
                              <Link
                                href={`/dashboard/tickets/${inc.ticket_id}`}
                                className="text-primary hover:text-primary/80 text-sm"
                              >
                                Open ticket
                              </Link>
                            ) : !inc.external_ticket_id ? (
                              <button
                                type="button"
                                onClick={() => createTicketMutation.mutate({ incident: inc })}
                                className="text-primary hover:text-primary/80 text-sm disabled:opacity-50"
                                disabled={creatingTicketForIncident}
                                title="Create remediation ticket"
                              >
                                {creatingTicketForIncident ? 'Creating ticket...' : 'Create ticket'}
                              </button>
                            ) : null}
                            <Link
                              href={`/dashboard/incidents/${inc.id}`}
                              className="text-primary hover:text-primary/80 text-sm"
                            >
                              Open incident
                            </Link>
                            <Link
                              href={buildIncidentGraphHref(inc.id, {
                                sourceLabel: 'Back to incident queue',
                                sourceHref: '/dashboard/incidents',
                              })}
                              className="text-primary hover:text-primary/80 text-sm"
                            >
                              Open graph
                            </Link>
                          </div>
                        );
                      })()}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={11} className="px-6 py-12 text-center text-text-muted">
                    No incidents match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
