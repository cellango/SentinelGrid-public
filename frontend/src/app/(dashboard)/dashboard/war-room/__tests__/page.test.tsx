import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import WarRoomPage from '../page';
import { getNowQueue } from '@/lib/api/dashboard';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useEventSourceStream } from '@/lib/realtime/useEventSourceStream';

const { mockPathname } = require('@/test-utils/navigation');

jest.mock('@/lib/api/dashboard', () => ({
  getNowQueue: jest.fn(),
  getNowQueueStreamUrl: jest.fn(() => '/events'),
  normalizeNowQueueResponse: jest.fn((payload) => payload),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/realtime/useEventSourceStream', () => ({
  useEventSourceStream: jest.fn(),
}));

const mockedGetNowQueue = getNowQueue as jest.MockedFunction<typeof getNowQueue>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockedUseEventSourceStream = useEventSourceStream as jest.MockedFunction<
  typeof useEventSourceStream
>;

describe('WarRoomPage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    mockPathname('/dashboard/war-room');
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
    mockedUseEventSourceStream.mockReturnValue({ status: 'connected' } as any);
  });

  it('shows an honest empty state when the now queue has no live items', async () => {
    mockedGetNowQueue.mockResolvedValue({
      items: [],
      summary: undefined,
    } as any);

    render(
      <QueryClientProvider client={queryClient}>
        <WarRoomPage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/No live queue items yet/i)).toBeInTheDocument();
    });
    expect(
      screen.queryByText(/Unauthorized Access to Production S3 Bucket/i)
    ).not.toBeInTheDocument();
  });
});
