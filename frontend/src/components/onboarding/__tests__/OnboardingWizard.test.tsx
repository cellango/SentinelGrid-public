import { screen, waitFor } from '@testing-library/react';

import OnboardingWizard from '../OnboardingWizard';
import { getOnboardingStatus } from '@/lib/api/onboarding';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/onboarding', () => ({
  getOnboardingStatus: jest.fn(),
}));

jest.mock('@/lib/onboarding/metrics', () => ({
  recordOnboardingCompleted: jest.fn(),
  recordOnboardingStarted: jest.fn(),
  recordOnboardingStepCompleted: jest.fn(),
  recordOnboardingStepSkipped: jest.fn(),
  recordOnboardingStepViewed: jest.fn(),
  syncOnboardingMetricsFromStatus: jest.fn(),
}));

jest.mock('../StepIdP', () => {
  const StepIdPMock = () => <div>Identity Step</div>;
  StepIdPMock.displayName = 'StepIdPMock';
  return StepIdPMock;
});
jest.mock('../StepCloudConnection', () => {
  const StepCloudConnectionMock = () => <div>Cloud Step</div>;
  StepCloudConnectionMock.displayName = 'StepCloudConnectionMock';
  return StepCloudConnectionMock;
});
jest.mock('../StepEndpointAgent', () => {
  const StepEndpointAgentMock = () => <div>Endpoint Step</div>;
  StepEndpointAgentMock.displayName = 'StepEndpointAgentMock';
  return StepEndpointAgentMock;
});
jest.mock('../StepGitSecurity', () => {
  const StepGitSecurityMock = () => <div>Git Step</div>;
  StepGitSecurityMock.displayName = 'StepGitSecurityMock';
  return StepGitSecurityMock;
});
jest.mock('../StepAIShield', () => {
  const StepAIShieldMock = () => <div>AI Shield Step</div>;
  StepAIShieldMock.displayName = 'StepAIShieldMock';
  return StepAIShieldMock;
});
jest.mock('../StepAppSec', () => {
  const StepAppSecMock = () => <div>AppSec Step</div>;
  StepAppSecMock.displayName = 'StepAppSecMock';
  return StepAppSecMock;
});
jest.mock('../StepTicketing', () => {
  const StepTicketingMock = () => <div>Ticketing Step</div>;
  StepTicketingMock.displayName = 'StepTicketingMock';
  return StepTicketingMock;
});
jest.mock('../StepTenantReadiness', () => {
  const StepTenantReadinessMock = () => <div>Tenant Readiness Step</div>;
  StepTenantReadinessMock.displayName = 'StepTenantReadinessMock';
  return StepTenantReadinessMock;
});

const mockedGetOnboardingStatus = getOnboardingStatus as jest.MockedFunction<
  typeof getOnboardingStatus
>;

const baseStatus = {
  idp_provider: 'google_workspace',
  onboarding_completed: false,
  access_profile_ready: false,
  birthright_ready: false,
  step_idp_completed: true,
  step_cloud_completed: true,
  steps: [
    { id: 'idp', done: true },
    { id: 'cloud', done: true },
    { id: 'endpoint', done: false },
    { id: 'git', done: false },
  ],
  services_selected: { cloud: true, git: true, socManaged: true },
};

describe('OnboardingWizard', () => {
  beforeEach(() => {
    mockedGetOnboardingStatus.mockResolvedValue(baseStatus as any);
    localStorage.clear();
  });

  it('seeds the canonical flow from backend status and keeps tenant readiness last', async () => {
    renderWithProviders(<OnboardingWizard initialStep={3} />);

    await waitFor(() => {
      expect(
        screen.getByText(/Connect Google Workspace, then AWS, then finish endpoint coverage\./i)
      ).toBeInTheDocument();
    });

    const stepButtons = screen.getAllByRole('button');

    await waitFor(() => {
      expect(stepButtons[0]).toHaveClass('bg-green-500');
      expect(stepButtons[1]).toHaveClass('bg-green-500');
    });

    expect(stepButtons).toHaveLength(5);
    expect(screen.getByText('Identity')).toBeInTheDocument();
    expect(screen.getByText('Cloud')).toBeInTheDocument();
    expect(screen.getByText('Endpoint')).toBeInTheDocument();
    expect(screen.getByText('Git')).toBeInTheDocument();
    expect(screen.getByText('Tenant readiness')).toBeInTheDocument();
  });

  it('includes ticketing only for customer-managed SOC onboarding', async () => {
    mockedGetOnboardingStatus.mockResolvedValue({
      ...baseStatus,
      services_selected: { cloud: true, git: true, socManaged: false },
      ticketing_health: { status: 'degraded' },
      steps: [
        { id: 'idp', done: true },
        { id: 'cloud', done: true },
        { id: 'endpoint', done: true },
        { id: 'git', done: true },
      ],
    } as any);

    renderWithProviders(<OnboardingWizard />);

    expect(await screen.findByText(/Ticketing/i)).toBeInTheDocument();
    expect(screen.getByText(/Tenant readiness/i)).toBeInTheDocument();
  });

  it('includes the AI Shield step only when the service was selected', async () => {
    mockedGetOnboardingStatus.mockResolvedValue({
      ...baseStatus,
      services_selected: { cloud: true, git: true, aiShield: 'hosted', socManaged: true },
      steps: [
        { id: 'idp', done: true },
        { id: 'cloud', done: true },
        { id: 'endpoint', done: true },
        { id: 'git', done: true },
      ],
    } as any);

    renderWithProviders(<OnboardingWizard />);

    expect(await screen.findByText(/AI Shield/i)).toBeInTheDocument();
    expect(screen.queryByText(/Ticketing/i)).not.toBeInTheDocument();
  });
});
