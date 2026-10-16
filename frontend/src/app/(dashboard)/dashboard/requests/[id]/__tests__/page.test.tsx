import { screen } from '@testing-library/react';

import RequestDetailPage from '@/app/(dashboard)/dashboard/requests/[id]/page';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

const mockUseAccessRequest = jest.fn();
const mockUseAuth = jest.fn();
const mockRequestDetail = jest.fn();

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'request-123' }),
}));

jest.mock('@/lib/hooks/useAccessRequests', () => ({
  useAccessRequest: (...args: unknown[]) => mockUseAccessRequest(...args),
}));

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('@/components/ui/Breadcrumbs', () => {
  const BreadcrumbsMock = () => <div data-testid="breadcrumbs" />;
  BreadcrumbsMock.displayName = 'BreadcrumbsMock';
  return BreadcrumbsMock;
});
jest.mock('@/components/requests/RequestTimeline', () => ({
  RequestTimeline: ({ requestId }: { requestId: string }) => (
    <div data-testid="timeline">{requestId}</div>
  ),
}));
jest.mock('@/components/requests/RequestDetail', () => ({
  RequestDetail: (props: Record<string, unknown>) => {
    mockRequestDetail(props);
    return <div data-testid="request-detail" />;
  },
}));

const baseRequest = {
  id: 'request-123',
  tenant_id: 'tenant-1',
  requested_by: 'user-1',
  requested_for: 'user-1',
  resource_type: 'entitlement',
  resource_id: 'ent-123',
  action: 'revoke',
  justification: 'Remove unused access',
  status: 'pending',
  created_at: '2026-04-15T12:00:00Z',
  updated_at: '2026-04-15T12:00:00Z',
};

describe('RequestDetailPage', () => {
  beforeEach(() => {
    mockRequestDetail.mockReset();
    mockUseAccessRequest.mockReturnValue({
      data: baseRequest,
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });
  });

  it('allows request owners to cancel but not review without admin role', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        roles: ['SOC_ANALYST'],
      },
    });

    renderWithProviders(<RequestDetailPage />);

    expect(screen.getByTestId('request-detail')).toBeInTheDocument();
    expect(mockRequestDetail).toHaveBeenCalledWith(
      expect.objectContaining({
        canReview: false,
        canCancel: true,
      })
    );
  });

  it('allows tenant admins to review requests they do not own', () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: 'admin-1',
        roles: ['TENANT_ADMIN'],
      },
    });
    mockUseAccessRequest.mockReturnValue({
      data: {
        ...baseRequest,
        requested_by: 'user-2',
      },
      isLoading: false,
      error: null,
      refetch: jest.fn(),
    });

    renderWithProviders(<RequestDetailPage />);

    expect(mockRequestDetail).toHaveBeenCalledWith(
      expect.objectContaining({
        canReview: true,
        canCancel: false,
      })
    );
  });
});
