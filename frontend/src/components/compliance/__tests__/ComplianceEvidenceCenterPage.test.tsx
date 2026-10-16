import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';

import ComplianceEvidenceCenterPage from '../pages/ComplianceEvidenceCenterPage';
import {
  listComplianceEvidence,
  listComplianceEvidenceCollectionTasks,
  listComplianceEvidencePackages,
  exportComplianceEvidencePackage,
} from '@/lib/api/compliance';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/components/PlanGate', () => ({
  PlanGate: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

jest.mock('@/components/ui/SlideOverPanel', () => ({
  __esModule: true,
  default: ({ open, title, children }: { open: boolean; title: string; children: ReactNode }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        {children}
      </div>
    ) : null,
}));

jest.mock('@/lib/api/compliance', () => ({
  createComplianceEvidence: jest.fn(),
  createComplianceEvidencePackage: jest.fn(),
  exportComplianceEvidencePackage: jest.fn(),
  getComplianceEvidence: jest.fn(),
  getComplianceEvidencePackage: jest.fn(),
  listComplianceEvidence: jest.fn(),
  listComplianceEvidenceCollectionTasks: jest.fn(),
  listComplianceEvidencePackages: jest.fn(),
  reviewComplianceEvidence: jest.fn(),
}));

const mockedListEvidence = listComplianceEvidence as jest.MockedFunction<typeof listComplianceEvidence>;
const mockedListTasks = listComplianceEvidenceCollectionTasks as jest.MockedFunction<
  typeof listComplianceEvidenceCollectionTasks
>;
const mockedListPackages = listComplianceEvidencePackages as jest.MockedFunction<typeof listComplianceEvidencePackages>;
const mockedExportPackage = exportComplianceEvidencePackage as jest.MockedFunction<typeof exportComplianceEvidencePackage>;

const evidenceItem = {
  id: 'evidence-1',
  tenant_id: 'tenant-1',
  evidence_type: 'configuration',
  title: 'MFA configuration export',
  description: 'MFA policy export.',
  source_system: 'iam_agent',
  source_resource_id: 'tenant-mfa-settings',
  collector: 'iam_agent',
  collection_method: 'api',
  collected_at: '2026-04-27T12:00:00Z',
  valid_from: '2026-04-01T00:00:00Z',
  valid_until: '2026-07-01T00:00:00Z',
  hash_sha256: 'a'.repeat(64),
  storage_uri: 's3://evidence/tenant/mfa.json',
  summary: 'MFA is enforced for privileged users.',
  sensitivity: 'internal',
  review_status: 'ready_for_review',
  control_links: [{ control_id: 'CC6.1', framework_id: 'soc2', link_type: 'supports' }],
} as const;

const expiringEvidenceItem = {
  ...evidenceItem,
  id: 'evidence-2',
  title: 'Quarterly access review attestation',
  valid_until: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
};

describe('ComplianceEvidenceCenterPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockedListEvidence.mockImplementation((params) => {
      if (params?.expires_before) {
        return Promise.resolve({
          tenant_id: 'tenant-1',
          items: [expiringEvidenceItem as any],
          count: 1,
          limit: 50,
          offset: 0,
        });
      }
      return Promise.resolve({
        tenant_id: 'tenant-1',
        items: [evidenceItem as any],
        count: 1,
        limit: 100,
        offset: 0,
      });
    });
    mockedListTasks.mockResolvedValue({
      tenant_id: 'tenant-1',
      items: [
        {
          id: 'task-1',
          tenant_id: 'tenant-1',
          task_name: 'Collect IAM IA-2 MFA evidence',
          task_type: 'configuration',
          status: 'manual_evidence_required',
          source_system: 'iam_agent',
          source_resource_id: 'iam:IA-2:configuration:mfa',
          collector: 'iam_agent',
          collection_method: 'manual_attestation',
          requested_by: 'iam_agent',
          metadata: {
            nist_control_id: 'IA-2',
            control_links: [{ control_id: 'CC6.1', framework_id: 'soc2' }],
          },
        },
      ],
      count: 1,
      limit: 100,
      offset: 0,
    } as any);
    mockedListPackages.mockResolvedValue({
      tenant_id: 'tenant-1',
      items: [
        {
          id: 'package-1',
          tenant_id: 'tenant-1',
          package_name: 'SOC 2 Q2 Evidence',
          framework_id: 'soc2',
          report_period_start: '2026-04-01',
          report_period_end: '2026-06-30',
          status: 'collecting',
          review_status: 'pending',
          evidence_item_count: 1,
        },
      ],
      count: 1,
      limit: 50,
      offset: 0,
    } as any);
    mockedExportPackage.mockResolvedValue({
      id: 'export-1',
      tenant_id: 'tenant-1',
      package_id: 'package-1',
      export_format: 'csv',
      status: 'requested',
      requested_by: 'user-1',
      requested_at: '2026-04-27T12:00:00Z',
      include_sensitive: false,
    } as any);
  });

  it('shows evidence lifecycle queues from repository APIs', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceEvidenceCenterPage />);

    expect(await screen.findByRole('heading', { name: /Evidence Center/i })).toBeInTheDocument();
    expect(await screen.findByText('MFA configuration export')).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /Collection tasks/i }));
    });
    expect(await screen.findByText('Collect IAM IA-2 MFA evidence')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add attestation/i })).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /Review queue/i }));
    });
    expect(await screen.findByText(/MFA is enforced for privileged users/i)).toBeInTheDocument();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /Packages/i }));
    });
    expect(await screen.findByText('SOC 2 Q2 Evidence')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /CSV/i })).toBeInTheDocument();
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /CSV/i }));
    });
    await waitFor(() => {
      expect(mockedExportPackage).toHaveBeenCalledWith(
        'package-1',
        expect.objectContaining({ export_format: 'csv' })
      );
    });
  });

  it('opens the manual attestation flow', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ComplianceEvidenceCenterPage />);

    await screen.findByText('MFA configuration export');
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /Manual attestation/i }));
    });

    expect(screen.getByRole('dialog', { name: /Manual Attestation/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Control/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Evidence URL or storage URI/i)).toBeInTheDocument();
  });
});
