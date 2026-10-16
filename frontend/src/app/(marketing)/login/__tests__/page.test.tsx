import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import LoginPage from '../page';
import {
  buildAuthProviderValue,
  renderWithProviders,
} from '@/test-utils/renderWithProviders';
import {
  getMockRouter,
  mockSearchParams,
} from '@/test-utils/navigation';
import { resetTestStorage } from '@/test-utils/storage';

const useAuthMock = jest.fn();
const loginMFAMock = jest.fn();

jest.mock('@/lib/providers/AuthProvider', () => ({
  useAuth: () => useAuthMock(),
}));

jest.mock('@/lib/api/auth', () => ({
  loginMFA: (...args: unknown[]) => loginMFAMock(...args),
}));

describe('LoginPage', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    resetTestStorage();
    mockSearchParams();
    useAuthMock.mockReturnValue(buildAuthProviderValue());
    loginMFAMock.mockReset();
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('directs account recovery to the identity provider without collecting a new password', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);
    await user.click(screen.getByRole('button', { name: /forgot password/i }));
    expect(screen.getByRole('alert')).toHaveTextContent(/verified account recovery/i);
    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
  });

  it('keeps password-reset-required login failures out of the retired direct-reset flow', async () => {
    const user = userEvent.setup();
    useAuthMock.mockReturnValue(buildAuthProviderValue({
      login: jest.fn().mockRejectedValue({ password_reset_required: true }),
    }));
    renderWithProviders(<LoginPage />);
    await user.type(screen.getByLabelText(/email/i), 'reviewer@example.com');
    await user.type(screen.getByLabelText(/^password$/i), 'SyntheticPassword123!');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/verified account recovery/i);
    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
  });

  it('redirects authenticated users to /dashboard when no redirect query is present', async () => {
    const router = getMockRouter();
    useAuthMock.mockReturnValue(
      buildAuthProviderValue({
        isAuthenticated: true,
      })
    );

    renderWithProviders(<LoginPage />);

    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith('/dashboard');
    });
  });

  it('redirects authenticated users to the redirect query target when present', async () => {
    const router = getMockRouter();
    mockSearchParams({ redirect: '/dashboard/incidents' });
    useAuthMock.mockReturnValue(
      buildAuthProviderValue({
        isAuthenticated: true,
      })
    );

    renderWithProviders(<LoginPage />);

    await waitFor(() => {
      expect(router.push).toHaveBeenCalledWith('/dashboard/incidents');
    });
  });

  it('shows the MFA form when login reports mfa_required', async () => {
    const user = userEvent.setup();
    const loginMock = jest.fn().mockRejectedValue({ mfa_required: true });
    useAuthMock.mockReturnValue(
      buildAuthProviderValue({
        login: loginMock,
      })
    );

    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/email/i), 'analyst@example.com');
    await user.type(screen.getByLabelText(/^password$/i), 'DemoPassword123!');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('heading', { name: /verify your identity/i })).toBeInTheDocument();
    expect(screen.getByText(/Enter the code from your authenticator app/i)).toBeInTheDocument();
  });

  it('blocks MFA submit when the otp is blank', async () => {
    const user = userEvent.setup();
    const loginMock = jest.fn().mockRejectedValue({ mfa_required: true });
    useAuthMock.mockReturnValue(
      buildAuthProviderValue({
        login: loginMock,
      })
    );

    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/email/i), 'analyst@example.com');
    await user.type(screen.getByLabelText(/^password$/i), 'DemoPassword123!');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('heading', { name: /verify your identity/i })).toBeInTheDocument();

    const otpField = screen.getByLabelText(/verification code/i);
    await user.type(otpField, '   ');
    await user.click(screen.getByRole('button', { name: /verify/i }));

    expect(screen.getByLabelText(/verification code/i)).toBeInTheDocument();
    expect(loginMFAMock).not.toHaveBeenCalled();
  });

  it('submits MFA verification and redirects after success', async () => {
    const user = userEvent.setup();
    const router = getMockRouter();
    const loginMock = jest.fn().mockRejectedValue({ mfa_required: true });
    loginMFAMock.mockResolvedValue({
      access_token: 'token-123',
      refresh_token: 'refresh-123',
      expires_in: 3600,
      token_type: 'bearer',
      user: {
        id: 'user-1',
        email: 'analyst@example.com',
        tenant_id: 'tenant-123',
        roles: ['SOC_ANALYST'],
      },
    });

    useAuthMock.mockReturnValue(
      buildAuthProviderValue({
        login: loginMock,
      })
    );

    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/email/i), 'analyst@example.com');
    await user.type(screen.getByLabelText(/^password$/i), 'DemoPassword123!');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('heading', { name: /verify your identity/i })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/verification code/i), '123456');
    await user.click(screen.getByRole('button', { name: /verify/i }));

    expect(loginMFAMock).toHaveBeenCalledWith(
      'analyst@example.com',
      'DemoPassword123!',
      '123456',
      false
    );

    await waitFor(
      () => {
        expect(router.push).toHaveBeenCalledWith('/dashboard');
      },
      { timeout: 1000 }
    );
  });
});
