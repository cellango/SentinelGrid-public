import { screen, waitFor } from '@testing-library/react';

import MyAccountPage from '@/app/(dashboard)/dashboard/iam/my-account/page';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

const { mockSearchParams, resetNavigationMocks } = require('@/test-utils/navigation');

const mockedGetProfile = jest.fn();
const mockedGetSessions = jest.fn();
const mockedGetApps = jest.fn();
const mockedUseAuth = jest.fn();

jest.mock('next/navigation', () => {
  const { getMockRouter, getMockSearchParams } = require('@/test-utils/navigation');
  return {
    useRouter() {
      return getMockRouter();
    },
    useSearchParams() {
      return getMockSearchParams();
    },
  };
});

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: () => mockedUseAuth(),
}));

jest.mock('@/lib/api/iam-self-service', () => ({
  getProfile: (...args: unknown[]) => mockedGetProfile(...args),
  updateProfile: jest.fn(),
  changePassword: jest.fn(),
  requestPasswordReset: jest.fn(),
  getSessions: (...args: unknown[]) => mockedGetSessions(...args),
  logoutSession: jest.fn(),
  getApps: (...args: unknown[]) => mockedGetApps(...args),
}));

describe('MyAccountPage', () => {
  beforeEach(() => {
    resetNavigationMocks();
    mockedUseAuth.mockReturnValue({ token: 'test-token' });
    mockedGetProfile.mockReset();
    mockedGetSessions.mockReset();
    mockedGetApps.mockReset();
    mockedGetProfile.mockResolvedValue({
      id: 'user-1',
      username: 'analyst',
      email: 'analyst@example.com',
      firstName: 'Avery',
      lastName: 'Analyst',
      locale: 'en',
      timezone: 'America/Chicago',
      emailVerified: true,
    });
    mockedGetSessions.mockResolvedValue([
      {
        id: 'session-1',
        username: 'analyst@example.com',
        userId: 'user-1',
        ipAddress: '203.0.113.10',
        start: 1713170400,
        lastAccess: 1713174000,
        clients: {},
      },
    ]);
    mockedGetApps.mockResolvedValue([]);
  });

  it('respects the tab query param and uses the honest sign-out label', async () => {
    mockSearchParams({ tab: 'sessions' });

    renderWithProviders(<MyAccountPage />);

    expect(await screen.findByRole('heading', { name: 'Active Sessions' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Sign Out All Sessions' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Sign Out$/ })).not.toBeInTheDocument();
  });

  it('shows an error instead of demo fallback when profile loading fails', async () => {
    mockSearchParams({ tab: 'profile' });
    mockedGetProfile.mockRejectedValueOnce(new Error('profile unavailable'));

    renderWithProviders(<MyAccountPage />);

    expect(
      await screen.findByText('Unable to load your profile from IAM self-service right now.')
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText(/showing demo profile/i)).not.toBeInTheDocument();
    });
  });
});
