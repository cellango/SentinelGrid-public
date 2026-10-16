import React from 'react';
import { render, screen } from '@testing-library/react';
import LogManagementPage from '../page';

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn().mockReturnValue({
    data: {
      hits: [
        {
          id: '1',
          '@timestamp': new Date().toISOString(),
          edr_source: 'sentinelguard-openedr',
          sidecar_enabled: true,
          event: { action: 'process' },
          user: { email: 'user@example.com' },
        },
      ],
      took: 10,
    },
    isLoading: false,
    isFetching: false,
    refetch: jest.fn(),
  }),
}));

// Mock API client imports used inside the component
jest.mock('@/lib/api/siem', () => ({
  searchLogsSimple: jest.fn(),
  loadSampleLogs: jest.fn().mockResolvedValue({ ingested: 0, source: 'endpoint' }),
}));

describe('LogManagementPage EDR badges', () => {
  it('renders edr_source and sidecar badges from results', () => {
    render(<LogManagementPage />);

    expect(screen.getAllByText(/Behavioral telemetry/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/sidecar on/i).length).toBeGreaterThan(0);
  });
});
