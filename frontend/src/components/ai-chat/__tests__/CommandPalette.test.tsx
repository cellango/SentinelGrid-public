import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import CommandPalette from '../CommandPalette';
import { getPeopleAccessSnapshot } from '@/lib/api/dashboard';
import { getIAMUsers, getPolicies } from '@/lib/api/iam-portal';
import { listDetectionRules } from '@/lib/api/detections';
import { listAlerts } from '@/lib/api/siem';
import { listIncidents } from '@/lib/api/incidents';
import { listReports } from '@/lib/api/reports';
import { getChatSuggestions, sendDashboardChat } from '@/lib/api/dashboard-chat';
import { useAuth } from '@/lib/providers/AuthProvider';

const { getMockRouter, mockPathname } = require('@/test-utils/navigation');

jest.mock('@/components/ui/AgentBadge', () => {
  return function MockAgentBadge({ agentId }: { agentId: string }) {
    return <span>{agentId}</span>;
  };
});

jest.mock('@/lib/api/dashboard-chat', () => ({
  getChatSuggestions: jest.fn(),
  sendDashboardChat: jest.fn(),
}));

jest.mock('@/lib/api/siem', () => ({
  listAlerts: jest.fn(),
}));

jest.mock('@/lib/api/incidents', () => ({
  listIncidents: jest.fn(),
}));

jest.mock('@/lib/api/detections', () => ({
  listDetectionRules: jest.fn(),
}));

jest.mock('@/lib/api/reports', () => ({
  listReports: jest.fn(),
}));

jest.mock('@/lib/api/iam-portal', () => ({
  getPolicies: jest.fn(),
  getIAMUsers: jest.fn(),
}));

jest.mock('@/lib/api/dashboard', () => ({
  getPeopleAccessSnapshot: jest.fn(),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

const mockedGetChatSuggestions = getChatSuggestions as jest.MockedFunction<typeof getChatSuggestions>;
const mockedSendDashboardChat = sendDashboardChat as jest.MockedFunction<typeof sendDashboardChat>;
const mockedListAlerts = listAlerts as jest.MockedFunction<typeof listAlerts>;
const mockedListIncidents = listIncidents as jest.MockedFunction<typeof listIncidents>;
const mockedListDetectionRules = listDetectionRules as jest.MockedFunction<typeof listDetectionRules>;
const mockedListReports = listReports as jest.MockedFunction<typeof listReports>;
const mockedGetPolicies = getPolicies as jest.MockedFunction<typeof getPolicies>;
const mockedGetIAMUsers = getIAMUsers as jest.MockedFunction<typeof getIAMUsers>;
const mockedGetPeopleAccessSnapshot = getPeopleAccessSnapshot as jest.MockedFunction<
  typeof getPeopleAccessSnapshot
>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

function seedWorkspaceApis() {
  mockedListAlerts.mockResolvedValue({ alerts: [] } as any);
  mockedListIncidents.mockResolvedValue({ items: [] } as any);
  mockedGetIAMUsers.mockResolvedValue([]);
  mockedListDetectionRules.mockResolvedValue([]);
  mockedGetPolicies.mockResolvedValue([]);
  mockedListReports.mockResolvedValue([]);
  mockedGetPeopleAccessSnapshot.mockResolvedValue({
    users_total: 42,
    users_admins: 3,
    mfa_coverage_percent: 98,
    mfa_missing_count: 2,
    dormant_accounts_count: 1,
  });
  mockedGetChatSuggestions.mockResolvedValue([
    'Show critical incidents from the last 24h',
  ]);
  mockedSendDashboardChat.mockResolvedValue({
    reply: 'ok',
    conversation_id: 'conv-1',
  } as any);
}

describe('CommandPalette', () => {
  beforeEach(() => {
    localStorage.clear();
    mockPathname('/dashboard/incidents');
    getMockRouter().push.mockReset();
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
    seedWorkspaceApis();
  });

  it('opens from the global keyboard shortcut and loads route results', async () => {
    const user = userEvent.setup();
    await act(async () => {
      render(<CommandPalette tenantId="tenant-123" />);
    });

    await act(async () => {
      await user.keyboard('{Control>}k{/Control}');
    });

    expect(
      await screen.findByRole('dialog', { name: /universal search and command palette/i })
    ).toBeInTheDocument();
    expect(await screen.findByText(/^Alert Queue$/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(mockedListAlerts).toHaveBeenCalled();
    });
  });

  it('filters protected routes out for non-admin protect-tier users', async () => {
    const user = userEvent.setup();
    await act(async () => {
      render(<CommandPalette tenantId="tenant-123" />);
    });

    await act(async () => {
      await user.keyboard('{Control>}k{/Control}');
    });

    expect(
      await screen.findByRole('dialog', { name: /universal search and command palette/i })
    ).toBeInTheDocument();
    await act(async () => {
      await user.type(
        screen.getByRole('textbox', { name: /search sentinelgrid workspace/i }),
        'compliance'
      );
    });

    await waitFor(() => {
      expect(screen.queryByText(/^Compliance$/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/^Partner Console$/i)).not.toBeInTheDocument();
    });
  });

  it('keeps non-launch partner and operations routes out of jump results even for admin users', async () => {
    const user = userEvent.setup();
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

    await act(async () => {
      render(<CommandPalette tenantId="tenant-123" />);
    });

    await act(async () => {
      await user.keyboard('{Control>}k{/Control}');
    });
    expect(
      await screen.findByRole('dialog', { name: /universal search and command palette/i })
    ).toBeInTheDocument();
    await act(async () => {
      await user.type(
        screen.getByRole('textbox', { name: /search sentinelgrid workspace/i }),
        'operations'
      );
    });

    await waitFor(() => {
      expect(screen.queryByText(/^Platform Operations$/i)).not.toBeInTheDocument();
    });

    await act(async () => {
      await user.clear(screen.getByRole('textbox', { name: /search sentinelgrid workspace/i }));
    });
    await act(async () => {
      await user.type(
        screen.getByRole('textbox', { name: /search sentinelgrid workspace/i }),
        'partner'
      );
    });
    await waitFor(() => {
      expect(screen.queryByText(/^Partner Console$/i)).not.toBeInTheDocument();
    });
  });
});
