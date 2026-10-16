'use client';

/**
 * Password Reset Modal
 * Handles password reset requirement for first-time login
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Logo } from '@/components/Logo';

interface PasswordResetModalProps {
  email: string;
  onClose: () => void;
  onPasswordReset: (newPassword: string, realm: string) => Promise<void> | void;
  defaultRealm?: string;
}

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

export function PasswordResetModal({ email, onClose, onPasswordReset, defaultRealm }: PasswordResetModalProps) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [realm, setRealm] = useState(defaultRealm || process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'sentinelgrid');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) {
        return;
      }

      const focusable = dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (focusable.length === 0) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    },
    [onClose]
  );

  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    document.addEventListener('keydown', handleKeyDown);
    requestAnimationFrame(() => {
      const firstFocusable = dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      if (firstFocusable) {
        firstFocusable.focus();
      } else {
        dialogRef.current?.focus();
      }
    });

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [handleKeyDown]);

  const handleContinue = async () => {
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    try {
      setLoading(true);
      await onPasswordReset(password, realm);
    } catch (err: any) {
      setError(err.message || 'Password reset failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center px-4">
      <div
        ref={dialogRef}
        className="w-full max-w-md bg-slate-900/95 border border-slate-800 rounded-2xl p-8 shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="password-reset-title"
        aria-describedby="password-reset-description"
        tabIndex={-1}
      >
        <div className="flex justify-center mb-6">
          <Logo className="w-12 h-12" />
        </div>
        
        <h2 id="password-reset-title" className="text-2xl font-semibold mb-2 text-center">Password Reset Required</h2>
        <p id="password-reset-description" className="text-sm text-slate-300 mb-6 text-center">
          For security, you need to set a new password for your account. You'll be redirected to complete this step.
        </p>

        <div className="space-y-4">
          <div className="p-4 bg-cyan-900/20 border border-cyan-800 rounded-lg">
            <p className="text-sm text-cyan-200">
              <strong>Email:</strong> {email}
            </p>
          </div>

          <div>
            <label htmlFor="password-reset-new-password" className="block text-sm font-medium text-slate-300 mb-2">New password</label>
            <input
              id="password-reset-new-password"
              name="new-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="Enter new password"
            />
          </div>

          <div>
            <label htmlFor="password-reset-confirm-password" className="block text-sm font-medium text-slate-300 mb-2">Confirm password</label>
            <input
              id="password-reset-confirm-password"
              name="confirm-password"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="Confirm password"
            />
          </div>

          <div>
            <label htmlFor="password-reset-realm" className="block text-sm font-medium text-slate-300 mb-2">Realm / Tenant realm</label>
            <input
              id="password-reset-realm"
              type="text"
              value={realm}
              onChange={(e) => setRealm(e.target.value)}
              autoComplete="organization"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-cyan-400"
              placeholder="e.g., demo or sg-mt-us-1"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Uses your tenant realm to reset password in the right Keycloak realm.
            </p>
          </div>

          {error && (
            <div className="p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300" role="alert" aria-live="polite">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleContinue}
              disabled={loading}
              className="flex-1 inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors disabled:opacity-50"
            >
              {loading ? 'Updating...' : 'Reset Password'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
