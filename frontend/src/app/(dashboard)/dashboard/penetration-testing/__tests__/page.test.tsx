import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PenetrationTestingPage from '../page';

const { mockPathname } = require('@/test-utils/navigation');

describe('PenetrationTestingPage', () => {
  it('renders the launch-boundary notice instead of a self-serve checkout flow', () => {
    mockPathname('/dashboard/penetration-testing');

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <PenetrationTestingPage />
      </QueryClientProvider>
    );

    expect(
      screen.getByText(/Penetration testing is not part of the day-one self-serve SaaS/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Web & API/i)).not.toBeInTheDocument();
  });
});
