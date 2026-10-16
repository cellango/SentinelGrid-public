import { render, screen } from '@testing-library/react';

import AIAppsPage from '../apps/page';
import AIAlertsPage from '../alerts/page';
import AISetupPage from '../setup/page';

describe('AI security launch boundary', () => {
  it('replaces the AI apps registry with an honest launch-boundary notice', () => {
    render(<AIAppsPage />);

    expect(
      screen.getByText(/AI app registry stays implementation-led for launch/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/\+ Create App/i)).not.toBeInTheDocument();
  });

  it('replaces the standalone AI alerts board with guidance back to the main queue', () => {
    render(<AIAlertsPage />);

    expect(
      screen.getByText(/AI-originated alerts are handled in the main queue for launch/i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/SG-AI-001/i)).not.toBeInTheDocument();
  });

  it('keeps the setup page but removes fake app-registry and policy-management steps', () => {
    render(<AISetupPage />);

    expect(screen.getByText(/AI Shield setup is implementation-led for launch/i)).toBeInTheDocument();
    expect(screen.queryByText(/your-ai-shield-key/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Create an AI App/i)).not.toBeInTheDocument();
  });
});
