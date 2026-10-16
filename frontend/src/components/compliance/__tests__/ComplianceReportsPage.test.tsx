import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ComplianceReportsPage from '../pages/ComplianceReportsPage';
import {
  getComplianceDashboard,
  getSoc2Coverage,
  listComplianceEvidencePackages,
} from '@/lib/api/compliance';
import {
  createScheduledReport,
  generateReport,
  listReports,
  listScheduledReports,
  listShares,
  listTemplates,
} from '@/lib/api/reports';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('next/dynamic', () => () => {
  function MockDynamicSection() {
    return <div data-testid="dynamic-section" />;
  }
  return MockDynamicSection;
});

jest.mock('@/components/PlanGate', () => ({
  PlanGate: ({ children }: { children: any }) => <>{children}</>,
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: () => ({
    user: {
      id: 'user-1',
      email: 'owner@example.com',
      roles: ['compliance_manager'],
    },
  }),
}));

jest.mock('@/lib/compliance/features', () => ({
  getComplianceRuntimeLabels: () => ({
    reportsTitle: 'Compliance Reports',
    reportsDescription: 'Generate compliance exports from selected frameworks.',
    evidenceMetricLabel: 'Evidence items',
    evidenceMetricDescription: 'Reviewed objects available for audit packets',
  }),
}));

