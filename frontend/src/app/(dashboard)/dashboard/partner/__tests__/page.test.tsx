import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import PartnerConsolePage from '../page';

const { mockPathname } = require('@/test-utils/navigation');

describe('PartnerConsolePage', () => {
  it('renders a qualified-scope notice instead of a demo-backed partner console', () => {
    mockPathname('/dashboard/partner');

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <PartnerConsolePage />
      </QueryClientProvider>
    );

    expect(
      screen.getByText(/Partner workflows are not part of the default self-serve launch/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Acme Corp/i)).not.toBeInTheDocument();
  });
});
