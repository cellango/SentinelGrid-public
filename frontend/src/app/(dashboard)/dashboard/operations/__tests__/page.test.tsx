import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import OperationsDashboard from '../page';

const { mockPathname } = require('@/test-utils/navigation');

describe('OperationsDashboard', () => {
  it('shows an internal-route notice instead of placeholder platform metrics', () => {
    mockPathname('/dashboard/operations');

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <OperationsDashboard />
      </QueryClientProvider>
    );

    expect(
      screen.getByText(/Platform operations is outside the customer-facing launch surface/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/^MTTR$/i)).not.toBeInTheDocument();
  });
});
