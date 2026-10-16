'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import clsx from 'clsx';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import StoryContextPanel from '@/components/operator/StoryContextPanel';
import CrossDomainRelationshipView from '@/components/operator/CrossDomainRelationshipView';
import IssueOwnershipSlaPanel from '@/components/operator/IssueOwnershipSlaPanel';
import ResponsePackPanel from '@/components/operator/ResponsePackPanel';
import SocCaseAgentPanel from '@/components/operator/SocCaseAgentPanel';
import { getIncidentAudit } from '@/lib/api/audit';
import {
  getIncident,
  getIncidentSocCaseState,
  submitIncidentSocFeedback,
  updateIncident,
  type Incident,
  type IncidentSocFeedbackPayload,
  type IncidentUpdatePayload,
} from '@/lib/api/incidents';
import { getSourceHealth, type SourceHealth } from '@/lib/api/siem';
import HealthBadge from '@/components/ui/HealthBadge';
import { describePlaybookExecution, playbooksApi } from '@/lib/api/playbooks';
import { matchResponsePacksForIncident } from '@/lib/playbooks/responsePacks';
import { addTicketComment, createTicket } from '@/lib/api/tickets';
import { useAuth } from '@/lib/providers/AuthProvider';
import { buildIncidentGraphHref } from '@/lib/security/graph-context';

type IncidentPhase = 'New' | 'Analyzing' | 'Containment' | 'Eradication/Recovery' | 'Monitoring' | 'Closed';
type IncidentSeverity = 'critical' | 'high' | 'medium' | 'low';
type IncidentStatus = 'open' | 'in_progress' | 'investigating' | 'resolved' | 'closed';

const severityColor = (sev: IncidentSeverity) =>
  sev === 'critical'
    ? 'bg-red-500/20 text-red-400'
    : sev === 'high'
      ? 'bg-orange-500/20 text-orange-400'
      : sev === 'medium'
        ? 'bg-yellow-500/20 text-yellow-400'
        : 'bg-blue-500/20 text-blue-300';

const INCIDENT_PHASES: IncidentPhase[] = [
  'New',
  'Analyzing',
  'Containment',
  'Eradication/Recovery',
  'Monitoring',
  'Closed',
];

const INCIDENT_STATUSES: IncidentStatus[] = ['open', 'in_progress', 'investigating', 'resolved', 'closed'];

