import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import IncidentDetailPage from '../page';
import { renderWithProviders } from '@/test-utils/renderWithProviders';
import {
  getIncident,
  getIncidentSocCaseState,
  submitIncidentSocFeedback,
  updateIncident,
} from '@/lib/api/incidents';
import { getIncidentAudit } from '@/lib/api/audit';
import { getSourceHealth } from '@/lib/api/siem';
import { playbooksApi } from '@/lib/api/playbooks';
import { addTicketComment, createTicket } from '@/lib/api/tickets';
import { useAuth } from '@/lib/providers/AuthProvider';

jest.mock('next/navigation', () => {
  const { getMockPathname, getMockRouter, getMockSearchParams } = require('@/test-utils/navigation');
  return {
    useRouter() {
      return getMockRouter();
    },
    useSearchParams() {
      return getMockSearchParams();
    },
    usePathname() {
      return getMockPathname();
    },
    useParams() {
      return { id: '11111111-1111-1111-1111-111111111111' };
    },
  };
});

jest.mock('@/components/ui/Breadcrumbs', () => {
  const BreadcrumbsMock = () => <div>Breadcrumbs</div>;
  BreadcrumbsMock.displayName = 'BreadcrumbsMock';
  return BreadcrumbsMock;
});
jest.mock('@/components/operator/StoryContextPanel', () => {
  const StoryContextPanelMock = () => <div>StoryContextPanel</div>;
  StoryContextPanelMock.displayName = 'StoryContextPanelMock';
  return StoryContextPanelMock;
});
jest.mock('@/components/operator/CrossDomainRelationshipView', () => {
  const CrossDomainRelationshipViewMock = () => <div>CrossDomainRelationshipView</div>;
  CrossDomainRelationshipViewMock.displayName = 'CrossDomainRelationshipViewMock';
  return CrossDomainRelationshipViewMock;
});
jest.mock('@/components/operator/IssueOwnershipSlaPanel', () => {
  const IssueOwnershipSlaPanelMock = () => <div>IssueOwnershipSlaPanel</div>;
  IssueOwnershipSlaPanelMock.displayName = 'IssueOwnershipSlaPanelMock';
  return IssueOwnershipSlaPanelMock;
});
jest.mock('@/components/operator/ResponsePackPanel', () => {
  const ResponsePackPanelMock = () => <div>ResponsePackPanel</div>;
  ResponsePackPanelMock.displayName = 'ResponsePackPanelMock';
  return ResponsePackPanelMock;
});
jest.mock('@/components/ui/HealthBadge', () => {
  const HealthBadgeMock = () => <div>HealthBadge</div>;
  HealthBadgeMock.displayName = 'HealthBadgeMock';
  return HealthBadgeMock;
});

jest.mock('@/lib/api/incidents', () => ({
  getIncident: jest.fn(),
  getIncidentSocCaseState: jest.fn(),
  submitIncidentSocFeedback: jest.fn(),
  updateIncident: jest.fn(),
}));

jest.mock('@/lib/api/audit', () => ({
  getIncidentAudit: jest.fn(),
}));

jest.mock('@/lib/api/siem', () => ({
  getSourceHealth: jest.fn(),
}));

jest.mock('@/lib/api/playbooks', () => ({
  playbooksApi: {
    list: jest.fn(),
    execute: jest.fn(),
  },
}));

jest.mock('@/lib/playbooks/responsePacks', () => ({
  matchResponsePacksForIncident: jest.fn().mockReturnValue([]),
}));

jest.mock('@/lib/api/tickets', () => ({
  addTicketComment: jest.fn(),
  createTicket: jest.fn(),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/security/graph-context', () => ({
  buildIncidentGraphHref: jest.fn().mockReturnValue('/dashboard/security-graph'),
}));

const mockedGetIncident = getIncident as jest.MockedFunction<typeof getIncident>;
const mockedGetIncidentSocCaseState = getIncidentSocCaseState as jest.MockedFunction<
  typeof getIncidentSocCaseState
>;
const mockedSubmitIncidentSocFeedback = submitIncidentSocFeedback as jest.MockedFunction<
  typeof submitIncidentSocFeedback
