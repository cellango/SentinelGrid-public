import { render, screen } from '@testing-library/react';

import DashboardSidebar from '../DashboardSidebar';
import { useAuth } from '@/lib/providers/AuthProvider';

const { mockPathname } = require('@/test-utils/navigation');

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe('DashboardSidebar', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('filters plan-gated items and marks the active route for protect tier users', () => {
    mockPathname('/dashboard/alerts');
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

    render(<DashboardSidebar />);

    expect(
      screen
        .getAllByRole('link', { name: /Alert Queue/i })
        .some((link) => link.getAttribute('aria-current') === 'page')
    ).toBe(true);
    expect(screen.queryByText(/Detection Coverage/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Compliance$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Pen Tests/i)).not.toBeInTheDocument();
    expect(screen.getAllByText(/Cloud Posture/i).length).toBeGreaterThan(0);
  });

  it('shows higher-tier navigation entries for admin users on comply tier', () => {
    mockPathname('/dashboard/compliance');
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      hydrated: true,
      token: 'token-123',
      tenantId: 'tenant-123',
      planTier: 'protect_defend_comply',
      user: {
        id: 'user-1',
        email: 'admin@example.com',
        roles: ['TENANT_ADMIN'],
        plan_tier: 'protect_defend_comply',
      },
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      setPlanTierOverride: jest.fn(),
    });

    render(<DashboardSidebar />);

    expect(screen.getAllByText(/^Compliance$/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Reports/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/AI Governance/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/IAM Reports/i)).not.toBeInTheDocument();
    expect(
      screen
        .getAllByRole('link', { name: /^Compliance$/i })
        .some((link) => link.getAttribute('aria-current') === 'page')
    ).toBe(true);
  });
});
