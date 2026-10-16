import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import SocCaseAgentPanel from '../SocCaseAgentPanel';
import type { IncidentSocCaseState } from '@/lib/api/incidents';

function buildSocCaseState(): IncidentSocCaseState {
  return {
    tenant_id: 'tenant-123',
    incident_id: 'incident-123',
    case_id: 'case-123',
    case_context: {},
    case_memory: {},
    latest_recommendation: {
      recommendation_id: 'rec-1',
      generated_at: '2026-03-30T12:00:00Z',
      case_summary: 'Suspicious login activity suggests likely account takeover.',
      response_pack_id: 'account_takeover',
      response_pack_label: 'Account takeover',
      recommended_playbooks: [
        {
          playbook_id: 'playbook-1',
          playbook_name: 'Account compromise investigation',
          rank: 1,
          confidence: 0.91,
          rationale: ['Matched suspicious login and MFA challenge failure.'],
          automation_mode: 'manual_review',
        },
      ],
      recommended_actions: [
        {
          action_id: 'action-1',
          action_type: 'enrich_identity',
          label: 'Review identity sign-in history',
          description: 'Validate whether the sign-in pattern matches known user behavior.',
          risk_level: 'investigative',
          requires_approval: false,
          recommended_owner_role: 'L1',
          evidence_basis: ['Impossible travel alert', 'MFA failure'],
          status: 'recommended',
        },
      ],
      missing_evidence: ['Confirm affected device posture'],
      proposed_phase: 'Analyzing',
      proposed_status: 'investigating',
      incident_note_draft: 'AI draft note',
      ticket_update_draft: 'AI draft ticket update',
      timeline_event_draft: 'AI timeline draft',
      confidence: 0.84,
      rationale: ['Primary signal matches account takeover behavior.'],
    },
    recommendation_versions: [
      {
        recommendation_id: 'rec-older',
        generated_at: '2026-03-30T11:00:00Z',
        case_summary: 'Earlier recommendation version.',
        response_pack_id: 'manual_investigation',
        response_pack_label: 'Manual investigation',
        recommended_playbooks: [],
        recommended_actions: [],
        missing_evidence: ['Validate user intent'],
        incident_note_draft: 'Older AI draft note',
        ticket_update_draft: 'Older AI draft ticket update',
        timeline_event_draft: 'Older AI timeline draft',
        closure_checklist: [],
        confidence: 0.42,
        rationale: ['Insufficient evidence during the first pass.'],
      },
      {
        recommendation_id: 'rec-1',
        generated_at: '2026-03-30T12:00:00Z',
        case_summary: 'Suspicious login activity suggests likely account takeover.',
        response_pack_id: 'account_takeover',
        response_pack_label: 'Account takeover',
        recommended_playbooks: [
          {
            playbook_id: 'playbook-1',
            playbook_name: 'Account compromise investigation',
            rank: 1,
            confidence: 0.91,
            rationale: ['Matched suspicious login and MFA challenge failure.'],
            automation_mode: 'manual_review',
          },
        ],
        recommended_actions: [
          {
            action_id: 'action-1',
            action_type: 'enrich_identity',
            label: 'Review identity sign-in history',
            description: 'Validate whether the sign-in pattern matches known user behavior.',
            risk_level: 'investigative',
            requires_approval: false,
            recommended_owner_role: 'L1',
            evidence_basis: ['Impossible travel alert', 'MFA failure'],
            status: 'recommended',
          },
        ],
        missing_evidence: ['Confirm affected device posture'],
        proposed_phase: 'Analyzing',
        proposed_status: 'investigating',
        incident_note_draft: 'AI draft note',
        ticket_update_draft: 'AI draft ticket update',
        timeline_event_draft: 'AI timeline draft',
        confidence: 0.84,
        rationale: ['Primary signal matches account takeover behavior.'],
        closure_checklist: [],
      },
    ],
    recent_tasks: [
      {
        id: 'task-1',
        tenant_id: 'tenant-123',
        incident_id: 'incident-123',
        case_id: 'case-123',
        agent_id: 'soc_case_agent',
        task_type: 'triage_new_incident',
        priority: 'high',
        status: 'completed',
        payload: {},
        context: {},
        created_at: '2026-03-30T12:00:00Z',
        updated_at: '2026-03-30T12:01:00Z',
      },
    ],
  };
}