>;
const mockedUpdateIncident = updateIncident as jest.MockedFunction<typeof updateIncident>;
const mockedGetIncidentAudit = getIncidentAudit as jest.MockedFunction<typeof getIncidentAudit>;
const mockedGetSourceHealth = getSourceHealth as jest.MockedFunction<typeof getSourceHealth>;
const mockedAddTicketComment = addTicketComment as jest.MockedFunction<typeof addTicketComment>;
const mockedCreateTicket = createTicket as jest.MockedFunction<typeof createTicket>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe('IncidentDetailPage SOC case panel', () => {
  beforeEach(() => {
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      hydrated: true,
      token: 'token-123',
      tenantId: 'tenant-123',
      planTier: 'protect',
      user: {
        id: 'user-1',
        email: 'analyst@example.com',
        roles: ['SOC_ANALYST'],
        plan_tier: 'protect',
      },
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      setPlanTierOverride: jest.fn(),
    });

    mockedGetIncident.mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      tenant_id: 'tenant-123',
      title: 'Suspicious login activity',
      severity: 'high',
      status: 'investigating',
      phase: 'Analyzing',
      description: 'Identity alert requiring operator review.',
      ticket_id: 'ticket-1',
      assigned_to: 'SOC Analyst',
      assignee: 'SOC Analyst',
      related_detections: [],
      timeline: [],
      story_domains: [],
      entities: [],
      evidence: [],
      created_at: '2026-03-30T12:00:00Z',
      updated_at: '2026-03-30T12:05:00Z',
    } as any);
    mockedGetIncidentSocCaseState.mockResolvedValue({
      tenant_id: 'tenant-123',
      incident_id: '11111111-1111-1111-1111-111111111111',
      case_id: 'case-1',
      case_context: {},
      case_memory: {},
      latest_recommendation: {
        recommendation_id: 'rec-1',
        generated_at: '2026-03-30T12:06:00Z',
        case_summary: 'The incident matches likely account takeover behavior.',
        response_pack_id: 'account_takeover',
        response_pack_label: 'Account takeover',
        recommended_playbooks: [
          {
            playbook_id: 'playbook-1',
            playbook_name: 'Investigate suspicious sign-in',
            rank: 1,
            confidence: 0.88,
            rationale: ['Correlated impossible travel and MFA challenge failures.'],
            automation_mode: 'manual_review',
          },
        ],
        recommended_actions: [
          {
            action_id: 'action-1',
            action_type: 'review_identity',
            label: 'Review identity sign-in history',
            description: 'Validate whether the identity has prior travel anomalies.',
            risk_level: 'investigative',
            requires_approval: false,
            recommended_owner_role: 'L1',
            evidence_basis: ['Impossible travel alert'],
            status: 'recommended',
          },
        ],
        missing_evidence: [],
        proposed_phase: 'Analyzing',
        proposed_status: 'investigating',
        incident_note_draft: 'AI generated incident note draft',
        ticket_update_draft: 'AI generated ticket update draft',
        timeline_event_draft: 'AI generated timeline draft',
        confidence: 0.82,
        rationale: ['Primary signal and related evidence align to account takeover.'],
      },
      recommendation_versions: [
        {
          recommendation_id: 'rec-older',
          generated_at: '2026-03-30T11:15:00Z',
          case_summary: 'Earlier recommendation version.',
          response_pack_id: 'manual_investigation',
          response_pack_label: 'Manual investigation',
          recommended_playbooks: [],
          recommended_actions: [],
          missing_evidence: ['Confirm user intent'],
          incident_note_draft: 'Older AI generated incident note draft',
          ticket_update_draft: 'Older AI generated ticket update draft',
          timeline_event_draft: 'Older AI generated timeline draft',
          confidence: 0.41,
          rationale: ['Initial evidence was incomplete.'],
          closure_checklist: [],
        },
        {
          recommendation_id: 'rec-1',
          generated_at: '2026-03-30T12:06:00Z',
          case_summary: 'The incident matches likely account takeover behavior.',
          response_pack_id: 'account_takeover',
          response_pack_label: 'Account takeover',
          recommended_playbooks: [
            {
              playbook_id: 'playbook-1',
              playbook_name: 'Investigate suspicious sign-in',
              rank: 1,
              confidence: 0.88,
              rationale: ['Correlated impossible travel and MFA challenge failures.'],
              automation_mode: 'manual_review',
            },
          ],
          recommended_actions: [
            {
              action_id: 'action-1',
              action_type: 'review_identity',
              label: 'Review identity sign-in history',
              description: 'Validate whether the identity has prior travel anomalies.',
              risk_level: 'investigative',
              requires_approval: false,
              recommended_owner_role: 'L1',
              evidence_basis: ['Impossible travel alert'],
              status: 'recommended',
            },
          ],
          missing_evidence: [],
          proposed_phase: 'Analyzing',
          proposed_status: 'investigating',
          incident_note_draft: 'AI generated incident note draft',
          ticket_update_draft: 'AI generated ticket update draft',
          timeline_event_draft: 'AI generated timeline draft',
          confidence: 0.82,
          rationale: ['Primary signal and related evidence align to account takeover.'],
          closure_checklist: [],
        },
      ],
      recent_tasks: [],
    });
    mockedSubmitIncidentSocFeedback.mockResolvedValue({
      tenant_id: 'tenant-123',
      incident_id: '11111111-1111-1111-1111-111111111111',
      case_id: 'case-1',
      case_context: {},
      case_memory: {},
      latest_recommendation: {
        recommendation_id: 'rec-1',
        generated_at: '2026-03-30T12:06:00Z',
        case_summary: 'The incident matches likely account takeover behavior.',
        response_pack_id: 'account_takeover',
        response_pack_label: 'Account takeover',
        recommended_playbooks: [
          {
            playbook_id: 'playbook-1',
            playbook_name: 'Investigate suspicious sign-in',
            rank: 1,
            confidence: 0.88,
            rationale: ['Correlated impossible travel and MFA challenge failures.'],
            automation_mode: 'manual_review',
            status: 'accepted',
          },
        ],
        recommended_actions: [
          {
            action_id: 'action-1',
            action_type: 'review_identity',
            label: 'Review identity sign-in history',
            description: 'Validate whether the identity has prior travel anomalies.',
            risk_level: 'investigative',
            requires_approval: false,
            recommended_owner_role: 'L1',
            evidence_basis: ['Impossible travel alert'],
            status: 'recommended',
          },
        ],
        missing_evidence: [],
        proposed_phase: 'Analyzing',
        proposed_status: 'investigating',
        incident_note_draft: 'AI generated incident note draft',
        ticket_update_draft: 'AI generated ticket update draft',
        timeline_event_draft: 'AI generated timeline draft',
        confidence: 0.82,
        rationale: ['Primary signal and related evidence align to account takeover.'],
      },
      recommendation_versions: [
        {
          recommendation_id: 'rec-older',
          generated_at: '2026-03-30T11:15:00Z',
          case_summary: 'Earlier recommendation version.',
          response_pack_id: 'manual_investigation',
          response_pack_label: 'Manual investigation',
          recommended_playbooks: [],
          recommended_actions: [],
          missing_evidence: ['Confirm user intent'],
          incident_note_draft: 'Older AI generated incident note draft',
          ticket_update_draft: 'Older AI generated ticket update draft',
          timeline_event_draft: 'Older AI generated timeline draft',
          confidence: 0.41,
          rationale: ['Initial evidence was incomplete.'],
          closure_checklist: [],
        },
        {
          recommendation_id: 'rec-1',
          generated_at: '2026-03-30T12:06:00Z',
          case_summary: 'The incident matches likely account takeover behavior.',
          response_pack_id: 'account_takeover',
          response_pack_label: 'Account takeover',
          recommended_playbooks: [
            {
              playbook_id: 'playbook-1',
              playbook_name: 'Investigate suspicious sign-in',
              rank: 1,
              confidence: 0.88,
              rationale: ['Correlated impossible travel and MFA challenge failures.'],
              automation_mode: 'manual_review',
              status: 'accepted',
            },
          ],
          recommended_actions: [
            {
              action_id: 'action-1',
              action_type: 'review_identity',
              label: 'Review identity sign-in history',
              description: 'Validate whether the identity has prior travel anomalies.',
              risk_level: 'investigative',
              requires_approval: false,
              recommended_owner_role: 'L1',
              evidence_basis: ['Impossible travel alert'],
              status: 'recommended',
            },
          ],
          missing_evidence: [],
          proposed_phase: 'Analyzing',
          proposed_status: 'investigating',
          incident_note_draft: 'AI generated incident note draft',
          ticket_update_draft: 'AI generated ticket update draft',
          timeline_event_draft: 'AI generated timeline draft',
          confidence: 0.82,
          rationale: ['Primary signal and related evidence align to account takeover.'],
          closure_checklist: [],
        },
      ],
      recent_tasks: [],
    });
    mockedUpdateIncident.mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      tenant_id: 'tenant-123',
      title: 'Suspicious login activity',
      severity: 'high',
      status: 'investigating',
      phase: 'Analyzing',
      description: 'Identity alert requiring operator review.',
      ticket_id: 'ticket-1',
      assigned_to: 'SOC Analyst',
      assignee: 'SOC Analyst',
      related_detections: [],
      timeline: [],
      story_domains: [],
      entities: [],
      evidence: [],
      created_at: '2026-03-30T12:00:00Z',
      updated_at: '2026-03-30T12:05:00Z',
    } as any);
    mockedGetIncidentAudit.mockResolvedValue([]);
    mockedGetSourceHealth.mockResolvedValue({
      ingestion_service: 'healthy',
      siem_agent: 'healthy',
      opensearch: 'healthy',
    } as any);
    (playbooksApi.list as jest.Mock).mockResolvedValue([]);
    (playbooksApi.execute as jest.Mock).mockResolvedValue({ execution_id: 'exec-1' });
    mockedAddTicketComment.mockResolvedValue({ id: 'ticket-1' } as any);
    mockedCreateTicket.mockResolvedValue({ id: 'ticket-1' } as any);
  });

  it('loads the AI note draft into the existing incident note composer', async () => {
    const user = userEvent.setup();

    await act(async () => {
      renderWithProviders(<IncidentDetailPage />);
    });

    expect(await screen.findByText(/SOC AI Agent/i)).toBeInTheDocument();
    expect(await screen.findByText(/The incident matches likely account takeover behavior/i)).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /use as incident note/i }));
    });

    await waitFor(() => {
      expect(
        screen.getByPlaceholderText(/Summarize investigation progress, remediation context, or the next operator handoff/i)
      ).toHaveValue('AI generated incident note draft');
    });
  });

  it('submits analyst feedback when accepting a recommended playbook', async () => {
    const user = userEvent.setup();

    await act(async () => {
      renderWithProviders(<IncidentDetailPage />);
    });

    expect(await screen.findByText(/SOC AI Agent/i)).toBeInTheDocument();

    await user.click(await screen.findByRole('button', { name: /accept playbook/i }));

    await waitFor(() => {
      expect(mockedSubmitIncidentSocFeedback).toHaveBeenCalledWith(
        '11111111-1111-1111-1111-111111111111',
        expect.objectContaining({
          recommendation_id: 'rec-1',
          feedback_type: 'accepted_recommendation',
          playbook_id: 'playbook-1',
          actor_id: 'analyst@example.com',
          actor_role: 'HUMAN_OWNER',
          accepted: true,
        })
      );
    });
  });

  it('posts the incident note, ticket update, and timeline drafts from the SOC panel', async () => {
    const user = userEvent.setup();

    await act(async () => {
      renderWithProviders(<IncidentDetailPage />);
    });

    expect(await screen.findByText(/SOC AI Agent/i)).toBeInTheDocument();
    expect(await screen.findByText(/The incident matches likely account takeover behavior/i)).toBeInTheDocument();

    await user.click(await screen.findByRole('button', { name: /post to incident/i }));
    await waitFor(() => {
      expect(mockedUpdateIncident).toHaveBeenCalledWith(
        '11111111-1111-1111-1111-111111111111',
        expect.objectContaining({ comment: 'AI generated incident note draft' })
      );
    });

    await user.click(await screen.findByRole('button', { name: /post to ticket/i }));
    await waitFor(() => {
      expect(mockedAddTicketComment).toHaveBeenCalledWith(
        'ticket-1',
        'AI generated ticket update draft',
        'tenant-123'
      );
    });

    await user.click(await screen.findByRole('button', { name: /post to timeline/i }));
    await waitFor(() => {
      expect(mockedUpdateIncident).toHaveBeenCalledWith(
        '11111111-1111-1111-1111-111111111111',
        expect.objectContaining({ timeline_event: 'AI generated timeline draft' })
      );
    });
  });
});
