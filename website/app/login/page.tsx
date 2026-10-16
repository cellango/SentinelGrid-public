'use client';

/**
 * Login Page
 * Custom login form for SentinelGrid
 */

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Logo } from '@/components/Logo';

export default function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // If already authenticated, redirect to dashboard
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password, rememberMe);
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-slate-900/70 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <div className="flex justify-center mb-6">
          <Logo className="w-12 h-12" />
        </div>
        
        <h1 className="text-2xl font-semibold mb-2 text-center">Welcome back</h1>
        <p className="text-sm text-slate-300 mb-8 text-center">
          Sign in to your SentinelGrid account
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="admin@sentinelgrid.ai"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="Enter your password"
            />
          </div>

          <div className="flex items-center">
            <input
              id="remember"
              type="checkbox"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-cyan-400 focus:ring-cyan-400"
            />
            <label htmlFor="remember" className="ml-2 text-sm text-slate-300">
              Remember me
            </label>
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
          <p className="text-xs text-slate-400 mb-2">
            Don&apos;t have an account?{' '}
            <Link href="/signup" className="text-cyan-400 hover:text-cyan-300">
              Sign up
            </Link>
          </p>
          <p className="text-xs text-slate-500">
            Default admin: admin@sentinelgrid.ai
          </p>
        </div>
      </div>
    </main>
  );
}
