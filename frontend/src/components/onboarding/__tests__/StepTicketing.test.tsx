import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import StepTicketing from '../StepTicketing';
import {
  connectTicketing,
  recheckHealth,
  searchTicketingAssignees,
} from '@/lib/api/onboarding';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

jest.mock('@/lib/api/onboarding', () => ({
  connectTicketing: jest.fn(),
  recheckHealth: jest.fn(),
  searchTicketingAssignees: jest.fn(),
}));

jest.mock('@/lib/onboarding/metrics', () => ({
  recordOnboardingCtaClick: jest.fn(),
}));

const mockedConnectTicketing = connectTicketing as jest.MockedFunction<typeof connectTicketing>;
const mockedRecheckHealth = recheckHealth as jest.MockedFunction<typeof recheckHealth>;
const mockedSearchTicketingAssignees = searchTicketingAssignees as jest.MockedFunction<
  typeof searchTicketingAssignees
>;

describe('StepTicketing', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    mockedConnectTicketing.mockReset();
    mockedRecheckHealth.mockReset();
    mockedSearchTicketingAssignees.mockReset();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.useRealTimers();
    consoleErrorSpy.mockRestore();
  });

  it('searches the downstream directory and fills the selected assignee', async () => {
    jest.useFakeTimers();
    mockedSearchTicketingAssignees.mockResolvedValue({
      provider: 'jira',
      assigneeIdentifierType: 'account_id',
      source: 'draft_config',
      results: [
        {
          value: 'acct-123',
          label: 'Alice Example',
          description: 'alice@example.com',
          identifierType: 'account_id',
          identifiers: { account_id: 'acct-123' },
        },
      ],
    });

    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime });

    renderWithProviders(
      <StepTicketing onNext={jest.fn()} onBack={jest.fn()} onSkip={jest.fn()} />
    );

    await user.click(screen.getByRole('button', { name: /Jira/ }));
    await user.type(
      screen.getByPlaceholderText('https://your-domain.atlassian.net'),
      'https://example.atlassian.net'
    );
    await user.type(screen.getByPlaceholderText('SECOPS'), 'SECOPS');
    await user.type(screen.getByPlaceholderText('Bearer ... or Basic ...'), 'Bearer jira-token');
    await user.click(screen.getByRole('radio', { name: /Named owner/i }));
    await user.type(screen.getByPlaceholderText('Search Jira users by name or email'), 'Alice');

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(mockedSearchTicketingAssignees).toHaveBeenCalledWith({
        query: 'Alice',
        provider: 'jira',
        url: 'https://example.atlassian.net',
        project: 'SECOPS',
        api_key: 'Bearer jira-token',
        assignee_identifier_type: 'account_id',
        limit: 8,
      });
    });

    await user.click(screen.getByRole('button', { name: /Alice Example/i }));

    expect(
      screen.getByPlaceholderText('712020:8f3f3cde-1234-4567-89ab-123456789abc')
    ).toHaveValue('acct-123');
  });

  it('submits a healthy Jira handoff and advances the wizard', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedConnectTicketing.mockResolvedValue({
      status: 'healthy',
      health: {
        status: 'healthy',
        checked_at: '2026-03-27T15:00:00Z',
        provider: 'jira',
      },
    } as any);

    renderWithProviders(
      <StepTicketing onNext={onNext} onBack={jest.fn()} onSkip={jest.fn()} />
    );

    await user.click(screen.getByRole('button', { name: /Jira/ }));
    await user.type(
      screen.getByPlaceholderText('https://your-domain.atlassian.net'),
      'https://example.atlassian.net'
    );
    await user.type(screen.getByPlaceholderText('SECOPS'), 'SECOPS');
    await user.type(screen.getByPlaceholderText('Bearer ... or Basic ...'), 'Bearer jira-token');
    await user.click(screen.getByRole('checkbox', { name: /Notify Slack/i }));
    await user.click(screen.getByRole('button', { name: /Save handoff settings/i }));

    await waitFor(() => {
      expect(mockedConnectTicketing).toHaveBeenCalledWith(
        expect.objectContaining({
          provider: 'jira',
          url: 'https://example.atlassian.net',
          project: 'SECOPS',
          api_key: 'Bearer jira-token',
          socManaged: false,
          assignment_mode: 'service_owner',
        })
      );
    });
    expect(onNext).toHaveBeenCalled();
  });

  it('shows a degraded health warning when the handoff recheck fails', async () => {
    const onNext = jest.fn();
    const user = userEvent.setup();

    mockedRecheckHealth.mockResolvedValue({
      health: {
        status: 'degraded',
        provider: 'jira',
        warnings: ['Named owner routing requires a default assignee.'],
      },
    } as any);

    renderWithProviders(
      <StepTicketing
        onNext={onNext}
        onBack={jest.fn()}
        onSkip={jest.fn()}
        initialHealth={{ status: 'unknown', provider: 'jira' }}
      />
    );

    await user.click(screen.getByRole('button', { name: /Re-run health/i }));

    await waitFor(() => {
      expect(
        screen.getAllByText(/Named owner routing requires a default assignee\./i).length
      ).toBeGreaterThan(0);
    });
    expect(onNext).not.toHaveBeenCalled();
  });
});
