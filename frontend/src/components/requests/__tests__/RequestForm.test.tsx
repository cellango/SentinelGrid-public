import { fireEvent, screen, waitFor } from '@testing-library/react';

import { RequestForm } from '@/components/requests/RequestForm';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

const mockPush = jest.fn();
const mockMutateAsync = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

jest.mock('@/lib/hooks/useAccessRequests', () => ({
  useCreateAccessRequest: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

describe('RequestForm', () => {
  beforeEach(() => {
    mockPush.mockReset();
    mockMutateAsync.mockReset();
    mockMutateAsync.mockResolvedValue({ id: 'request-123' });
  });

  it('prefills request details and submits revoke requests', async () => {
    renderWithProviders(
      <RequestForm
        tenantId="tenant-1"
        initialValues={{
          resource_type: 'entitlement',
          resource_id: 'ent-123',
          action: 'revoke',
          justification: 'Remove unused access for this entitlement',
        }}
      />
    );

    expect(screen.getByLabelText(/resource type/i)).toHaveValue('entitlement');
    expect(screen.getByLabelText(/resource id/i)).toHaveValue('ent-123');
    expect(screen.getByLabelText(/action/i)).toHaveValue('revoke');
    expect(screen.getByLabelText(/justification/i)).toHaveValue(
      'Remove unused access for this entitlement'
    );

    fireEvent.click(screen.getByRole('button', { name: /submit request/i }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({
        tenant_id: 'tenant-1',
        resource_type: 'entitlement',
        resource_id: 'ent-123',
        action: 'revoke',
        justification: 'Remove unused access for this entitlement',
        expires_at: undefined,
      });
    });
    expect(mockPush).toHaveBeenCalledWith('/dashboard/requests/request-123');
  });
});
