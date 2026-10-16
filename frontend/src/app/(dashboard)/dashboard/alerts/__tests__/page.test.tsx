import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import AlertsPage from '../page';
import { getSIEMStats, getSourceHealth, listAlerts } from '@/lib/api/siem';
import { useAuth } from '@/lib/providers/AuthProvider';

const { mockPathname, mockSearchParams } = require('@/test-utils/navigation');

jest.mock('../components/MitreFilter', () => {
  return function MockMitreFilter() {
    return <div>MITRE Filter</div>;
  };
});

jest.mock('@/lib/api/siem', () => ({
  listAlerts: jest.fn(),
  getSIEMStats: jest.fn(),
  updateAlert: jest.fn(),
  getSourceHealth: jest.fn(),
}));

jest.mock('@/lib/api/playbooks', () => ({
  playbooksApi: {
    execute: jest.fn(),
  },
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

const mockedListAlerts = listAlerts as jest.MockedFunction<typeof listAlerts>;
const mockedGetSIEMStats = getSIEMStats as jest.MockedFunction<typeof getSIEMStats>;
const mockedGetSourceHealth = getSourceHealth as jest.MockedFunction<typeof getSourceHealth>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

describe('AlertsPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    mockPathname('/dashboard/alerts');
    mockSearchParams({});
    mockedUseAuth.mockReturnValue({
      isAuthenticated: true,
      hydrated: true,
      token: 'token-123',
      tenantId: 'tenant-123',
      planTier: 'protect_defend',
      user: {
        id: 'user-1',
        email: 'analyst@example.com',
        roles: ['SOC_ANALYST'],
        plan_tier: 'protect_defend',
      },
      login: jest.fn(),
      logout: jest.fn(),
      refreshToken: jest.fn(),
      setPlanTierOverride: jest.fn(),
    });
    mockedListAlerts.mockResolvedValue({ alerts: [] } as any);
    mockedGetSIEMStats.mockResolvedValue({
      alerts_count: 0,
      alerts_by_severity: {},
      alerts_by_status: {},
    } as any);
    mockedGetSourceHealth.mockResolvedValue({
      ingestion_service: 'healthy',
      siem_agent: 'healthy',
      opensearch: 'healthy',
      wazuh: 'healthy',
      openedr: 'healthy',
      velociraptor: 'healthy',
    } as any);
  });

  it('stays empty when no live alerts exist instead of showing sample data', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AlertsPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getAllByText(/No live alerts/i).length).toBeGreaterThan(0);
    });
    expect(screen.queryByText(/Suspicious login from unusual location/i)).not.toBeInTheDocument();
  });
});
