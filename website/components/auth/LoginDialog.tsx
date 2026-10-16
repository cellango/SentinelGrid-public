'use client';

import { useState } from 'react';
import { useAuth } from '@/lib/providers/AuthProvider';
import { Logo } from '@/components/Logo';

interface LoginDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function LoginDialog({ isOpen, onClose, onSuccess }: LoginDialogProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password, rememberMe);
      onSuccess?.();
      onClose();
    } catch (err: any) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900/95 border border-slate-800 rounded-2xl p-8 shadow-2xl w-full max-w-md">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-2.5">
            <Logo className="w-7 h-7" />
            <span className="font-semibold tracking-wide text-lg">
              Sentinel<span className="text-cyan-400">Grid</span>
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <h2 className="text-2xl font-semibold mb-2">Welcome back</h2>
        <p className="text-sm text-slate-300 mb-6">
          Sign in to your SentinelGrid account
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="email" className="block text-xs text-slate-300 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 focus:border-cyan-400 focus:outline-none"
              placeholder="you@company.com"
              autoComplete="email"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-xs text-slate-300 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200 focus:border-cyan-400 focus:outline-none"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded"
              />
              Remember me
            </label>
            <a
              href="#"
              className="text-xs text-cyan-400 hover:text-cyan-300"
              onClick={(e) => {
                e.preventDefault();
                // TODO: Implement forgot password
              }}
            >
              Forgot password?
            </a>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}

