import { screen, waitFor } from '@testing-library/react';

import Breadcrumbs from '../Breadcrumbs';
import { getIncident } from '@/lib/api/incidents';
import { renderWithProviders } from '@/test-utils/renderWithProviders';

const { mockPathname } = require('@/test-utils/navigation');

jest.mock('@/lib/api/incidents', () => ({
  getIncident: jest.fn(),
}));

jest.mock('@/lib/api/accessRequests', () => ({
  accessRequestsApi: { get: jest.fn() },
}));

jest.mock('@/lib/api/certificates', () => ({
  certificateApi: { getCertificate: jest.fn() },
}));

jest.mock('@/lib/api/detection-rules', () => ({
  getDetectionRule: jest.fn(),
}));

jest.mock('@/lib/api/governance', () => ({
  campaignsApi: { get: jest.fn() },
}));

jest.mock('@/lib/api/iam-portal', () => ({
  getApp: jest.fn(),
}));

jest.mock('@/lib/api/phishing', () => ({
  getPhishingReport: jest.fn(),
}));

jest.mock('@/lib/api/playbooks', () => ({
  playbooksApi: { get: jest.fn() },
}));

jest.mock('@/lib/api/scans', () => ({
  getScan: jest.fn(),
}));

jest.mock('@/lib/api/siem', () => ({
  getAlert: jest.fn(),
}));

jest.mock('@/lib/api/tickets', () => ({
  getTicket: jest.fn(),
}));

const mockedGetIncident = getIncident as jest.MockedFunction<typeof getIncident>;

describe('Breadcrumbs', () => {
  beforeEach(() => {
    localStorage.clear();
    mockedGetIncident.mockReset();
  });

  it('renders static breadcrumb labels for dashboard routes', () => {
    mockPathname('/dashboard/iam/people');

    renderWithProviders(<Breadcrumbs />);

    expect(screen.getByRole('link', { name: /^Now$/i })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: /^Identity Operations$/i })).toHaveAttribute(
      'href',
      '/dashboard/iam'
    );
    expect(screen.getByText(/^People & Access$/i)).toHaveAttribute('aria-current', 'page');
  });

  it('resolves dynamic incident labels from the entity API', async () => {
    mockPathname('/dashboard/incidents/inc-123');
    mockedGetIncident.mockResolvedValue({
      id: 'inc-123',
      external_id: 'INC-123',
      title: 'Credential stuffing incident',
    } as any);

    renderWithProviders(<Breadcrumbs />);

    await waitFor(() => {
      expect(mockedGetIncident).toHaveBeenCalledWith('inc-123');
    });

    expect(await screen.findByText('INC-123: Credential stuffing incident: inc-123')).toHaveAttribute(
      'aria-current',
      'page'
    );
  });
});
