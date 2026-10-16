import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import SecurityGraphPage from '../page';

const { mockPathname, mockSearchParams } = require('@/test-utils/navigation');

jest.mock('@/lib/api/siem', () => ({
  getAlert: jest.fn(),
}));

jest.mock('@/lib/api/incidents', () => ({
  getIncident: jest.fn(),
}));

describe('SecurityGraphPage', () => {
  it('requires real story context instead of rendering seeded demo paths', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    mockPathname('/dashboard/security-graph');
    mockSearchParams({});

    render(
      <QueryClientProvider client={queryClient}>
        <SecurityGraphPage />
      </QueryClientProvider>
    );

    expect(await screen.findByText(/Open a story to build the graph/i)).toBeInTheDocument();
    expect(screen.queryByText(/Public S3/i)).not.toBeInTheDocument();
  });
});
