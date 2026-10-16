import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import OnboardingBanner from '../OnboardingBanner';
import {
  enableDetectionRules,
  getOnboardingStatus,
} from '@/lib/api/onboarding';
import { loadSampleLogs } from '@/lib/api/siem';
import { useAuth } from '@/lib/providers/AuthProvider';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/onboarding', () => ({
  getOnboardingStatus: jest.fn(),
  enableDetectionRules: jest.fn(),
}));

jest.mock('@/lib/api/siem', () => ({
  loadSampleLogs: jest.fn(),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/onboarding/metrics', () => ({
  recordOnboardingBannerDismissed: jest.fn(),
  recordOnboardingCtaClick: jest.fn(),
  syncOnboardingMetricsFromStatus: jest.fn(),
}));

const mockedGetOnboardingStatus = getOnboardingStatus as jest.MockedFunction<
  typeof getOnboardingStatus
>;
const mockedEnableDetectionRules = enableDetectionRules as jest.MockedFunction<
  typeof enableDetectionRules
>;
const mockedLoadSampleLogs = loadSampleLogs as jest.MockedFunction<typeof loadSampleLogs>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

const baseStatus = {
  idp_connected: false,
  idp_provider: 'google_workspace',
  cloud_connected: false,
  endpoint_deployed: false,
  git_connected: false,
  ticketing_connected: false,
  onboarding_completed: false,
  overall_complete: false,
  last_incomplete_step_id: 'idp',
  next_step: 'idp',
  status_version: 'v1',
  steps: [
    { id: 'idp', done: false },
    { id: 'cloud', done: false },
    { id: 'endpoint', done: false },
    { id: 'git', done: false },
    { id: 'ticketing', done: false },
  ],
  services_selected: { cloud: true, git: true, socManaged: false, idpProvider: 'google_workspace' },
  access_profile_ready: false,
  birthright_ready: false,
  announcements: [],
};

describe('OnboardingBanner', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    localStorage.clear();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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
    mockedGetOnboardingStatus.mockResolvedValue(baseStatus as any);
    mockedEnableDetectionRules.mockResolvedValue({
      success: true,
      rules_enabled: ['failed_logins', 'new_admin', 'suspicious_cloud'],
      rules_created: 3,
      rules_updated: 0,
    } as any);
    mockedLoadSampleLogs.mockResolvedValue({ ingested: 20, source: 'auth' } as any);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('renders the current next step and activation summary while onboarding is incomplete', async () => {
    renderWithProviders(<OnboardingBanner />);

    expect(await screen.findByText(/First-Run Checklist/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Fastest path to first value: connect Google Workspace, then AWS, then finish endpoint coverage\./i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Current next step/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Continue with Identity/i })).toBeInTheDocument();
    expect(
      screen.getByText((_, node) =>
        Boolean(node?.textContent?.match(/\b0 of \d+ integrations connected\b/i))
      )
    ).toBeInTheDocument();
    expect(screen.getByText(/Ticketing Pending/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Enable quick-start detections/i })
    ).toBeEnabled();
  });

  it('hides when onboarding and people readiness are complete', async () => {
    mockedGetOnboardingStatus.mockResolvedValue({
      ...baseStatus,
      onboarding_completed: true,
      overall_complete: true,
      access_profile_ready: true,
      birthright_ready: true,
    } as any);

    renderWithProviders(<OnboardingBanner />);

    await waitFor(() => {
      expect(screen.queryByText(/First-Run Checklist/i)).not.toBeInTheDocument();
    });
  });

  it('dismisses by status version so a new version shows the banner again', async () => {
    mockedGetOnboardingStatus
      .mockResolvedValueOnce({ ...baseStatus, status_version: 'v1' } as any)
      .mockResolvedValueOnce({
        ...baseStatus,
        status_version: 'v2',
        announcements: [{ id: 'config-incomplete', title: 'Resume setup', body: 'New work is ready.' }],
      } as any);

    const user = userEvent.setup();
    const firstRender = renderWithProviders(<OnboardingBanner />);

    expect(await screen.findByText(/First-Run Checklist/i)).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: /Dismiss/i })[0]);

    await waitFor(() => {
      expect(screen.queryByText(/First-Run Checklist/i)).not.toBeInTheDocument();
    });

    firstRender.unmount();
    renderWithProviders(<OnboardingBanner />);

    expect(await screen.findByText(/First-Run Checklist/i)).toBeInTheDocument();
    expect(screen.getByText(/Resume setup/i)).toBeInTheDocument();
  });
});
