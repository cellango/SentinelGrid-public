import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ComplianceDashboardPage from '../pages/ComplianceDashboardPage';
import { getComplianceDashboard } from '@/lib/api/compliance';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('next/dynamic', () => () => {
  function MockDynamicComponent() {
    return <div data-testid="soc2-heatmap">SOC 2 heatmap</div>;
  }
  return MockDynamicComponent;
});

jest.mock('@/components/PlanGate', () => ({
  PlanGate: ({ children }: { children: any }) => <>{children}</>,
}));

jest.mock('@/components/compliance/FrameworkSelectionPanel', () => ({
  FrameworkSelectionPanel: () => <div>Selected Frameworks panel</div>,
}));

jest.mock('@/components/compliance/FrameworkStarterPacksPanel', () => ({
  FrameworkStarterPacksPanel: () => <div>Framework Starter Packs</div>,
}));

jest.mock('@/components/compliance/ComplianceAgentWorkbenchPanel', () => ({
  ComplianceAgentWorkbenchPanel: () => <div>Compliance Agent Workbench</div>,
}));

jest.mock('@/components/compliance/ComplianceWorkflowPanel', () => ({
  ComplianceWorkflowPanel: () => <div>SOC 2 workflow panel</div>,
}));

jest.mock('@/components/ui/SlideOverPanel', () => ({
  __esModule: true,
  default: ({ children }: { children: any }) => <div>{children}</div>,
}));

jest.mock('@/lib/compliance/features', () => ({
  complianceFeatureFlags: {
    multiFramework: true,
    evidenceRepository: true,
    complianceAgent: true,
  },
  getComplianceRuntimeLabels: () => ({
    dashboardTitle: 'Compliance Dashboard',
    dashboardDescription: 'Track selected frameworks, evidence, and report readiness from live security signals.',
    reportsTitle: 'Compliance Reports',
    reportsDescription: 'Generate compliance exports from selected frameworks.',
    evidenceMetricLabel: 'Evidence items',
    evidenceMetricDescription: 'Reviewed objects available for audit packets',
  }),
}));

jest.mock('@/lib/api/compliance', () => ({
  getComplianceDashboard: jest.fn(),
}));

const mockedGetDashboard = getComplianceDashboard as jest.MockedFunction<typeof getComplianceDashboard>;

