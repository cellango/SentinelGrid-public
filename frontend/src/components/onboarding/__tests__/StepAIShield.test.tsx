import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import StepAIShield from '../StepAIShield';
import { connectAIShield, recheckHealth } from '@/lib/api/onboarding';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/onboarding', () => ({
  connectAIShield: jest.fn(),
  recheckHealth: jest.fn(),
}));

const mockedConnectAIShield = connectAIShield as jest.MockedFunction<typeof connectAIShield>;
const mockedRecheckHealth = recheckHealth as jest.MockedFunction<typeof recheckHealth>;

describe('StepAIShield', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    mockedConnectAIShield.mockReset();
    mockedRecheckHealth.mockReset();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('advances the wizard only when AI Shield health is healthy', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedConnectAIShield.mockResolvedValue({
      success: true,
      status: 'healthy',
      health: {
        status: 'healthy',
        checked_at: '2026-04-15T12:00:00Z',
      },
    } as any);

    renderWithProviders(
      <StepAIShield onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} mode="hosted" />
    );

    await user.type(
      screen.getByPlaceholderText('https://ai-shield.sentinelgrid.ai/gateway'),
      'https://ai-shield.example.com'
    );
    await user.type(screen.getByPlaceholderText('••••••••'), 'secret-token');
    await user.click(screen.getByRole('button', { name: /save & check health/i }));

    await waitFor(() => {
      expect(mockedConnectAIShield).toHaveBeenCalledWith(
        expect.objectContaining({
          mode: 'hosted',
          endpoint_url: 'https://ai-shield.example.com',
          api_key: 'secret-token',
        })
      );
    });
    expect(onNext).toHaveBeenCalled();
  });

  it('shows the degraded status and keeps the wizard on the page when health is not healthy', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedConnectAIShield.mockResolvedValue({
      success: false,
      status: 'degraded',
      message: 'AI Shield configuration saved, but health is degraded',
      health: {
        status: 'degraded',
        checked_at: '2026-04-15T12:05:00Z',
      },
    } as any);

    renderWithProviders(
      <StepAIShield onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} mode="hosted" />
    );

    await user.type(
      screen.getByPlaceholderText('https://ai-shield.sentinelgrid.ai/gateway'),
      'https://ai-shield.example.com'
    );
    await user.type(screen.getByPlaceholderText('••••••••'), 'bad-token');
    await user.click(screen.getByRole('button', { name: /save & check health/i }));

    expect(await screen.findByText(/health is degraded/i)).toBeInTheDocument();
    expect(onNext).not.toHaveBeenCalled();
  });
});
