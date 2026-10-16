import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import DashboardHeader from '../DashboardHeader';
import { getOnboardingStatus } from '@/lib/api/onboarding';
import { playbooksApi } from '@/lib/api/playbooks';
import { openCommandPalette } from '@/lib/command-palette';
import { useAuth } from '@/lib/providers/AuthProvider';
import { usePartnerTenantContext } from '@/lib/partner/tenantContext';
import { useTheme } from '@/lib/providers/ThemeProvider';

const { getMockRouter, mockPathname } = require('@/test-utils/navigation');

jest.mock('@/lib/api/onboarding', () => ({
  getOnboardingStatus: jest.fn(),
}));

jest.mock('@/lib/api/playbooks', () => ({
  playbooksApi: {
    listExecutions: jest.fn(),
  },
}));

jest.mock('@/lib/command-palette', () => ({
  OPEN_COMMAND_PALETTE_EVENT: 'sentinelgrid:open-command-palette',
  openCommandPalette: jest.fn(),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/partner/tenantContext', () => ({
  usePartnerTenantContext: jest.fn(),
}));

jest.mock('@/lib/providers/ThemeProvider', () => ({
  useTheme: jest.fn(),
}));

const mockedGetOnboardingStatus = getOnboardingStatus as jest.MockedFunction<
  typeof getOnboardingStatus
>;
const mockedListExecutions = playbooksApi.listExecutions as jest.MockedFunction<
  typeof playbooksApi.listExecutions
>;
const mockedOpenCommandPalette = openCommandPalette as jest.MockedFunction<
  typeof openCommandPalette
>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockedUsePartnerTenantContext = usePartnerTenantContext as jest.MockedFunction<
  typeof usePartnerTenantContext
>;
const mockedUseTheme = useTheme as jest.MockedFunction<typeof useTheme>;

describe('DashboardHeader', () => {
  beforeEach(() => {
    getMockRouter().push.mockReset();
    mockPathname('/dashboard/incidents');
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
    mockedUsePartnerTenantContext.mockReturnValue({
      activeTenant: null,
      effectiveTenantId: 'tenant-123',
      homeTenantId: null,
      isInPartnerTenantContext: false,
      enterTenantContext: jest.fn(),
      clearTenantContext: jest.fn(),
    });
    mockedUseTheme.mockReturnValue({
      theme: 'dark',
      toggleTheme: jest.fn(),
    } as any);
    mockedGetOnboardingStatus.mockResolvedValue({
      steps: [
        { id: 'idp', done: true },
        { id: 'cloud', done: false },
      ],
    } as any);
    mockedListExecutions.mockResolvedValue([]);
  });

  it('renders route-specific metadata and opens the command palette from search', async () => {
    const user = userEvent.setup();
    render(<DashboardHeader onMobileMenuToggle={jest.fn()} />);

    expect(await screen.findByText(/Incident Queue/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Monitor active cases, assignees, and escalations without leaving the main queue\./i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Open universal search/i }));

    expect(mockedOpenCommandPalette).toHaveBeenCalledWith({ source: 'header-search' });
  });

  it('shows partner tenant context controls and exits back to the main queue', async () => {
    const clearTenantContext = jest.fn();
    const user = userEvent.setup();

    mockedUsePartnerTenantContext.mockReturnValue({
      activeTenant: {
        tenantName: 'Acme Health',
        deliveryMode: 'managed_detection',
        approvalMode: 'customer_approves',
        enteredAt: '2026-03-28T12:00:00.000Z',
      },
      effectiveTenantId: 'tenant-456',
      homeTenantId: 'partner-home',
      isInPartnerTenantContext: true,
      enterTenantContext: jest.fn(),
      clearTenantContext,
    } as any);

    render(<DashboardHeader onMobileMenuToggle={jest.fn()} />);

    expect(await screen.findByText(/Managed Tenant Context Active/i)).toBeInTheDocument();
    expect(screen.getByText(/Acme Health is the active client scope for this session\./i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Exit Tenant Context/i }));

    expect(clearTenantContext).toHaveBeenCalled();
    expect(getMockRouter().push).toHaveBeenCalledWith('/dashboard/now');
  });

  it('loads the pending approvals count from playbook executions', async () => {
    mockedListExecutions.mockResolvedValue([
      { id: 'exec-1', status: 'pending', approval_status: 'pending' },
      { id: 'exec-2', status: 'pending', approval_status: 'pending' },
    ] as any);

    render(<DashboardHeader onMobileMenuToggle={jest.fn()} />);

    await waitFor(() => {
      expect(mockedListExecutions).toHaveBeenCalledWith({
        status: 'pending',
        approval_status: 'pending',
        limit: 25,
      });
    });

    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
