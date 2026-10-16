import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import NowQueueDock from '../NowQueueDock';
import { recordAIFeedback } from '@/lib/api/ai-feedback';
import { getNowQueue, getNowQueueStreamUrl, normalizeNowQueueResponse } from '@/lib/api/dashboard';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useEventSourceStream } from '@/lib/realtime/useEventSourceStream';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

const { mockPathname } = require('@/test-utils/navigation');

jest.mock('@/components/ai/AITransparencyPanel', () => {
  return function MockAITransparencyPanel({
    title,
    onDisagree,
  }: {
    title: string;
    onDisagree: () => void;
  }) {
    return (
      <div>
        <p>{title}</p>
        <button type="button" onClick={onDisagree}>
          Disagree
        </button>
      </div>
    );
  };
});

jest.mock('@/lib/api/ai-feedback', () => ({
  recordAIFeedback: jest.fn(),
}));

jest.mock('@/lib/api/dashboard', () => ({
  getNowQueue: jest.fn(),
  getNowQueueStreamUrl: jest.fn(),
  normalizeNowQueueResponse: jest.fn(),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/lib/realtime/useEventSourceStream', () => ({
  useEventSourceStream: jest.fn(),
}));

const mockedRecordAIFeedback = recordAIFeedback as jest.MockedFunction<typeof recordAIFeedback>;
const mockedGetNowQueue = getNowQueue as jest.MockedFunction<typeof getNowQueue>;
const mockedGetNowQueueStreamUrl = getNowQueueStreamUrl as jest.MockedFunction<
  typeof getNowQueueStreamUrl
>;
const mockedNormalizeNowQueueResponse = normalizeNowQueueResponse as jest.MockedFunction<
  typeof normalizeNowQueueResponse
>;
const mockedUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockedUseEventSourceStream = useEventSourceStream as jest.MockedFunction<
  typeof useEventSourceStream
>;

const nowQueuePayload = {
  tenant_id: 'tenant-123',
  generated_at: '2026-03-28T12:00:00.000Z',
  summary: {
    total_items: 2,
    urgent_items: 1,
    incidents: 1,
    alerts: 1,
    recommendations: 0,
    domains: [
      { domain: 'identity', count: 1 },
      { domain: 'cloud', count: 1 },
    ],
  },
  items: [
    {
      id: 'incident-1',
      item_type: 'incident',
      priority: 'critical',
      title: 'Privilege escalation incident',
      summary: 'Admin access expanded to an unapproved identity.',
      why_now: 'The account is still active and linked to production systems.',
      status: 'open',
      owner: 'SOC Team',
      source_label: 'Now Queue',
      href: '/dashboard/incidents/incident-1',
      action_label: 'Open incident',
      action_href: '/dashboard/incidents/incident-1',
      domains: ['identity'],
      entities: [],
      evidence: [],
      estimated_time_minutes: 12,
    },
    {
      id: 'alert-1',
      item_type: 'alert',
      priority: 'high',
      title: 'Suspicious sign-in alert',
      summary: 'Repeated sign-ins from a new region.',
      why_now: 'The actor is still authenticating.',
      status: 'triage',
      owner: 'Analyst',
      source_label: 'Now Queue',
      href: '/dashboard/alerts/alert-1',
      action_label: 'Open alert',
      action_href: '/dashboard/alerts/alert-1',
      domains: ['cloud'],
      entities: [],
      evidence: [],
      estimated_time_minutes: 8,
    },
  ],
};

describe('NowQueueDock', () => {
  beforeEach(() => {
    localStorage.clear();
    mockedRecordAIFeedback.mockReset();
    mockedGetNowQueue.mockResolvedValue(nowQueuePayload as any);
    mockedGetNowQueueStreamUrl.mockReturnValue('/api/v1/orchestrator/tenant/tenant-123/now-queue/stream');
    mockedNormalizeNowQueueResponse.mockImplementation((payload) => payload);
    mockedUseEventSourceStream.mockReturnValue({
      status: 'unsupported',
      isLive: false,
    } as any);
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

    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: jest.fn().mockImplementation(() => ({
        matches: false,
        media: '(max-width: 1023px)',
        onchange: null,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        addListener: jest.fn(),
        removeListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  it('stays hidden on the root dashboard route', async () => {
    mockPathname('/dashboard');

    renderWithProviders(<NowQueueDock tenantId="tenant-123" />);

    await waitFor(() => {
      expect(screen.queryByText(/^Now Queue$/i)).not.toBeInTheDocument();
    });
  });

  it('restores expanded state and shows top queue items on non-root routes', async () => {
    mockPathname('/dashboard/incidents');
    localStorage.setItem('sg_now_queue_dock_state', 'expanded');

    renderWithProviders(<NowQueueDock tenantId="tenant-123" />);

    expect((await screen.findAllByText(/Privilege escalation incident/i)).length).toBeGreaterThan(0);
    expect(screen.getByText(/2 items across incidents, alerts, and recommendations\./i)).toBeInTheDocument();
    expect(
      screen.getAllByText(
        (_, node) =>
          node?.tagName === 'P' &&
          Boolean(node.textContent?.includes('1 urgent item need attention first.'))
      ).length
    ).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: /Collapse Now queue widget/i })).toBeInTheDocument();
  });

  it('records disagreement feedback for the active queue item', async () => {
    const user = userEvent.setup();
    mockPathname('/dashboard/incidents');
    localStorage.setItem('sg_now_queue_dock_state', 'expanded');

    renderWithProviders(<NowQueueDock tenantId="tenant-123" />);

    await user.click((await screen.findAllByRole('button', { name: /^Disagree$/i }))[0]);

    expect(mockedRecordAIFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        tenantId: 'tenant-123',
        actorUserId: 'user-1',
        action: 'ai_priority_disagreed',
        resourceType: 'incident',
        resourceId: 'incident-1',
      })
    );
  });
});
