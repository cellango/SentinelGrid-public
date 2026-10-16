import { render, screen } from '@testing-library/react';

import SecurityGraphPreviewCard from '../SecurityGraphPreviewCard';

describe('SecurityGraphPreviewCard', () => {
  it('shows an honest empty state and points back to the queue when no live graph context exists', () => {
    render(
      <SecurityGraphPreviewCard
        queue={{
          tenant_id: 'tenant-123',
          generated_at: '2026-04-15T12:00:00Z',
          items: [],
          summary: {
            total_items: 0,
            urgent_items: 0,
            incidents: 0,
            alerts: 0,
            recommendations: 0,
            domains: [],
          },
        }}
      />
    );

    expect(screen.getByText(/No live attack-path context is available yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/seeded demo paths/i)).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open queue/i })).toHaveAttribute('href', '/dashboard');
  });
});