jest.mock('react-hot-toast', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('@/lib/api/compliance', () => ({
  getComplianceDashboard: jest.fn(),
  getSoc2Coverage: jest.fn(),
  listComplianceEvidencePackages: jest.fn(),
}));

jest.mock('@/lib/api/reports', () => ({
  createScheduledReport: jest.fn(),
  createShare: jest.fn(),
  deleteShare: jest.fn(),
  generateReport: jest.fn(),
  getReportDownload: jest.fn(),
  listReports: jest.fn(),
  listScheduledReports: jest.fn(),
  listShares: jest.fn(),
  listTemplates: jest.fn(),
}));

const mockedGetDashboard = getComplianceDashboard as jest.MockedFunction<typeof getComplianceDashboard>;
const mockedGetCoverage = getSoc2Coverage as jest.MockedFunction<typeof getSoc2Coverage>;
const mockedListPackages = listComplianceEvidencePackages as jest.MockedFunction<typeof listComplianceEvidencePackages>;
const mockedCreateSchedule = createScheduledReport as jest.MockedFunction<typeof createScheduledReport>;
const mockedGenerateReport = generateReport as jest.MockedFunction<typeof generateReport>;
const mockedListReports = listReports as jest.MockedFunction<typeof listReports>;
const mockedListSchedules = listScheduledReports as jest.MockedFunction<typeof listScheduledReports>;
const mockedListShares = listShares as jest.MockedFunction<typeof listShares>;
const mockedListTemplates = listTemplates as jest.MockedFunction<typeof listTemplates>;

const template = {
  id: 'tpl-soc2',
  tenant_id: null,
  name: 'SOC 2 Evidence Summary',
  description: 'Evidence-backed SOC 2 report',
  type: 'soc2',
  sections: [],
  data_queries: [],
  required_roles: ['compliance_manager'],
  created_at: '2026-04-27T00:00:00Z',
  updated_at: '2026-04-27T00:00:00Z',
} as const;

const generatedReport = {
  id: 'report-1',
  tenant_id: 'tenant-123',
  template_id: 'tpl-soc2',
  name: 'SOC 2 Evidence Summary - 2026-04-27',
  format: 'PDF',
  status: 'PENDING',
  generated_at: '2026-04-27T12:00:00Z',
  generated_by: 'user-1',
  date_range_start: '2026-01-27T00:00:00Z',
  date_range_end: '2026-04-27T00:00:00Z',
  download_url: undefined,
  sections: [],
  metadata: {
    template_name: 'SOC 2 Evidence Summary',
    template_key: 'soc_2_evidence_summary',
    report_inputs: {
      framework_ids: ['soc2'],
      control_ids: [],
      evidence_package_ids: ['pkg-1'],
      include_gaps: true,
      include_expired_evidence: false,
      date_range: {
        start: '2026-01-27',
        end: '2026-04-27',
      },
    },
    compliance_snapshot: {
      status: 'pending',
    },
  },
  created_at: '2026-04-27T12:00:00Z',
  updated_at: '2026-04-27T12:00:00Z',
} as const;

describe('ComplianceReportsPage', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockedGetCoverage.mockResolvedValue({
      summary: {
        tenant_id: 'tenant-123',
        total_criteria: 2,
        open_criteria: 1,
        total_findings: 1,
        open_findings: 1,
        status: 'partial',
        mapped_detections: 2,
        control_checks: 1,
        playbooks: 0,
        automated_responses: 0,
        evidence_items: 3,
      },
      controls: [],
      status: 'partial',
      reporting_summary: {
        criteria_ready: 1,
        criteria_partial: 1,
        criteria_needing_attention: 1,
        criteria_not_assessed: 0,
        key_detection_count: 2,
        control_check_count: 1,
        playbook_count: 0,
        playbook_execution_count: 0,
        reportable_evidence_items: 3,
        top_detection_sources: [],
      },
      key_detections: [],
      control_checks: [],
      overall_score: 65,
    } as any);
    mockedGetDashboard.mockResolvedValue({
      framework_coverage: {
        tenant_id: 'tenant-123',
        count: 1,
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
            status: 'partially_supported',
            status_counts: { accepted: 1, needs_evidence: 1 },
            average_confidence: 0.65,
            control_count: 2,
            returned_control_count: 2,
            limit: 50,
            offset: 0,
            generated_at: '2026-04-27T00:00:00Z',
            controls: [],
          },
        ],
      },
    } as any);
    mockedListTemplates.mockResolvedValue([template] as any);
    mockedListReports.mockResolvedValue([]);
    mockedListShares.mockResolvedValue([]);
    mockedListSchedules.mockResolvedValue([]);
    mockedListPackages.mockResolvedValue({
      tenant_id: 'tenant-123',
      count: 1,
      limit: 50,
      offset: 0,
      items: [
        {
          id: 'pkg-1',
          tenant_id: 'tenant-123',
          package_name: 'SOC 2 Q2 Evidence',
          package_type: 'audit',
          framework_id: 'soc2',
          report_period_start: '2026-04-01',
          report_period_end: '2026-06-30',
          status: 'collecting',
          review_status: 'ready_for_review',
          evidence_item_count: 2,
        },
      ],
    } as any);
    mockedGenerateReport.mockResolvedValue(generatedReport as any);
    mockedCreateSchedule.mockResolvedValue({ job_id: 'job-1', message: 'Scheduled report created successfully' });
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('generates a framework-scoped evidence-backed report', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceReportsPage />);

    await screen.findByText(/SOC 2 Trust Services Criteria/i);
    await user.click(await screen.findByLabelText(/SOC 2 Q2 Evidence/i));
    await user.click(screen.getByRole('button', { name: /Generate selected report/i }));

    await waitFor(() => {
      expect(mockedGenerateReport).toHaveBeenCalledWith(
        expect.objectContaining({
          template_id: 'tpl-soc2',
          format: 'pdf',
          framework_ids: ['soc2'],
          evidence_package_ids: ['pkg-1'],
          include_gaps: true,
          include_expired_evidence: false,
          parameters: { evidence_basis: 'evidence_backed' },
        })
      );
    });
    expect(await screen.findByText(/Report snapshot/i)).toBeTruthy();
    expect(screen.getAllByText(/Evidence-backed/i).length).toBeGreaterThan(0);
  });

  it('creates a schedule for a supported compliance template', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceReportsPage />);

    await screen.findByText(/Schedule report/i);
    await user.type(screen.getByLabelText(/Recipients/i), 'compliance@example.com');
    await user.click(screen.getByRole('button', { name: /Create schedule/i }));

    await waitFor(() => {
      expect(mockedCreateSchedule).toHaveBeenCalledWith('tpl-soc2', {
        frequency: 'monthly',
        day: '1',
        time: '09:00',
        recipients: ['compliance@example.com'],
        enabled: true,
      });
    });
  });
});
