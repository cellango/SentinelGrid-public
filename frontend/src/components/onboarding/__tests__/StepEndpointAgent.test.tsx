import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import StepEndpointAgent from '../StepEndpointAgent';
import { recheckHealth } from '@/lib/api/onboarding';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('../ImageSelection', () => {
  const ImageSelectionMock = () => <div>Image Selection</div>;
  ImageSelectionMock.displayName = 'ImageSelectionMock';
  return ImageSelectionMock;
});

jest.mock('@/lib/api/onboarding', () => ({
  recheckHealth: jest.fn(),
}));

const mockedRecheckHealth = recheckHealth as jest.MockedFunction<typeof recheckHealth>;

describe('StepEndpointAgent', () => {
  beforeEach(() => {
    mockedRecheckHealth.mockReset();
    window.localStorage.clear();
  });

  it('advances only when endpoint coverage validates as healthy', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedRecheckHealth.mockResolvedValue({
      success: true,
      health: {
        status: 'healthy',
        checked_at: '2026-04-18T12:00:00Z',
        message: 'Endpoint agent is registered and reporting for this tenant.',
      },
    } as any);

    renderWithProviders(
      <StepEndpointAgent onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /validate endpoint coverage/i }));
    });

    await waitFor(() => {
      expect(mockedRecheckHealth).toHaveBeenCalledWith('endpoint');
      expect(onNext).toHaveBeenCalled();
    });
  });

  it('keeps the wizard on the step when no endpoint agent is registered', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedRecheckHealth.mockResolvedValue({
      success: true,
      health: {
        status: 'pending',
        checked_at: '2026-04-18T12:00:00Z',
        message: 'No endpoint agent is registered for this tenant yet. Deploy the agent and re-run validation.',
      },
    } as any);

    renderWithProviders(
      <StepEndpointAgent onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} />
    );

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /validate endpoint coverage/i }));
    });

    expect(
      (await screen.findAllByText(/no endpoint agent is registered for this tenant yet/i)).length
    ).toBeGreaterThan(0);
    expect(onNext).not.toHaveBeenCalled();
  });
});