describe('SocCaseAgentPanel', () => {
  it('renders the latest recommendation and recent activity', () => {
    render(<SocCaseAgentPanel state={buildSocCaseState()} />);

    expect(screen.getByText(/SOC AI Agent/i)).toBeInTheDocument();
    expect(screen.getByText(/Suspicious login activity suggests likely account takeover/i)).toBeInTheDocument();
    expect(screen.getByText('Account takeover', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getByText(/Review identity sign-in history/i)).toBeInTheDocument();
    expect(screen.getByText(/Impossible travel alert/i)).toBeInTheDocument();
    expect(screen.getByText(/triage new incident/i)).toBeInTheDocument();
  });

  it('allows loading the incident note draft into the composer', async () => {
    const user = userEvent.setup();
    const onUseIncidentNoteDraft = jest.fn();

    render(
      <SocCaseAgentPanel
        state={buildSocCaseState()}
        onUseIncidentNoteDraft={onUseIncidentNoteDraft}
      />
    );

    await user.click(screen.getByRole('button', { name: /use as incident note/i }));

    expect(onUseIncidentNoteDraft).toHaveBeenCalledWith('AI draft note');
  });

  it('renders recommendation history and can load an older draft', async () => {
    const user = userEvent.setup();
    const onUseIncidentNoteDraft = jest.fn();

    render(
      <SocCaseAgentPanel
        state={buildSocCaseState()}
        onUseIncidentNoteDraft={onUseIncidentNoteDraft}
      />
    );

    expect(screen.getByText(/Recommendation history/i)).toBeInTheDocument();
    expect(screen.getByText(/Earlier recommendation version\./i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /load note draft/i }));

    expect(onUseIncidentNoteDraft).toHaveBeenCalledWith('Older AI draft note');
  });

  it('emits accept and reject callbacks for recommended playbooks and actions', async () => {
    const user = userEvent.setup();
    const onAcceptPlaybook = jest.fn();
    const onRejectAction = jest.fn();

    render(
      <SocCaseAgentPanel
        state={buildSocCaseState()}
        onAcceptPlaybook={onAcceptPlaybook}
        onRejectAction={onRejectAction}
      />
    );

    await user.click(screen.getByRole('button', { name: /accept playbook/i }));
    await user.click(screen.getByRole('button', { name: /reject action/i }));

    expect(onAcceptPlaybook).toHaveBeenCalledWith(
      expect.objectContaining({ playbook_id: 'playbook-1', playbook_name: 'Account compromise investigation' })
    );
    expect(onRejectAction).toHaveBeenCalledWith(
      expect.objectContaining({ action_id: 'action-1', label: 'Review identity sign-in history' })
    );
  });

  it('emits posting callbacks for incident, ticket, and timeline drafts', async () => {
    const user = userEvent.setup();
    const onPostIncidentNoteDraft = jest.fn();
    const onPostTicketUpdateDraft = jest.fn();
    const onPostTimelineEventDraft = jest.fn();

    render(
      <SocCaseAgentPanel
        state={buildSocCaseState()}
        onPostIncidentNoteDraft={onPostIncidentNoteDraft}
        onPostTicketUpdateDraft={onPostTicketUpdateDraft}
        onPostTimelineEventDraft={onPostTimelineEventDraft}
      />
    );

    await user.click(screen.getByRole('button', { name: /post to incident/i }));
    await user.click(screen.getByRole('button', { name: /post to ticket/i }));
    await user.click(screen.getByRole('button', { name: /post to timeline/i }));

    expect(onPostIncidentNoteDraft).toHaveBeenCalledWith('AI draft note');
    expect(onPostTicketUpdateDraft).toHaveBeenCalledWith('AI draft ticket update');
    expect(onPostTimelineEventDraft).toHaveBeenCalledWith('AI timeline draft');
  });
});
