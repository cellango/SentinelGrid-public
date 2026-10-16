import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { DemoRequestForm } from '../DemoRequestForm';
import { createDemoRequest } from '@/lib/api/leads';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/leads', () => ({
  createDemoRequest: jest.fn(),
}));

jest.mock('@/lib/marketing/analytics', () => ({
  trackMarketingEvent: jest.fn(),
}));

const mockedCreateDemoRequest = createDemoRequest as jest.MockedFunction<typeof createDemoRequest>;

describe('DemoRequestForm', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    mockedCreateDemoRequest.mockReset();
    window.history.pushState({}, '', '/demo');
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('submits the standard launch-path qualification by default', async () => {
    const user = userEvent.setup();
    mockedCreateDemoRequest.mockResolvedValue({
      success: true,
      lead_id: 'lead-123',
      message: 'ok',
    });

    renderWithProviders(<DemoRequestForm />);

    await user.type(screen.getByLabelText(/^name$/i), 'Jamie Rivera');
    await user.type(screen.getByLabelText(/^work email$/i), 'buyer@example.com');
    await user.type(screen.getByLabelText(/^company name$/i), 'Example Co');
    await user.click(screen.getByRole('button', { name: /request a guided demo/i }));

    await waitFor(() => {
      expect(mockedCreateDemoRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          motion: 'standard',
          identity_profile: 'microsoft_entra',
          rollout_scope: 'single_environment',
          retention_profile: 'standard',
          ai_shield_fit: 'none',
        })
      );
    });
  });

  it('marks a request for guided review when rollout qualifiers exceed the standard launch path', async () => {
    const user = userEvent.setup();
    mockedCreateDemoRequest.mockResolvedValue({
      success: true,
      lead_id: 'lead-456',
      message: 'ok',
    });

    renderWithProviders(<DemoRequestForm />);

    await user.click(screen.getByText(/tell us more/i));
    await user.selectOptions(screen.getByLabelText(/identity path/i), 'mixed');
    await user.selectOptions(screen.getByLabelText(/rollout scope/i), 'multi_environment');
    await user.selectOptions(screen.getByLabelText(/retention and trust needs/i), 'extended_or_archive');
    await user.selectOptions(screen.getByLabelText(/ai shield interest/i), 'primary');

    expect(
      screen.getByText(/this looks like a guided review instead of the standard launch path/i)
    ).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^name$/i), 'Jamie Rivera');
    await user.type(screen.getByLabelText(/^work email$/i), 'buyer@example.com');
    await user.type(screen.getByLabelText(/^company name$/i), 'Example Co');
    await user.click(screen.getByRole('button', { name: /request a guided demo/i }));

    await waitFor(() => {
      expect(mockedCreateDemoRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          motion: 'standard',
          identity_profile: 'mixed',
          rollout_scope: 'multi_environment',
          retention_profile: 'extended_or_archive',
          ai_shield_fit: 'primary',
        })
      );
    });
  });
});