export default function IncidentDetailPage() {
  const params = useParams();
  const incidentId = params.id as string;
  const isRealId = /^[0-9a-fA-F-]{32,36}$/.test(incidentId);
  const queryClient = useQueryClient();
  const { user, tenantId } = useAuth();
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [commentText, setCommentText] = useState('');
  const [draftPostingTarget, setDraftPostingTarget] = useState<
    'incident_note' | 'ticket_update' | 'timeline_event' | null
  >(null);

  const demoIncidents = useMemo<Record<string, Incident>>(
    () => ({
      'inc-demo-1': {
        id: 'inc-demo-1',
        title: 'Account takeover investigation',
        severity: 'high',
        phase: 'Analyzing',
        status: 'in_progress',
        assignee: 'SOC Manager',
        assigned_to: 'SOC Manager',
        sla: '4h',
        updated_at: new Date().toISOString(),
        related_detections: [{ id: 'demo-1', title: 'Suspicious login from unusual location', severity: 'high' }],
        external_ticket_id: 'ZMD-1001',
        external_ticket_provider: 'zammad',
      },
      'inc-demo-2': {
        id: 'inc-demo-2',
        title: 'Endpoint ransomware containment',
        severity: 'critical',
        phase: 'Containment',
        status: 'open',
        assignee: 'Analyst A',
        assigned_to: 'Analyst A',
        sla: '2h',
        updated_at: new Date().toISOString(),
        related_detections: [{ id: 'demo-2', title: 'Ransomware behavior detected on endpoint', severity: 'critical' }],
      },
    }),
    []
  );

  const { data: incident, isLoading, error } = useQuery({
    queryKey: ['incident', incidentId],
    queryFn: () => getIncident(incidentId),
    enabled: !!incidentId && isRealId,
    retry: 1,
  });

  const { data: auditEvents } = useQuery({
    queryKey: ['incident-audit', incidentId],
    queryFn: () => getIncidentAudit(incidentId),
    enabled: !!incidentId,
  });

  const { data: sourceHealth } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });
  const { data: playbooks } = useQuery({
    queryKey: ['playbooks-all'],
    queryFn: () => playbooksApi.list(),
  });
  const {
    data: socCaseState,
    isLoading: socCaseLoading,
    error: socCaseError,
  } = useQuery({
    queryKey: ['incident-soc-case', incidentId],
    queryFn: () => getIncidentSocCaseState(incidentId),
    enabled: !!incidentId && isRealId && !!incident,
    retry: false,
    staleTime: 15000,
  });

  const fallbackIncident = useMemo<Incident | null>(() => {
    if (isRealId) {
      return null;
    }
    return (
      demoIncidents[incidentId] || {
        id: incidentId,
        title: 'Sample incident',
        severity: 'high',
        phase: 'Analyzing',
        status: 'in_progress',
        assignee: 'SOC Manager',
        assigned_to: 'SOC Manager',
        sla: '4h',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        description: 'This is a sample incident view. Hook to /incidents/:id API to replace this.',
        related_detections: [{ id: 'det-123', title: 'Privilege escalation attempt', severity: 'critical' }],
        external_ticket_id: 'TCK-1024',
        external_ticket_provider: 'zammad',
        timeline: [
          { ts: new Date().toISOString(), text: 'Incident created (auto)', actor: 'system' },
          { ts: new Date().toISOString(), text: 'Assigned to SOC Manager', actor: 'system' },
        ],
      }
    );
  }, [demoIncidents, incidentId, isRealId]);

  const updateMutation = useMutation({
    mutationFn: (updates: IncidentUpdatePayload) => updateIncident(incidentId, updates),
    onSuccess: (updatedIncident) => {
      queryClient.setQueryData(['incident', incidentId], updatedIncident);
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident-audit', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-soc-case', incidentId] });
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: (payload: IncidentSocFeedbackPayload) => submitIncidentSocFeedback(incidentId, payload),
    onSuccess: (updatedState) => {
      queryClient.setQueryData(['incident-soc-case', incidentId], updatedState);
    },
  });

  const inc = incident || fallbackIncident;
  const isEditable = Boolean(incident);
  const matchedResponsePacks = useMemo(() => {
    if (!inc) return [];
    return matchResponsePacksForIncident(inc, playbooks || []);
  }, [inc, playbooks]);
  const timelineEntries = useMemo(() => {
    const merged = [...(inc?.timeline || []), ...(auditEvents || [])];
    const seen = new Set<string>();
    return merged
      .filter((entry) => {
        const key = `${entry.ts || ''}|${entry.text || ''}|${entry.actor || ''}`;
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      })
      .sort((left, right) => (left.ts || '').localeCompare(right.ts || ''));
  }, [auditEvents, inc?.timeline]);
  const storyEvidence = inc?.evidence || [];
  const relatedAlertEvidence = storyEvidence.filter((item) => item.type === 'alert');
  const relatedDetections = inc?.related_detections?.length
    ? inc.related_detections
    : relatedAlertEvidence.map((item) => ({
        id: item.id,
        title: item.title,
        severity: item.severity,
      }));

  const runPlaybookMutation = useMutation({
    mutationFn: (playbookId: string) =>
      playbooksApi.execute(playbookId, 'incident', incidentId, { incident_id: incidentId }),
    onMutate: () => {
      setActionMessage('Recording incident response execution request...');
      setActionError(null);
    },
    onSuccess: (response) => {
      setActionMessage(describePlaybookExecution(response));
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ['incident-soc-case', incidentId] });
    },
    onError: (mutationError: any) => {
      setActionError(mutationError?.message || 'Failed to record response playbook request.');
    },
  });

  const createTicketMutation = useMutation({
    mutationFn: async () => {
      if (!inc) {
        throw new Error('Incident not loaded');
      }

      return createTicket({
        title: `Respond to incident: ${inc.title}`,
        description: inc.description || `Operator handoff for incident ${inc.id}.`,
        severity: inc.severity,
        priority: inc.severity,
        category: 'incident_response',
        source: 'incident',
        alert_ids: relatedDetections.map((d) => d.id),
        assigned_to: inc.assigned_to || inc.assignee || user?.email || undefined,
        created_by: user?.email || undefined,
        incident_id: inc.id,
        incident_management_mode: 'linked_ticket',
      });
    },
    onMutate: () => {
      setActionMessage('Creating remediation ticket...');
      setActionError(null);
    },
    onSuccess: (ticket) => {
      queryClient.setQueryData<Incident | undefined>(['incident', incidentId], (current) =>
        current
          ? {
              ...current,
              ticket_id: ticket.id,
              external_ticket_id: ticket.external_id || current.external_ticket_id,
              external_ticket_provider: ticket.source || current.external_ticket_provider,
            }
          : current
      );
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
      queryClient.invalidateQueries({ queryKey: ['incident', incidentId] });
      queryClient.invalidateQueries({ queryKey: ['incident-soc-case', incidentId] });
      setActionMessage(`Remediation ticket ${ticket.id} created.`);
      setActionError(null);
    },
    onError: (mutationError: any) => {
      setActionError(mutationError?.message || 'Failed to create remediation ticket.');
    },
  });

  const saveIncidentUpdate = async (updates: IncidentUpdatePayload, successMessage: string) => {
    if (!isEditable) {
      return false;
    }
    try {
      setActionMessage(null);
      setActionError(null);
      await updateMutation.mutateAsync(updates);
      setActionMessage(successMessage);
      return true;
    } catch (mutationError: any) {
      setActionError(mutationError?.message || 'Failed to update incident.');
      return false;
    }
  };

  const postIncidentDraft = async (
    target: 'incident_note' | 'timeline_event',
    updates: IncidentUpdatePayload,
    successMessage: string
  ) => {
    setDraftPostingTarget(target);
    try {
      await saveIncidentUpdate(updates, successMessage);
    } finally {
      setDraftPostingTarget(null);
    }
  };

  const postTicketUpdateDraft = async (draft: string) => {
    if (!inc?.ticket_id) {
      setActionError('Link a ticket before posting the ticket update draft.');
      setActionMessage(null);
      return;
    }
    if (!tenantId) {
      setActionError('Tenant context is missing for the linked ticket update.');
      setActionMessage(null);
      return;
    }
    setDraftPostingTarget('ticket_update');
    try {
      setActionMessage(null);
      setActionError(null);
      await addTicketComment(inc.ticket_id, draft, tenantId);
      queryClient.invalidateQueries({ queryKey: ['incident-soc-case', incidentId] });
      setActionMessage('Ticket update draft posted to the linked ticket.');
    } catch (mutationError: any) {
      setActionError(mutationError?.message || 'Failed to post the ticket update draft.');
    } finally {
      setDraftPostingTarget(null);
    }
  };

  const handleIncidentComment = async () => {
    const trimmed = commentText.trim();
    if (!trimmed) {
      setActionError('Enter a note before saving.');
      setActionMessage(null);
      return;
    }
    const saved = await saveIncidentUpdate({ comment: trimmed }, 'Incident note added.');
    if (saved) {
      setCommentText('');
    }
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-8 bg-slate-800 rounded w-1/3" />
          <div className="h-6 bg-slate-800 rounded w-1/2" />
          <div className="h-40 bg-slate-800 rounded" />
        </div>
      </div>
    );
  }

  if (error && isRealId && !incident) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
          <h1 className="text-lg font-semibold text-red-100">Failed to load incident</h1>
          <p className="mt-2 text-sm text-red-200">
            The requested incident could not be loaded from the backend.
          </p>
        </div>
      </div>
    );
  }

  if (!inc) {
    return (
      <div className="p-6">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
          <h1 className="text-lg font-semibold text-red-100">Incident not found</h1>
        </div>
      </div>
    );
  }

  const phase = (inc.phase || inc.status || 'New') as IncidentPhase;
  const severity = (inc.severity as IncidentSeverity) || 'medium';
  const ticketLabel = inc.external_ticket_id
    ? `${inc.external_ticket_provider || 'ticket'}:${inc.external_ticket_id}`
    : inc.ticket_id
      ? `Local ticket ${inc.ticket_id}`
      : 'Local only';
  const ticketHref = inc.ticket_id ? `/dashboard/tickets/${inc.ticket_id}` : null;
  const primaryResponsePack = matchedResponsePacks[0];
  const latestRecommendation = socCaseState?.latest_recommendation || null;
  const recommendedPlaybook = latestRecommendation?.recommended_playbooks.find((playbook) => playbook.playbook_id) || null;
  const primaryPlaybookId = recommendedPlaybook?.playbook_id || primaryResponsePack?.primaryPlaybook?.id || null;
  const primaryPlaybookLabel = recommendedPlaybook?.playbook_name || primaryResponsePack?.primaryPlaybook?.name || null;
  const containmentReached = ['Containment', 'Eradication/Recovery', 'Monitoring', 'Closed'].includes(phase);
  const incidentGraphHref = buildIncidentGraphHref(inc.id);
  const socCaseErrorMessage = socCaseError instanceof Error ? socCaseError.message : null;
  const feedbackPendingKey = feedbackMutation.isPending
    ? feedbackMutation.variables?.action_id
      ? `action:${feedbackMutation.variables.action_id}`
      : `playbook:${
          feedbackMutation.variables?.playbook_id ||
          feedbackMutation.variables?.playbook_key ||
          feedbackMutation.variables?.playbook_name ||
          'pending'
        }`
    : null;

  const submitRecommendationFeedback = async (payload: Omit<IncidentSocFeedbackPayload, 'actor_id' | 'actor_role'>, successMessage: string) => {
    try {
      setActionMessage(null);
      setActionError(null);
      await feedbackMutation.mutateAsync({
        ...payload,
        actor_id: user?.email || user?.id || 'operator',
        actor_role: 'HUMAN_OWNER',
      });
      setActionMessage(successMessage);
    } catch (mutationError: any) {
      setActionError(mutationError?.message || 'Failed to record SOC AI feedback.');
    }
  };

  return (
    <div className="p-6 space-y-6">
      <Breadcrumbs />
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-text-main">{inc.title}</h1>
          <span className={clsx('px-3 py-1 text-xs font-semibold rounded', severityColor(severity))}>
            {severity.toUpperCase()}
          </span>
          <span className="px-3 py-1 text-xs font-semibold rounded bg-primary/20 text-primary">{phase}</span>
          <span className="px-3 py-1 text-xs font-semibold rounded bg-[rgba(255,255,255,0.05)] text-text-muted">
            {inc.status}
          </span>
        </div>
        <Link
          href={incidentGraphHref}
          className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-primary/30 px-4 py-2 text-sm font-medium text-text-main hover:border-primary/50"
        >
          Open security graph
        </Link>
      </div>

      <p className="text-text-muted">
        {(() => {
          const ts = inc.updated_at || inc.created_at || new Date().toISOString();
          return (
            <>
              Incident ID: {inc.id} • Last updated {new Date(ts).toLocaleString()}
            </>
          );
        })()}
      </p>

      <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-muted">
        <span className="uppercase tracking-wide">Pipeline health</span>
        <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
        <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
        <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
      </div>

      <div className="rounded-xl border border-surface-card-border bg-surface-card p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-main">Quick remediation</h2>
            <p className="mt-1 text-sm text-text-muted">
              Run the recommended response pack, move the case into containment, or create the linked remediation ticket without leaving this incident.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                if (!primaryPlaybookId) {
                  setActionError('No matched response pack is ready to launch.');
                  setActionMessage(null);
                  return;
                }
                runPlaybookMutation.mutate(primaryPlaybookId, {
                  onSuccess: () => {
                    setActionMessage(
                      `${latestRecommendation?.response_pack_label || primaryResponsePack?.pack.label || 'Recommended'} playbook execution started.`
                    );
                    setActionError(null);
                  },
                });
              }}
              disabled={!isEditable || !primaryPlaybookId || runPlaybookMutation.isPending}
              className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110 disabled:opacity-60"
            >
              {runPlaybookMutation.isPending
                ? 'Launching playbook...'
                : primaryPlaybookId
                  ? `Run ${latestRecommendation?.response_pack_label || primaryPlaybookLabel || 'recommended'} playbook`
                  : 'No playbook ready'}
            </button>
            <button
              type="button"
              onClick={() =>
                void saveIncidentUpdate(
                  { phase: 'Containment', status: inc.status === 'closed' ? inc.status : 'in_progress' },
                  'Incident moved to containment.'
                )
              }
              disabled={!isEditable || updateMutation.isPending || containmentReached}
              className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-primary/30 px-4 py-2 text-sm font-medium text-primary hover:bg-primary/10 disabled:opacity-60"
            >
              {containmentReached ? 'Containment active' : 'Move to containment'}
            </button>
            {ticketHref ? (
              <Link
                href={ticketHref}
                className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
              >
                Open linked ticket
              </Link>
            ) : (
              <button
                type="button"
                onClick={() => createTicketMutation.mutate()}
                disabled={!isEditable || createTicketMutation.isPending}
                className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40 disabled:opacity-60"
              >
                {createTicketMutation.isPending ? 'Creating ticket...' : 'Create remediation ticket'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
          <div className="text-sm text-text-muted mb-1">Assignee</div>
          <div className="text-text-main font-semibold">{inc.assignee || 'Unassigned'}</div>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
          <div className="text-sm text-text-muted mb-1">SLA</div>
          <div className="text-text-main font-semibold">
            {inc.due_date ? new Date(inc.due_date).toLocaleString() : inc.sla || 'Not set'}
          </div>
        </div>
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-4">
          <div className="text-sm text-text-muted mb-1">Ticket linkage</div>
          {ticketHref ? (
            <Link href={ticketHref} className="text-primary font-semibold hover:text-primary/80">
              {ticketLabel}
            </Link>
          ) : (
            <div className="text-text-main font-semibold">{ticketLabel}</div>
          )}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[220px,220px]">
        <div className="rounded-xl border border-surface-card-border bg-surface-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Status</p>
          <select
            value={(inc.status || 'open') as IncidentStatus}
            onChange={(event) =>
              void saveIncidentUpdate(
                { status: event.target.value as IncidentStatus },
                `Incident status updated to ${event.target.value.replace('_', ' ')}.`
              )
            }
            disabled={!isEditable || updateMutation.isPending}
            className="mt-3 w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.8)] px-3 py-2 text-sm text-text-main disabled:opacity-60"
          >
            {INCIDENT_STATUSES.map((statusOption) => (
              <option key={statusOption} value={statusOption}>
                {statusOption.replace('_', ' ')}
              </option>
            ))}
          </select>
        </div>

        <div className="rounded-xl border border-surface-card-border bg-surface-card p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Phase</p>
          <select
            value={phase}
            onChange={(event) =>
              void saveIncidentUpdate(
                { phase: event.target.value as IncidentPhase },
                `Incident phase updated to ${event.target.value}.`
              )
            }
            disabled={!isEditable || updateMutation.isPending}
            className="mt-3 w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.8)] px-3 py-2 text-sm text-text-main disabled:opacity-60"
          >
            {INCIDENT_PHASES.map((phaseOption) => (
              <option key={phaseOption} value={phaseOption}>
                {phaseOption}
              </option>
            ))}
          </select>
        </div>
      </div>

      <IssueOwnershipSlaPanel
        issueLabel="Incident"
        currentOwner={inc.assigned_to || inc.assignee}
        currentDueDate={inc.due_date}
        onOwnerSave={async (assignedTo) => {
          await saveIncidentUpdate(
            { assigned_to: assignedTo.trim() || null },
            `Incident assignment updated${assignedTo ? ` to ${assignedTo}` : ''}.`
          );
        }}
        onDueDateSave={async (dueDate) => {
          await saveIncidentUpdate(
            { due_date: dueDate },
            `Incident SLA target ${dueDate ? 'updated' : 'cleared'}.`
          );
        }}
        ownerSaving={updateMutation.isPending}
        dueDateSaving={updateMutation.isPending}
        assignmentTitle="Incident ownership"
        assignmentDescription="Use the configured downstream directory search to set the incident owner."
        assignmentSaveLabel="Save incident owner"
      />

      {(actionMessage || actionError || !isEditable) && (
        <div
          className={clsx(
            'rounded-xl border px-4 py-3 text-sm',
            actionError
              ? 'border-red-500/30 bg-red-500/10 text-red-100'
              : 'border-cyan-500/30 bg-cyan-500/10 text-cyan-100'
          )}
        >
          {actionError || actionMessage || 'This sample incident is read-only.'}
        </div>
      )}

      <StoryContextPanel
        title="Cross-domain story"
        description="Linked identities, assets, cloud resources, AI apps, and supporting evidence for this incident."
        domains={inc.story_domains}
        entities={inc.entities}
        evidence={inc.evidence}
        emptyEntityText="No linked entities have been normalized for this incident yet."
        emptyEvidenceText="No supporting evidence has been linked yet."
        graphHref={incidentGraphHref}
        getEntityGraphHref={(entity) =>
          buildIncidentGraphHref(inc.id, {
            focusEntityId: entity.id,
            sourceLabel: 'Back to incident',
            sourceHref: `/dashboard/incidents/${inc.id}`,
          })
        }
        getEvidenceGraphHref={(item) =>
          buildIncidentGraphHref(inc.id, {
            focusEvidenceId: item.id,
            sourceLabel: 'Back to incident',
            sourceHref: `/dashboard/incidents/${inc.id}`,
          })
        }
      />

      <CrossDomainRelationshipView
        title="Cross-domain relationships"
        description="See how this incident connects people, assets, cloud resources, AI activity, and supporting workflows before you pivot into the next investigation surface."
        domains={inc.story_domains}
        entities={inc.entities}
        evidence={inc.evidence}
      />

      <SocCaseAgentPanel
        state={socCaseState}
        isLoading={socCaseLoading}
        errorMessage={socCaseErrorMessage}
        feedbackPendingKey={feedbackPendingKey}
        draftPostingTarget={draftPostingTarget}
        onUseIncidentNoteDraft={(draft) => {
          setCommentText(draft);
          setActionMessage('SOC AI incident draft loaded into the note composer.');
          setActionError(null);
        }}
        onPostIncidentNoteDraft={(draft) => {
          void postIncidentDraft(
            'incident_note',
            { comment: draft },
            'SOC AI incident note posted to the incident.'
          );
        }}
        onPostTicketUpdateDraft={
          inc.ticket_id
            ? (draft) => {
                void postTicketUpdateDraft(draft);
              }
            : undefined
        }
        onPostTimelineEventDraft={(draft) => {
          void postIncidentDraft(
            'timeline_event',
            { timeline_event: draft },
            'SOC AI timeline draft posted to the incident timeline.'
          );
        }}
        onAcceptPlaybook={(playbook) => {
          if (!latestRecommendation) return;
          void submitRecommendationFeedback(
            {
              recommendation_id: latestRecommendation.recommendation_id,
              feedback_type: 'accepted_recommendation',
              accepted: true,
              playbook_id: playbook.playbook_id || null,
              playbook_key: playbook.playbook_key || null,
              playbook_name: playbook.playbook_name,
            },
            `Accepted playbook recommendation: ${playbook.playbook_name}.`
          );
        }}
        onRejectPlaybook={(playbook) => {
          if (!latestRecommendation) return;
          void submitRecommendationFeedback(
            {
              recommendation_id: latestRecommendation.recommendation_id,
              feedback_type: 'rejected_recommendation',
              accepted: false,
              playbook_id: playbook.playbook_id || null,
              playbook_key: playbook.playbook_key || null,
              playbook_name: playbook.playbook_name,
            },
            `Rejected playbook recommendation: ${playbook.playbook_name}.`
          );
        }}
        onAcceptAction={(action) => {
          if (!latestRecommendation) return;
          void submitRecommendationFeedback(
            {
              recommendation_id: latestRecommendation.recommendation_id,
              feedback_type: 'accepted_recommendation',
              accepted: true,
              action_id: action.action_id,
            },
            `Accepted action recommendation: ${action.label}.`
          );
        }}
        onRejectAction={(action) => {
          if (!latestRecommendation) return;
          void submitRecommendationFeedback(
            {
              recommendation_id: latestRecommendation.recommendation_id,
              feedback_type: 'rejected_recommendation',
              accepted: false,
              action_id: action.action_id,
            },
            `Rejected action recommendation: ${action.label}.`
          );
        }}
      />

      <ResponsePackPanel
        title="Saved response packs"
        description="Use the shared SMB response-pack library to move from incident context into the right containment, ownership, and playbook sequence."
        packs={matchedResponsePacks}
        runningPlaybookId={(runPlaybookMutation.variables as string | undefined) || null}
        onRunPlaybook={
          isEditable
            ? (playbookId, pack) => {
                runPlaybookMutation.mutate(playbookId, {
                  onSuccess: () => {
                    setActionMessage(`${pack.pack.label} playbook execution started.`);
                    setActionError(null);
                  },
                });
              }
            : undefined
        }
        emptyState="No saved response pack matched this incident yet. Open the playbook library if the operator needs a broader response workflow."
      />

      <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-text-main">Notes</h2>
            <p className="mt-1 text-sm text-text-muted">
              Add analyst notes to the incident. Linked tickets receive the same note when comment sync is available.
            </p>
          </div>
          {ticketHref && (
            <Link href={ticketHref} className="text-sm font-medium text-primary hover:text-primary/80">
              Open linked ticket
            </Link>
          )}
        </div>
        <div className="mt-4 space-y-3">
          <textarea
            value={commentText}
            onChange={(event) => {
              setCommentText(event.target.value);
              setActionError(null);
              setActionMessage(null);
            }}
            rows={4}
            placeholder="Summarize investigation progress, remediation context, or the next operator handoff."
            disabled={!isEditable || updateMutation.isPending}
            className="w-full rounded-lg border border-[rgba(148,163,184,0.2)] bg-[rgba(15,23,42,0.85)] px-3 py-2 text-sm text-text-main disabled:opacity-60"
          />
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => void handleIncidentComment()}
              disabled={!isEditable || updateMutation.isPending}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-bg disabled:opacity-60"
            >
              Add note
            </button>
            {!isEditable && <span className="text-xs text-text-muted">Demo incidents are read-only.</span>}
          </div>
        </div>
      </div>

      <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
        <h2 className="text-lg font-semibold text-text-main mb-3">Description</h2>
        <p className="text-text-main text-sm">{inc.description || 'No description provided.'}</p>
        {inc.raw_payload?.ai_summary && (
          <p className="text-sm text-primary mt-2">AI summary: {inc.raw_payload.ai_summary}</p>
        )}
        {inc.detection_rule_id && (
          <div className="mt-3 text-xs text-text-muted">
            Detection rule:
            <a href={`/dashboard/siem/detection-rules/${inc.detection_rule_id}`} className="text-primary ml-1">
              {inc.detection_rule_id}
            </a>
            {inc.detection_rule_version_id && <span className="ml-2">vID: {inc.detection_rule_version_id}</span>}
          </div>
        )}
        {inc.playbook_version_id && (
          <div className="text-xs text-text-muted mt-1">Playbook version: {inc.playbook_version_id}</div>
        )}
      </div>

      <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-text-main">Related detections</h2>
          <span className="text-xs text-text-muted">{relatedDetections.length} linked</span>
        </div>
        {relatedDetections.length > 0 ? (
          <div className="space-y-2">
            {relatedDetections.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between rounded border border-[rgba(255,255,255,0.05)] px-3 py-2"
              >
                <div>
                  <div className="text-sm font-semibold text-text-main">{d.title || d.id}</div>
                  <div className="text-[11px] text-text-muted">{d.id}</div>
                </div>
                <Link href={`/dashboard/alerts/${d.id}`} className="text-primary text-sm hover:text-primary/80">
                  View detection
                </Link>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No detections linked.</p>
        )}
      </div>

      <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
        <h2 className="text-lg font-semibold text-text-main mb-3">Timeline</h2>
        <div className="space-y-2">
          {timelineEntries.length > 0 ? (
            timelineEntries.map((entry, idx) => (
              <div key={`${entry.ts || 'event'}-${idx}`} className="flex items-start gap-3">
                <div className="w-36 text-xs text-text-muted">
                  {entry.ts ? new Date(entry.ts).toLocaleString() : '—'}
                </div>
                <div className="text-sm text-text-main">{entry.text || 'Event'}</div>
                {entry.actor && <div className="text-xs text-text-muted">({entry.actor})</div>}
              </div>
            ))
          ) : (
            <p className="text-sm text-text-muted">No timeline entries yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
