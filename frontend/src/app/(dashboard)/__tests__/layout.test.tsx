import { render, screen, waitFor } from '@testing-library/react';

import DashboardLayout from '../layout';
import { useAuth } from '@/lib/providers/AuthProvider';
import { usePartnerTenantContext } from '@/lib/partner/tenantContext';

const { getMockRouter } = require('@/test-utils/navigation');

jest.mock('next/dynamic', () => () => {
  return function MockDynamicComponent(props: { tenantId?: string }) {
    return <div data-testid="command-palette">Command Palette {props.tenantId}</div>;
  };
});

jest.mock('@/components/layout/DashboardSidebar', () => {
  return function MockSidebar(props: { mobileOpen?: boolean }) {
    return <div data-testid="dashboard-sidebar">Sidebar {String(props.mobileOpen)}</div>;
  };
});

jest.mock('@/components/layout/DashboardHeader', () => {
  return function MockHeader() {
    return <div data-testid="dashboard-header">Header</div>;
  };
});

jest.mock('@/components/layout/MobileBottomNav', () => {
  return function MockMobileBottomNav() {
    return <div data-testid="mobile-bottom-nav">Mobile Bottom Nav</div>;
  };
});

jest.mock('@/components/layout/NowQueueDock', () => {
  return function MockNowQueueDock(props: { tenantId?: string }) {
    return <div data-testid="now-queue-dock">Now Queue {props.tenantId}</div>;
  };
});

jest.mock('@/components/ai-chat/FloatingChatbot', () => {
  return function MockFloatingChatbot(props: { tenantId?: string }) {
    return <div data-testid="floating-chatbot">Chatbot {props.tenantId}</div>;
  };
});

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/partner/tenantContext', () => ({
  usePartnerTenantContext: jest.fn(),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockedUsePartnerTenantContext = usePartnerTenantContext as jest.MockedFunction<
  typeof usePartnerTenantContext
>;

describe('DashboardLayout', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    getMockRouter().push.mockReset();
    mockedUsePartnerTenantContext.mockReturnValue({
      effectiveTenantId: 'tenant-123',
      homeTenantId: null,
      activeTenant: null,
      isInPartnerTenantContext: false,
      enterTenantContext: jest.fn(),
      clearTenantContext: jest.fn(),
    });
  });

  it('shows a loading state until auth is hydrated', () => {
    mockedUseAuth.mockReturnValue({
      isAuthenticated: false,
      hydrated: false,
      token: null,
      tenantId: null,
      planTier: null,
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      setPlanTierOverride: jest.fn(),
    });

    render(<DashboardLayout><div>Child content</div></DashboardLayout>);

    expect(screen.getByRole('status', { name: /Loading application/i })).toBeInTheDocument();
  });

  it('redirects unauthenticated users to login when no stored token exists', async () => {
    mockedUseAuth.mockReturnValue({
      isAuthenticated: false,
      hydrated: true,
      token: null,
      tenantId: null,
      planTier: null,
      user: null,
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      setPlanTierOverride: jest.fn(),
    });

    render(<DashboardLayout><div>Child content</div></DashboardLayout>);

    await waitFor(() => {
      expect(getMockRouter().push).toHaveBeenCalledWith('/login');
    });
    expect(screen.queryByText('Child content')).not.toBeInTheDocument();
  });

  it('renders the shell and tenant-scoped utilities for authenticated users', () => {
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

    render(<DashboardLayout><div>Child content</div></DashboardLayout>);

    expect(screen.getByTestId('dashboard-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('dashboard-header')).toBeInTheDocument();
    expect(screen.getByText('Child content')).toBeInTheDocument();
    expect(screen.getByTestId('mobile-bottom-nav')).toBeInTheDocument();
    expect(screen.getByTestId('now-queue-dock')).toHaveTextContent('tenant-123');
    expect(screen.getByTestId('command-palette')).toHaveTextContent('tenant-123');
    expect(screen.getByTestId('floating-chatbot')).toHaveTextContent('tenant-123');
  });
});
