import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FrameworkSelectionPanel } from '../FrameworkSelectionPanel';
import {
  getComplianceFrameworkSelections,
  updateComplianceFrameworkSelections,
} from '@/lib/api/compliance';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/compliance', () => ({
  getComplianceFrameworkSelections: jest.fn(),
  updateComplianceFrameworkSelections: jest.fn(),
}));

const mockedGetSelections = getComplianceFrameworkSelections as jest.MockedFunction<
  typeof getComplianceFrameworkSelections
>;
const mockedUpdateSelections = updateComplianceFrameworkSelections as jest.MockedFunction<
  typeof updateComplianceFrameworkSelections
>;

const selectionsPayload = {
  tenant_id: 'tenant-123',
  items: [
    {
      framework_id: 'soc2',
      framework_code: 'SOC2',
      framework_name: 'SOC 2 Trust Services Criteria',
      runtime_support: 'readiness',
      control_count: 10,
      status: 'active',
      priority: 1,
      target_date: null,
      selected_by: 'onboarding_trust_profile',
      selected_at: '2026-04-27T00:00:00Z',
      updated_at: '2026-04-27T00:00:00Z',
      source: 'onboarding_trust_profile',
    },
  ],
  count: 1,
  available_frameworks: [
    {
      framework_id: 'soc2',
      framework_code: 'SOC2',
      framework_name: 'SOC 2 Trust Services Criteria',
      runtime_support: 'readiness',
      control_count: 10,
      description: 'SOC 2 readiness reporting.',
    },
    {
      framework_id: 'hipaa',
      framework_code: 'HIPAA',
      framework_name: 'HIPAA Security Rule',
      runtime_support: 'catalog',
      control_count: 8,
      description: 'HIPAA catalog data.',
    },
  ],
  source: 'tenant_framework_selections',
} as const;

describe('FrameworkSelectionPanel', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockedGetSelections.mockResolvedValue(selectionsPayload as any);
    mockedUpdateSelections.mockResolvedValue({
      ...selectionsPayload,
      items: [
        ...selectionsPayload.items,
        {
          framework_id: 'hipaa',
          framework_code: 'HIPAA',
          framework_name: 'HIPAA Security Rule',
          runtime_support: 'catalog',
          control_count: 8,
          status: 'evaluating',
          priority: 2,
          target_date: null,
          selected_by: 'user-1',
          selected_at: '2026-04-27T00:00:00Z',
          updated_at: '2026-04-27T00:00:00Z',
          source: 'manual',
        },
      ],
      count: 2,
    } as any);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('renders current selections read-only when editing is disabled', async () => {
    renderWithProviders(<FrameworkSelectionPanel editable={false} />);

    expect(await screen.findByText(/Selected Frameworks/i)).toBeInTheDocument();
    expect(screen.getByText(/picker disabled/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/Select SOC 2 Trust Services Criteria/i)).toBeDisabled();
    expect(screen.getByRole('button', { name: /Save framework scope/i })).toBeDisabled();
    expect(screen.getByText(/readiness live/i)).toBeInTheDocument();
    expect(screen.getByText(/catalog ready/i)).toBeInTheDocument();
  });

  it('saves selected frameworks when editing is enabled', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FrameworkSelectionPanel editable />);

    await screen.findByText(/Selected Frameworks/i);
    await user.click(await screen.findByLabelText(/Select HIPAA Security Rule/i));
    await user.click(screen.getByRole('button', { name: /Save framework scope/i }));

    await waitFor(() => {
      expect(mockedUpdateSelections).toHaveBeenCalledWith({
        selections: [
          {
            framework_id: 'soc2',
            status: 'active',
            priority: 1,
            target_date: null,
          },
          {
            framework_id: 'hipaa',
            status: 'evaluating',
            priority: 2,
            target_date: null,
          },
        ],
      });
    });
    await waitFor(() => {
      expect(screen.getByText(/2 selected/i)).toBeInTheDocument();
    });
  });
});
