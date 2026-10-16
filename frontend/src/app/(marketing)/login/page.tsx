'use client';

/**
 * Login Page
 * Custom login form for SentinelGrid
 */

import { useEffect, useState, Suspense } from 'react';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Logo } from '@/components/Logo';
import { HelpButton } from '@/components/HelpButton';

function LoginPageContent() {
  const { isAuthenticated, login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mfaRequired, setMfaRequired] = useState(false);


  useEffect(() => {
    // If already authenticated, redirect to dashboard or redirect param
    if (isAuthenticated) {
      const redirectTo = searchParams.get('redirect') || '/dashboard';
      router.push(redirectTo);
    }
  }, [isAuthenticated, router, searchParams]);

  // Pre-fill email from URL param (e.g. after signup/payment redirect)
  useEffect(() => {
    const emailParam = searchParams.get('email');
    if (emailParam && !email) {
      setEmail(emailParam);
    }
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let loginResponse;
      if (mfaRequired) {
        if (!otp.trim()) {
          setError('MFA required. Please enter your verification code.');
          setLoading(false);
          return;
        }
        const { loginMFA } = await import('@/lib/api/auth');
        loginResponse = await loginMFA(email, password, otp.trim(), rememberMe);
      } else {
        try {
          loginResponse = await login(email, password, rememberMe);
        } catch (err: any) {
          if (err?.mfa_required) {
            setMfaRequired(true);
            setError(null);
            setLoading(false);
            return;
          }
          throw err;
        }
      }

      setMfaRequired(false);
      // Get redirect target from URL parameter or default to dashboard
      const redirectTo = searchParams.get('redirect') || '/dashboard';

      // Small delay to ensure token is fully stored
      await new Promise(resolve => setTimeout(resolve, 100));
      router.push(redirectTo);
    } catch (err: any) {
      setError(err.password_reset_required
        ? "Use your identity provider's verified account recovery flow to reset your password."
        : err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-bg text-text-main flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-bg-alt/90 border border-border rounded-2xl p-8 shadow-2xl">
        <div className="flex justify-center mb-6">
          <Logo className="w-12 h-12" />
        </div>
        
        {error && (
          <div
            className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300"
            role="alert"
            aria-live="polite"
          >
            {error}
          </div>
        )}

        {mfaRequired ? (
          <>
            <h1 className="text-2xl font-semibold mb-2 text-center">Verify your identity</h1>
            <p className="text-sm text-text-muted mb-1 text-center">
              Enter the code from your authenticator app
            </p>
            <p className="text-xs text-text-main0 mb-6 text-center">{email}</p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="otp" className="block text-sm font-medium text-text-muted mb-2">
                  Verification code
                </label>
                <input
                  id="otp"
                  name="otp"
                  type="text"
                  value={otp}
                  onChange={(e) => {
                    setOtp(e.target.value);
                    setError(null);
                  }}
                  required
                  autoFocus
                  autoComplete="one-time-code"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  className="w-full px-4 py-2 bg-bg-alt border border-border-muted rounded-lg text-text-main text-center text-lg tracking-[0.3em] focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  placeholder="000000"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Verifying...' : 'Verify'}
              </button>
            </form>

            <div className="text-center mt-4">
              <button
                type="button"
                onClick={() => {
                  setMfaRequired(false);
                  setOtp('');
                  setError(null);
                }}
                className="text-sm text-text-muted/70 hover:text-text-main/80 transition-colors"
              >
                Back to sign in
              </button>
            </div>
          </>
        ) : (
          <>
            <h1 className="text-2xl font-semibold mb-2 text-center">Welcome back</h1>
            <p className="text-sm text-text-muted mb-8 text-center">
              Sign in to your SentinelGrid account
            </p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-text-muted mb-2">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="username"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  inputMode="email"
                  className="w-full px-4 py-2 bg-bg-alt border border-border-muted rounded-lg text-text-main focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  placeholder="you@company.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-text-muted mb-2">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setError(null);
                  }}
                  required
                  autoComplete="current-password"
                  className="w-full px-4 py-2 bg-bg-alt border border-border-muted rounded-lg text-text-main focus:outline-none focus:ring-2 focus:ring-cyan-400"
                  placeholder="Enter your password"
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-border-muted bg-bg-alt text-cyan-400 focus:ring-cyan-400"
                  />
                  <label htmlFor="remember" className="ml-2 text-sm text-text-muted">
                    Remember me
                  </label>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setError("Use your identity provider's verified account recovery flow to reset your password.");
                  }}
                  className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                >
                  Forgot password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>

            <div className="text-center">
              <p className="text-xs text-text-muted/70 mb-2">
                Don&apos;t have an account?{' '}
                <Link href="/signup" className="text-cyan-400 hover:text-cyan-300">
                  Sign up
                </Link>
              </p>
            </div>
          </>
        )}
      </div>

      <HelpButton />


    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg flex items-center justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-400"></div></div>}>
      <LoginPageContent />
    </Suspense>
  );
}
