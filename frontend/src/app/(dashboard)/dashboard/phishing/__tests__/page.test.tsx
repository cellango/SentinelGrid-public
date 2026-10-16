/**
 * Tests for Phishing Queue Page
 */

import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PhishingQueuePage from '../page';
import * as phishingAPI from '@/lib/api/phishing';

// Mock the API
jest.mock('@/lib/api/phishing');

const mockReports = [
  {
    id: '1',
    subject: 'Urgent: Verify Your Account',
    from_address: 'attacker@example.com',
    reported_by: 'user@company.com',
    classification: 'phishing',
    status: 'confirmed_phishing',
    severity: 'high',
    classification_confidence: 95,
    received_date: '2024-01-01T12:00:00Z',
    created_at: '2024-01-01T12:00:00Z',
    updated_at: '2024-01-01T12:00:00Z',
    tenant_id: 'tenant-1',
    message_id: 'msg1',
    to_address: 'victim@company.com',
  },
];

describe('PhishingQueuePage', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    jest.clearAllMocks();
    // Ensure tenant is set so the query runs in tests
    localStorage.setItem('tenant_id', 'tenant-1');
  });

  it('renders phishing reports', async () => {
    (phishingAPI.getPhishingReports as jest.Mock).mockResolvedValue(mockReports);

    render(
      <QueryClientProvider client={queryClient}>
        <PhishingQueuePage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Urgent: Verify Your Account')).toBeInTheDocument();
    });
  });

  it('displays empty state when no reports', async () => {
    (phishingAPI.getPhishingReports as jest.Mock).mockResolvedValue([]);

    render(
      <QueryClientProvider client={queryClient}>
        <PhishingQueuePage />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/No phishing reports found/)).toBeInTheDocument();
    });
  });

  it('filters reports by search query', async () => {
    (phishingAPI.getPhishingReports as jest.Mock).mockResolvedValue(mockReports);

    render(
      <QueryClientProvider client={queryClient}>
        <PhishingQueuePage />
      </QueryClientProvider>
    );

    // Search functionality would be tested here
    // This is a placeholder test structure
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search by subject/)).toBeInTheDocument();
    });
  });
});
