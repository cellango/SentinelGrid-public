import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import StepAppSec from '../StepAppSec';
import { connectAppSec, recheckHealth } from '@/lib/api/onboarding';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/onboarding', () => ({
  connectAppSec: jest.fn(),
  recheckHealth: jest.fn(),
}));

const mockedConnectAppSec = connectAppSec as jest.MockedFunction<typeof connectAppSec>;
const mockedRecheckHealth = recheckHealth as jest.MockedFunction<typeof recheckHealth>;

describe('StepAppSec', () => {
  beforeEach(() => {
    mockedConnectAppSec.mockReset();
    mockedRecheckHealth.mockReset();
  });

  it('advances the wizard only when AppSec health is healthy', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedConnectAppSec.mockResolvedValue({
      success: true,
      status: 'healthy',
      health: {
        status: 'healthy',
        checked_at: '2026-04-18T14:00:00Z',
      },
    } as any);

    renderWithProviders(<StepAppSec onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} />);

    await act(async () => {
      await user.type(screen.getByPlaceholderText('https://apps.yourdomain.com'), 'https://appsec.example.com');
      await user.type(screen.getByPlaceholderText('••••••••'), 'secret-token');
      await user.click(screen.getByRole('button', { name: /save & check health/i }));
    });

    await waitFor(() => {
      expect(mockedConnectAppSec).toHaveBeenCalledWith(
        expect.objectContaining({
          gateway_url: 'https://appsec.example.com',
          api_key: 'secret-token',
        })
      );
      expect(onNext).toHaveBeenCalled();
    });
  });

  it('shows the degraded status and keeps the wizard on the page when health is not healthy', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedConnectAppSec.mockResolvedValue({
      success: false,
      status: 'degraded',
      message: 'AppSec settings were saved, but health is degraded',
      health: {
        status: 'degraded',
        checked_at: '2026-04-18T14:05:00Z',
      },
    } as any);

    renderWithProviders(<StepAppSec onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} />);

    await act(async () => {
      await user.type(screen.getByPlaceholderText('https://apps.yourdomain.com'), 'https://appsec.example.com');
      await user.type(screen.getByPlaceholderText('••••••••'), 'bad-token');
      await user.click(screen.getByRole('button', { name: /save & check health/i }));
    });

    expect(await screen.findByText(/health is degraded/i)).toBeInTheDocument();
    expect(onNext).not.toHaveBeenCalled();
  });
});
