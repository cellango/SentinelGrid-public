import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { ComplianceAgentWorkbenchPanel } from '../ComplianceAgentWorkbenchPanel';
import {
  decideComplianceAgentRecommendation,
  listComplianceAgentRecommendations,
} from '@/lib/api/compliance';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/compliance', () => ({
  listComplianceAgentRecommendations: jest.fn(),
  decideComplianceAgentRecommendation: jest.fn(),
}));

const mockedListRecommendations = listComplianceAgentRecommendations as jest.MockedFunction<
  typeof listComplianceAgentRecommendations
>;
const mockedDecideRecommendation = decideComplianceAgentRecommendation as jest.MockedFunction<
  typeof decideComplianceAgentRecommendation
>;

const recommendationPayload = {
  tenant_id: 'tenant-123',
  items: [
    {
      id: 'rec-evidence',
      tenant_id: 'tenant-123',
      trigger_type: 'evidence_expiring',
      recommendation_type: 'create_evidence_collection_task',
      state: 'proposed',
      priority: 'high',
      source_type: 'evidence',
      source_id: 'ev-1',
      framework_id: 'soc2',
      control_id: 'CC6.1',
      evidence_item_id: 'ev-1',
      evidence_package_id: null,
      report_id: null,
      title: 'Refresh expiring MFA evidence',
      summary: 'Evidence expires soon and needs replacement before the next report.',
      proposed_actions: [
        {
          action: 'create_evidence_collection_task',
          tool: 'create_evidence_collection_task',
          requires_approval: true,
          arguments: { task_name: 'Refresh MFA configuration export' },
        },
      ],
      requires_approval: true,
      created_at: '2026-04-27T10:00:00Z',
      updated_at: '2026-04-27T10:00:00Z',
      metadata: {},
    },
    {
      id: 'rec-gap',
      tenant_id: 'tenant-123',
      trigger_type: 'high_priority_control_gap_detected',
      recommendation_type: 'create_evidence_collection_task',
      state: 'proposed',
      priority: 'critical',
      source_type: 'control_gap',
      source_id: 'gap-1',
      framework_id: 'soc2',
      control_id: 'CC7.2',
      evidence_item_id: null,
      evidence_package_id: null,
      report_id: null,
      title: 'Close high-priority control gap CC7.2',
      summary: 'Endpoint monitoring evidence is missing.',
      proposed_actions: [
        {
          action: 'create_evidence_collection_task',
          requires_approval: true,
          arguments: { task_name: 'Collect endpoint monitoring evidence' },
        },
      ],
      requires_approval: true,
      created_at: '2026-04-27T11:00:00Z',
      updated_at: '2026-04-27T11:00:00Z',
      metadata: {},
    },
    {
      id: 'rec-report',
      tenant_id: 'tenant-123',
      trigger_type: 'report_generation_requested',
      recommendation_type: 'read_only_summary',
      state: 'proposed',
      priority: 'medium',
      source_type: 'report',
      source_id: 'report-1',
      framework_id: 'soc2',
      control_id: null,
      evidence_item_id: null,
      evidence_package_id: null,
      report_id: 'report-1',
      title: 'Review generated compliance report inputs',
      summary: 'Verify selected frameworks and evidence packages.',
      proposed_actions: [
        {
          action: 'summarize_report_inputs',
          requires_approval: false,
          arguments: {},
        },
      ],
      requires_approval: false,
      created_at: '2026-04-27T12:00:00Z',
      updated_at: '2026-04-27T12:00:00Z',
      metadata: {},
    },
  ],
  count: 3,
  limit: 50,
  offset: 0,
} as const;

describe('ComplianceAgentWorkbenchPanel', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockedListRecommendations.mockResolvedValue(recommendationPayload as any);
    mockedDecideRecommendation.mockResolvedValue({
      ...recommendationPayload.items[0],
      state: 'accepted',
      decided_by: 'user-1',
      decided_at: '2026-04-27T12:30:00Z',
    } as any);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    jest.clearAllMocks();
  });

  it('renders proposed recommendations with source links and category filters', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceAgentWorkbenchPanel />);

    expect(await screen.findByText(/Compliance Agent Workbench/i)).toBeTruthy();
    expect(await screen.findByText(/Refresh expiring MFA evidence/i)).toBeTruthy();
    expect(screen.getByText(/Close high-priority control gap CC7.2/i)).toBeTruthy();
    expect(screen.getByText(/Review generated compliance report inputs/i)).toBeTruthy();

    expect(screen.getByRole('link', { name: /Open evidence/i }).getAttribute('href')).toBe(
      '/dashboard/compliance/evidence?evidence_id=ev-1'
    );
    expect(screen.getByRole('link', { name: /Open control/i }).getAttribute('href')).toBe(
      '/dashboard/compliance?control=CC7.2'
    );
    expect(screen.getByRole('link', { name: /Open report/i }).getAttribute('href')).toBe(
      '/dashboard/compliance/reports?report_id=report-1'
    );

    await user.click(screen.getByRole('tab', { name: /Report drafts/i }));

    expect(screen.getByText(/Review generated compliance report inputs/i)).toBeTruthy();
    expect(screen.queryByText(/Refresh expiring MFA evidence/i)).toBeNull();
    expect(screen.queryByText(/Close high-priority control gap CC7.2/i)).toBeNull();
  });

  it('records approve and reject decisions through the compliance API', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceAgentWorkbenchPanel />);

    await screen.findByText(/Refresh expiring MFA evidence/i);
    await user.click(screen.getAllByRole('button', { name: /Approve/i })[0]);

    await waitFor(() => {
      expect(mockedDecideRecommendation).toHaveBeenCalledWith('rec-evidence', {
        state: 'accepted',
        decision_notes: 'Approved from the Compliance Agent workbench.',
      });
    });

    await user.click(screen.getAllByRole('button', { name: /Reject/i })[1]);

    await waitFor(() => {
      expect(mockedDecideRecommendation).toHaveBeenCalledWith('rec-gap', {
        state: 'rejected',
        decision_notes: 'Rejected from the Compliance Agent workbench.',
      });
    });
  });
});
