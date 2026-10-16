'use client';

import clsx from 'clsx';
import type {
  IncidentSocCaseState,
  SocActionRecommendation,
  SocCaseTaskSummary,
  SocPlaybookRecommendation,
} from '@/lib/api/incidents';

interface SocCaseAgentPanelProps {
  state?: IncidentSocCaseState | null;
  isLoading?: boolean;
  errorMessage?: string | null;
  onUseIncidentNoteDraft?: (draft: string) => void;
  onPostIncidentNoteDraft?: (draft: string) => void;
  onPostTicketUpdateDraft?: (draft: string) => void;
  onPostTimelineEventDraft?: (draft: string) => void;
  onAcceptPlaybook?: (playbook: SocPlaybookRecommendation) => void;
  onRejectPlaybook?: (playbook: SocPlaybookRecommendation) => void;
  onAcceptAction?: (action: SocActionRecommendation) => void;
  onRejectAction?: (action: SocActionRecommendation) => void;
  feedbackPendingKey?: string | null;
  draftPostingTarget?: 'incident_note' | 'ticket_update' | 'timeline_event' | null;
}

function riskTone(riskLevel: SocActionRecommendation['risk_level']) {
  switch (riskLevel) {
    case 'critical':
      return 'border-red-500/40 bg-red-500/15 text-red-100';
    case 'high':
      return 'border-orange-500/40 bg-orange-500/15 text-orange-100';
    case 'medium':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-100';
    case 'low':
      return 'border-emerald-500/40 bg-emerald-500/15 text-emerald-100';
    case 'investigative':
      return 'border-sky-500/40 bg-sky-500/15 text-sky-100';
    default:
      return 'border-slate-500/40 bg-slate-500/15 text-slate-100';
  }
}

function taskTone(status: SocCaseTaskSummary['status']) {
  switch (status) {
    case 'completed':
      return 'border-emerald-500/40 bg-emerald-500/15 text-emerald-100';
    case 'failed':
      return 'border-red-500/40 bg-red-500/15 text-red-100';
    case 'running':
      return 'border-sky-500/40 bg-sky-500/15 text-sky-100';
    case 'queued':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-100';
    default:
      return 'border-slate-500/40 bg-slate-500/15 text-slate-100';
  }
}

function automationTone(mode: SocPlaybookRecommendation['automation_mode']) {
  switch (mode) {
    case 'automated':
      return 'border-emerald-500/40 bg-emerald-500/15 text-emerald-100';
    case 'approval_required':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-100';
    default:
      return 'border-slate-500/40 bg-slate-500/15 text-slate-100';
  }
}

function feedbackTone(status?: SocPlaybookRecommendation['status']) {
  switch (status) {
    case 'accepted':
      return 'border-emerald-500/40 bg-emerald-500/15 text-emerald-100';
    case 'rejected':
      return 'border-red-500/40 bg-red-500/15 text-red-100';
    case 'executed':
      return 'border-sky-500/40 bg-sky-500/15 text-sky-100';
    case 'skipped':
      return 'border-slate-500/40 bg-slate-500/15 text-slate-100';
    default:
      return 'border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted';
  }
}

function formatEnumLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatTimestamp(value?: string | null) {
  if (!value) return 'Unknown';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export default function SocCaseAgentPanel({
  state,
  isLoading = false,
  errorMessage,
  onUseIncidentNoteDraft,
  onPostIncidentNoteDraft,
  onPostTicketUpdateDraft,
  onPostTimelineEventDraft,
  onAcceptPlaybook,
  onRejectPlaybook,
  onAcceptAction,
  onRejectAction,
  feedbackPendingKey,
  draftPostingTarget,
}: SocCaseAgentPanelProps) {
  const latestRecommendation = state?.latest_recommendation || null;
  const recommendationVersions = state?.recommendation_versions || [];
  const historicalRecommendations = latestRecommendation
    ? recommendationVersions.filter(
        (recommendation) => recommendation.recommendation_id !== latestRecommendation.recommendation_id
      )
    : recommendationVersions;
  const recentTasks = state?.recent_tasks || [];

  return (
    <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-main">SOC AI Agent</h2>
          <p className="mt-1 text-sm text-text-muted">
            Supervised case guidance for the current incident. The agent recommends the response path,
            drafts operator notes, and records its recent planning activity here.
          </p>
        </div>
        {latestRecommendation && (
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
              {latestRecommendation.response_pack_label}
            </span>
            <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
              Confidence {(latestRecommendation.confidence * 100).toFixed(0)}%
            </span>
            {latestRecommendation.proposed_phase && (
              <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                Proposed phase: {latestRecommendation.proposed_phase}
              </span>
            )}
            {latestRecommendation.proposed_status && (
              <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                Proposed status: {latestRecommendation.proposed_status}
              </span>
            )}
          </div>
        )}
      </div>

      {isLoading ? (
        <div className="mt-5 animate-pulse space-y-3">
          <div className="h-5 w-1/3 rounded bg-slate-800" />
          <div className="h-4 w-full rounded bg-slate-800" />
          <div className="h-4 w-5/6 rounded bg-slate-800" />
          <div className="h-24 rounded bg-slate-800" />
        </div>
      ) : errorMessage ? (
        <div className="mt-5 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
          {errorMessage}
        </div>
      ) : !latestRecommendation ? (
        <div className="mt-5 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4 text-sm text-text-muted">
          No SOC AI recommendation has been generated for this incident yet.
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Current case summary
                </p>
                <p className="mt-2 text-sm text-text-main">{latestRecommendation.case_summary}</p>
              </div>
              <div className="text-xs text-text-muted">
                Recommendation generated {formatTimestamp(latestRecommendation.generated_at)}
              </div>
            </div>

            {latestRecommendation.missing_evidence.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Missing evidence
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {latestRecommendation.missing_evidence.map((item) => (
                    <span
                      key={item}
                      className="rounded-full border border-amber-500/40 bg-amber-500/15 px-2.5 py-1 text-[11px] text-amber-100"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.05fr,0.95fr]">
            <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Recommended playbooks
              </p>
              <div className="mt-3 space-y-3">
                {latestRecommendation.recommended_playbooks.map((playbook) => (
                  <div
                    key={`${playbook.playbook_id || playbook.playbook_key || playbook.playbook_name}-${playbook.rank}`}
                    className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="text-sm font-semibold text-text-main">
                          {playbook.rank}. {playbook.playbook_name}
                        </div>
                        <div className="mt-1 text-xs text-text-muted">
                          Confidence {(playbook.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                      <span
                        className={clsx(
                          'rounded-full border px-2.5 py-1 text-[11px]',
                          automationTone(playbook.automation_mode)
                        )}
                      >
                        {formatEnumLabel(playbook.automation_mode)}
                      </span>
                      <span
                        className={clsx(
                          'rounded-full border px-2.5 py-1 text-[11px]',
                          feedbackTone(playbook.status)
                        )}
                      >
                        {formatEnumLabel(playbook.status || 'recommended')}
                      </span>
                    </div>
                    {playbook.rationale.length > 0 && (
                      <ul className="mt-2 space-y-1 text-sm text-text-muted">
                        {playbook.rationale.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    )}
                    {(onAcceptPlaybook || onRejectPlaybook) && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {onAcceptPlaybook && (
                          <button
                            type="button"
                            onClick={() => onAcceptPlaybook(playbook)}
                            disabled={
                              feedbackPendingKey === `playbook:${playbook.playbook_id || playbook.playbook_key || playbook.playbook_name}` ||
                              playbook.status === 'accepted'
                            }
                            className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-60"
                          >
                            Accept playbook
                          </button>
                        )}
                        {onRejectPlaybook && (
                          <button
                            type="button"
                            onClick={() => onRejectPlaybook(playbook)}
                            disabled={
                              feedbackPendingKey === `playbook:${playbook.playbook_id || playbook.playbook_key || playbook.playbook_name}` ||
                              playbook.status === 'rejected'
                            }
                            className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-200 hover:bg-red-500/10 disabled:opacity-60"
                          >
                            Reject playbook
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Why this recommendation
              </p>
              <ul className="mt-3 space-y-2 text-sm text-text-main">
                {latestRecommendation.rationale.map((reason) => (
                  <li
                    key={reason}
                    className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-2"
                  >
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Recommended next actions
            </p>
            <div className="mt-3 space-y-3">
              {latestRecommendation.recommended_actions.map((action) => (
                <div
                  key={action.action_id}
                  className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="text-sm font-semibold text-text-main">{action.label}</div>
                    <span
                      className={clsx(
                        'rounded-full border px-2.5 py-1 text-[11px]',
                        riskTone(action.risk_level)
                      )}
                    >
                      {formatEnumLabel(action.risk_level)}
                    </span>
                    <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                      Owner {action.recommended_owner_role}
                    </span>
                    {action.requires_approval && (
                      <span className="rounded-full border border-amber-500/40 bg-amber-500/15 px-2.5 py-1 text-[11px] text-amber-100">
                        Approval required
                      </span>
                    )}
                    <span
                      className={clsx(
                        'rounded-full border px-2.5 py-1 text-[11px]',
                        feedbackTone(action.status)
                      )}
                    >
                      {formatEnumLabel(action.status)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-text-main">{action.description}</p>
                  {action.evidence_basis.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {action.evidence_basis.map((item) => (
                        <span
                          key={item}
                          className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted"
                        >
                          {item}
                        </span>
                      ))}
                    </div>
                  )}
                  {(onAcceptAction || onRejectAction) && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {onAcceptAction && (
                        <button
                          type="button"
                          onClick={() => onAcceptAction(action)}
                          disabled={
                            feedbackPendingKey === `action:${action.action_id}` || action.status === 'accepted'
                          }
                          className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-60"
                        >
                          Accept action
                        </button>
                      )}
                      {onRejectAction && (
                        <button
                          type="button"
                          onClick={() => onRejectAction(action)}
                          disabled={
                            feedbackPendingKey === `action:${action.action_id}` || action.status === 'rejected'
                          }
                          className="rounded-lg border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-200 hover:bg-red-500/10 disabled:opacity-60"
                        >
                          Reject action
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Incident note draft
                </p>
                <div className="flex flex-wrap gap-2">
                  {latestRecommendation.incident_note_draft && onUseIncidentNoteDraft && (
                    <button
                      type="button"
                      onClick={() => onUseIncidentNoteDraft(latestRecommendation.incident_note_draft!)}
                      className="rounded-lg border border-primary/30 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10"
                    >
                      Use as incident note
                    </button>
                  )}
                  {latestRecommendation.incident_note_draft && onPostIncidentNoteDraft && (
                    <button
                      type="button"
                      onClick={() => onPostIncidentNoteDraft(latestRecommendation.incident_note_draft!)}
                      disabled={draftPostingTarget === 'incident_note'}
                      className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-60"
                    >
                      Post to incident
                    </button>
                  )}
                </div>
              </div>
              <p className="mt-3 whitespace-pre-wrap rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3 text-sm text-text-main">
                {latestRecommendation.incident_note_draft || 'No incident note draft yet.'}
              </p>
            </div>

            <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Ticket update draft
                </p>
                {latestRecommendation.ticket_update_draft && onPostTicketUpdateDraft && (
                  <button
                    type="button"
                    onClick={() => onPostTicketUpdateDraft(latestRecommendation.ticket_update_draft!)}
                    disabled={draftPostingTarget === 'ticket_update'}
                    className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-60"
                  >
                    Post to ticket
                  </button>
                )}
              </div>
              <p className="mt-3 whitespace-pre-wrap rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3 text-sm text-text-main">
                {latestRecommendation.ticket_update_draft || 'No ticket update draft yet.'}
              </p>
            </div>

            <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Timeline event draft
                </p>
                {latestRecommendation.timeline_event_draft && onPostTimelineEventDraft && (
                  <button
                    type="button"
                    onClick={() => onPostTimelineEventDraft(latestRecommendation.timeline_event_draft!)}
                    disabled={draftPostingTarget === 'timeline_event'}
                    className="rounded-lg border border-emerald-500/30 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-60"
                  >
                    Post to timeline
                  </button>
                )}
              </div>
              <p className="mt-3 whitespace-pre-wrap rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3 text-sm text-text-main">
                {latestRecommendation.timeline_event_draft || 'No timeline event draft yet.'}
              </p>
            </div>
          </div>

          {historicalRecommendations.length > 0 && (
            <div className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
              <div className="flex items-center justify-between gap-3">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Recommendation history
                </p>
                <span className="text-xs text-text-muted">
                  {historicalRecommendations.length} prior recommendation
                  {historicalRecommendations.length === 1 ? '' : 's'}
                </span>
              </div>
              <div className="mt-3 space-y-3">
                {historicalRecommendations.map((recommendation) => (
                  <div
                    key={recommendation.recommendation_id}
                    className="rounded-lg border border-[rgba(148,163,184,0.12)] px-4 py-4"
                  >
                    <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="text-sm font-semibold text-text-main">
                          {recommendation.response_pack_label}
                        </div>
                        <div className="mt-1 text-xs text-text-muted">
                          Generated {formatTimestamp(recommendation.generated_at)} • Confidence{' '}
                          {(recommendation.confidence * 100).toFixed(0)}%
                        </div>
                      </div>
                      {recommendation.incident_note_draft && onUseIncidentNoteDraft && (
                        <button
                          type="button"
                          onClick={() => onUseIncidentNoteDraft(recommendation.incident_note_draft!)}
                          className="rounded-lg border border-primary/30 px-3 py-1.5 text-xs font-medium text-primary hover:bg-primary/10"
                        >
                          Load note draft
                        </button>
                      )}
                    </div>
                    <p className="mt-3 text-sm text-text-main">{recommendation.case_summary}</p>
                    <div className="mt-3 grid gap-3 xl:grid-cols-3">
                      <div className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                          Incident note
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm text-text-main">
                          {recommendation.incident_note_draft || 'No stored incident note draft.'}
                        </p>
                      </div>
                      <div className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                          Ticket update
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm text-text-main">
                          {recommendation.ticket_update_draft || 'No stored ticket update draft.'}
                        </p>
                      </div>
                      <div className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-muted">
                          Timeline draft
                        </p>
                        <p className="mt-2 whitespace-pre-wrap text-sm text-text-main">
                          {recommendation.timeline_event_draft || 'No stored timeline draft.'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {recentTasks.length > 0 && (
        <div className="mt-5 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Recent agent activity
            </p>
            <span className="text-xs text-text-muted">{recentTasks.length} recent tasks</span>
          </div>
          <div className="mt-3 space-y-3">
            {recentTasks.map((task) => (
              <div
                key={task.id}
                className="flex flex-col gap-2 rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-3 lg:flex-row lg:items-center lg:justify-between"
              >
                <div>
                  <div className="text-sm font-semibold text-text-main">
                    {formatEnumLabel(task.task_type)}
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    Updated {formatTimestamp(task.updated_at)}
                  </div>
                </div>
                <span
                  className={clsx('rounded-full border px-2.5 py-1 text-[11px]', taskTone(task.status))}
                >
                  {formatEnumLabel(task.status)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
