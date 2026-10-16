import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import MarketingFunnelPage from '../page';

const { mockPathname } = require('@/test-utils/navigation');

describe('MarketingFunnelPage', () => {
  it('renders an internal-route notice instead of customer-facing revenue analytics', () => {
    mockPathname('/dashboard/operations/marketing-funnel');

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <MarketingFunnelPage />
      </QueryClientProvider>
    );

    expect(
      screen.getByText(/Revenue and activation analytics stay outside the customer launch surface/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/CTA clicks/i)).not.toBeInTheDocument();
  });
});
