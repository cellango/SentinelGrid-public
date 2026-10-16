'use client';

import Link from 'next/link';
import { useAuth } from '@/lib/providers/AuthProvider';
import { useRouter } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';

export default function Header() {
  const { isAuthenticated, user, login, logout } = useAuth();
  const router = useRouter();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserMenu]);

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
    router.push('/');
  };

  const getInitials = (email: string) => {
    const parts = email.split('@');
    if (parts[0].length >= 2) {
      return parts[0].substring(0, 2).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  };

  return (
    <header className="sticky top-0 z-20 backdrop-blur-md bg-[rgba(2,6,23,0.85)] border-b border-[rgba(15,23,42,0.9)]">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-18">
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-6.5 h-7 rounded-[10px] bg-gradient-to-br from-primary to-secondary shadow-[0_0_25px_rgba(34,211,238,0.5)] relative">
            <div className="absolute inset-1 rounded-lg border border-[rgba(15,23,42,0.9)]" />
          </div>
          <span className="font-semibold tracking-wide">
            Sentinel<span className="text-primary">Grid</span>
          </span>
        </Link>
        <nav className="hidden md:flex gap-6 text-sm">
          <Link href="#product" className="text-text-muted hover:text-text-main">
            Product
          </Link>
          <Link href="#how-it-works" className="text-text-muted hover:text-text-main">
            How it works
          </Link>
          <Link href="#solutions" className="text-text-muted hover:text-text-main">
            Solutions
          </Link>
          <Link href="#pricing" className="text-text-muted hover:text-text-main">
            Pricing
          </Link>
        </nav>
        <div className="flex gap-3 items-center">
          {isAuthenticated && user ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-2 rounded-full border border-[rgba(148,163,184,0.5)] bg-transparent hover:border-primary transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 text-xs font-semibold">
                  {getInitials(user.email)}
                </div>
                <span className="hidden md:inline text-sm text-text-main">
                  {user.email.split('@')[0]}
                </span>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-2 z-50">
                  <div className="px-4 py-3 border-b border-slate-800">
                    <p className="text-sm font-medium text-text-main">{user.email}</p>
                    <p className="text-xs text-text-muted mt-1">
                      {user.roles.join(', ')}
                    </p>
                  </div>
                  <Link
                    href="/dashboard"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-text-main hover:bg-slate-800 transition-colors"
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/dashboard/iam/my-account"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-text-main hover:bg-slate-800 transition-colors"
                  >
                    My Account
                  </Link>
                  <Link
                    href="/dashboard/settings"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-text-main hover:bg-slate-800 transition-colors"
                  >
                    Settings
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-text-main hover:bg-slate-800 transition-colors"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link
                href="/login"
                className="px-4 py-2 rounded-full text-sm border border-[rgba(148,163,184,0.5)] bg-transparent text-text-main hover:border-primary transition-colors"
              >
                Sign in
              </Link>
              <Link
                href="#contact"
                className="px-4 py-2 rounded-full text-sm bg-gradient-to-r from-primary to-secondary text-bg font-semibold hover:brightness-105"
              >
                Book a demo
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}

