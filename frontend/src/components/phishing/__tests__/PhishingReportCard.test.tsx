/**
 * Tests for PhishingReportCard Component
 */

import { render, screen } from '@testing-library/react';
import PhishingReportCard from '../PhishingReportCard';
import { PhishingReport } from '@/lib/api/phishing';

const mockReport: PhishingReport = {
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
  raw_email: 'Raw email content',
};

describe('PhishingReportCard', () => {
  it('renders report information', () => {
    const onClick = jest.fn();
    render(<PhishingReportCard report={mockReport} onClick={onClick} />);

    expect(screen.getByText('Urgent: Verify Your Account')).toBeInTheDocument();
    expect(screen.getByText(/attacker@example.com/)).toBeInTheDocument();
    expect(screen.getByText(/user@company.com/)).toBeInTheDocument();
  });

  it('displays classification badge', () => {
    const onClick = jest.fn();
    render(<PhishingReportCard report={mockReport} onClick={onClick} />);

    expect(screen.getByText('phishing')).toBeInTheDocument();
  });

  it('displays status badge', () => {
    const onClick = jest.fn();
    render(<PhishingReportCard report={mockReport} onClick={onClick} />);

    expect(screen.getByText(/confirmed phishing/i)).toBeInTheDocument();
  });

  it('displays confidence score', () => {
    const onClick = jest.fn();
    render(<PhishingReportCard report={mockReport} onClick={onClick} />);

    expect(screen.getByText(/95.0%/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = jest.fn();
    render(<PhishingReportCard report={mockReport} onClick={onClick} />);

    const card = screen.getByText('Urgent: Verify Your Account').closest('div');
    card?.click();

    expect(onClick).toHaveBeenCalled();
  });
});