const dashboardPayload = {
  overall_stats: {
    overall_score: 72,
    controls_implemented: 1,
    total_controls: 2,
    evidence_items: 4,
    last_assessment: '2026-04-27T10:00:00Z',
    mapped_detections: 3,
    control_checks: 2,
  },
  soc2: {
    summary: {
      tenant_id: 'tenant-123',
      total_criteria: 2,
      open_criteria: 1,
      total_findings: 2,
      open_findings: 1,
      status: 'partial',
      mapped_detections: 3,
      control_checks: 2,
      playbooks: 1,
      automated_responses: 1,
      evidence_items: 4,
      last_assessment: '2026-04-27T10:00:00Z',
    },
    controls: [
      {
        id: 'CC1.1',
        title: 'Control environment oversight',
        description: 'Board oversight is tracked.',
        status: 'compliant',
        open_findings: 0,
        total_findings: 0,
        detection_count: 1,
        control_check_count: 1,
        playbook_count: 1,
        playbook_execution_count: 1,
        evidence_items: 2,
        mapped_nist_controls: ['AC-1'],
        key_detections: [],
        control_checks: [],
        supporting_playbooks: [],
        last_activity: '2026-04-27T10:00:00Z',
      },
    ],
    status: 'partial',
    reporting_summary: {
      criteria_ready: 1,
      criteria_partial: 1,
      criteria_needing_attention: 1,
      criteria_not_assessed: 0,
      key_detection_count: 3,
      control_check_count: 2,
      playbook_count: 1,
      playbook_execution_count: 1,
      reportable_evidence_items: 4,
      top_detection_sources: [],
    },
    key_detections: [],
    control_checks: [],
    overall_score: 72,
  },
  reporting_summary: {
    criteria_ready: 1,
    criteria_partial: 1,
    criteria_needing_attention: 1,
    criteria_not_assessed: 0,
    key_detection_count: 3,
    control_check_count: 2,
    playbook_count: 1,
    playbook_execution_count: 1,
    reportable_evidence_items: 4,
    top_detection_sources: [],
  },
  priority_criteria: [
    {
      id: 'CC1.1',
      title: 'Control environment oversight',
      description: 'Board oversight is tracked.',
      status: 'compliant',
      open_findings: 0,
      total_findings: 0,
      detection_count: 1,
      control_check_count: 1,
      playbook_count: 1,
      playbook_execution_count: 1,
      evidence_items: 2,
      mapped_nist_controls: ['AC-1'],
      key_detections: [],
      control_checks: [],
      supporting_playbooks: [],
      last_activity: '2026-04-27T10:00:00Z',
    },
  ],
  key_detections: [],
  control_checks: [],
  framework_starter_packs: [
    {
      framework_key: 'soc2',
      framework_name: 'SOC 2',
      launch_state: 'live',
      score_label: 'Readiness score',
      score: 72,
      summary: 'Starter pack summary',
      note: 'Starter pack note',
      metrics: {
        criteria_ready: 1,
        criteria_needing_attention: 1,
        mapped_signals: 3,
        evidence_items: 4,
      },
      artifact_template_keys: [],
      focus_areas: [],
      quick_actions: [],
    },
  ],
  framework_coverage: {
    tenant_id: 'tenant-123',
    count: 2,
    limit: 50,
    offset: 0,
    source: 'generalized_coverage_engine',
    items: [
      {
        tenant_id: 'tenant-123',
        framework_id: 'soc2',
        framework_code: 'SOC2',
        framework_name: 'SOC 2 Trust Services Criteria',
        runtime_support: 'readiness',
        selection_status: 'active',
        selection_source: 'manual',
        status: 'partially_supported',
        status_counts: {
          accepted: 1,
          needs_evidence: 1,
        },
        average_confidence: 0.72,
        control_count: 2,
        returned_control_count: 2,
        limit: 50,
        offset: 0,
        generated_at: '2026-04-27T10:00:00Z',
        controls: [
          {
            id: 'CC1.1',
            framework_id: 'soc2',
            control_id: 'CC1.1',
            title: 'Control environment oversight',
            description: 'Board oversight is tracked.',
            status: 'accepted',
            severity: 'low',
            confidence: 0.86,
            signals: [{ id: 'signal-1' }],
            gaps: [],
            evidence_requirements: [{ id: 'evidence-1' }],
            last_activity: '2026-04-27T10:00:00Z',
            trace: [],
            metadata: {},
          },
          {
            id: 'CC6.1',
            framework_id: 'soc2',
            control_id: 'CC6.1',
            title: 'Logical access enforcement',
            description: 'Access enforcement requires more evidence.',
            status: 'needs_evidence',
            severity: 'high',
            confidence: 0.42,
            signals: [],
            gaps: [{ title: 'Attach access review evidence' }],
            evidence_requirements: [{ id: 'evidence-2' }],
            last_activity: null,
            trace: [],
            metadata: {},
          },
        ],
      },
      {
        tenant_id: 'tenant-123',
        framework_id: 'hipaa',
        framework_code: 'HIPAA',
        framework_name: 'HIPAA Security Rule',
        runtime_support: 'catalog',
        selection_status: 'evaluating',
        selection_source: 'manual',
        status: 'not_started',
        status_counts: {
          not_started: 1,
        },
        average_confidence: 0,
        control_count: 1,
        returned_control_count: 1,
        limit: 50,
        offset: 0,
        generated_at: '2026-04-27T10:00:00Z',
        controls: [
          {
            id: '164.308(a)(1)',
            framework_id: 'hipaa',
            control_id: '164.308(a)(1)',
            title: 'Security management process',
            description: 'Implement policies and procedures to prevent, detect, contain, and correct security violations.',
            status: 'not_started',
            severity: null,
            confidence: 0,
            signals: [],
            gaps: [{ title: 'Assign HIPAA security owner' }],
            evidence_requirements: [{ id: 'policy-evidence' }, { id: 'risk-analysis' }],
            last_activity: null,
            trace: [],
            metadata: {},
          },
        ],
      },
    ],
  },
  selected_frameworks: [],
} as const;

describe('ComplianceDashboardPage', () => {
  beforeEach(() => {
    mockedGetDashboard.mockResolvedValue(dashboardPayload as any);
  });

  it('shows framework-scoped status first and removes starter packs from primary status', async () => {
    renderWithProviders(<ComplianceDashboardPage />);

    expect(await screen.findByRole('heading', { name: /Selected framework status/i })).toBeTruthy();
    expect(await screen.findByRole('tab', { name: /SOC 2 Trust Services Criteria/i })).toBeTruthy();
    expect(screen.getByRole('tab', { name: /HIPAA Security Rule/i })).toBeTruthy();
    expect(screen.getAllByText(/Evidence freshness/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Report readiness/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/SOC 2 Criteria Heatmap/i)).toBeTruthy();
    expect(screen.queryByText(/Framework Starter Packs/i)).toBeNull();
  });

  it('switches dashboard details by selected framework tab', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceDashboardPage />);

    const hipaaTab = await screen.findByRole('tab', { name: /HIPAA Security Rule/i });
    await act(async () => {
      await user.click(hipaaTab);
    });

    await waitFor(() => {
      expect(hipaaTab.getAttribute('aria-selected')).toBe('true');
    });
    expect(screen.getByRole('heading', { name: /HIPAA Security Rule Report Readiness/i })).toBeTruthy();
    expect(screen.getByText(/Selected Framework Controls/i)).toBeTruthy();
    expect(screen.getAllByText(/164\.308\(a\)\(1\)/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/SOC 2 Priority Criteria/i)).toBeNull();
    expect(screen.queryByText(/SOC 2 Criteria Heatmap/i)).toBeNull();
  });
});
