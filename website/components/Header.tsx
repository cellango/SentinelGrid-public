"use client";

import Link from "next/link";
import { Logo } from "./Logo";
import { useAuth } from "@/lib/providers/AuthProvider";
import { useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { LoginDialog } from "./auth/LoginDialog";

export function Header() {
  const { isAuthenticated, user, logout } = useAuth();
  const router = useRouter();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showLoginDialog, setShowLoginDialog] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    if (showUserMenu) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showUserMenu]);

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
    router.push("/");
  };

  const getInitials = (email: string) => {
    const parts = email.split("@");
    if (parts[0].length >= 2) {
      return parts[0].substring(0, 2).toUpperCase();
    }
    return email.substring(0, 2).toUpperCase();
  };

  return (
    <header className="border-b border-slate-800 sticky top-0 bg-slate-950/80 backdrop-blur-md z-50">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo className="w-7 h-7" />
          <span className="font-semibold tracking-wide text-lg">
            Sentinel<span className="text-cyan-400">Grid</span>
          </span>
        </Link>
        <nav className="hidden md:flex gap-6 text-sm items-center">
          <Link
            href="/#how-it-works"
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            How it works
          </Link>
          <Link
            href="/#security-in-a-box"
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            Security in a Box
          </Link>
          <div className="relative group">
            <button className="text-slate-400 hover:text-slate-200 transition-colors flex items-center gap-1">
              Services
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <div className="absolute left-0 mt-2 w-48 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-2 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
              <Link
                href="/ai-shield"
                className="block px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
              >
                AI Shield
              </Link>
              <Link
                href="/ai-pentest"
                className="block px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
              >
                Pentest Agent
              </Link>
              <Link
                href="/siem-soar"
                className="block px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
              >
                Managed SIEM + SOAR
              </Link>
            </div>
          </div>
          <Link
            href="/#pricing"
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            Pricing
          </Link>
          <Link
            href="/trust"
            className="text-slate-400 hover:text-slate-200 transition-colors"
          >
            Trust &amp; SOC 2
          </Link>
        </nav>
        <div className="flex gap-3 items-center">
          {isAuthenticated && user ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-2 rounded-full border border-slate-600 bg-transparent text-slate-200 hover:border-cyan-400 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 text-xs font-semibold">
                  {getInitials(user.email)}
                </div>
                <span className="hidden md:inline text-sm text-slate-200">
                  {user.email.split("@")[0]}
                </span>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-2 z-50">
                  <div className="px-4 py-3 border-b border-slate-800">
                    <p className="text-sm font-medium text-slate-200">{user.email}</p>
                    <p className="text-xs text-slate-400 mt-1">
                      {user.roles.join(", ")}
                    </p>
                  </div>
                  <Link
                    href="/dashboard"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/settings"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
                  >
                    Settings
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-slate-800 transition-colors"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
                 ) : (
                   <>
                     <button
                       onClick={() => setShowLoginDialog(true)}
                       className="px-4 py-2 rounded-full text-sm border border-slate-600 bg-transparent text-slate-200 hover:border-cyan-400 transition-colors"
                     >
                       Sign in
                     </button>
              <Link
                href="/demo"
                className="px-4 py-2 rounded-full text-sm border border-slate-600 bg-transparent text-slate-200 hover:border-cyan-400 transition-colors"
              >
                Book a demo
              </Link>
              <Link
                href="/signup"
                className="px-4 py-2 rounded-full text-sm bg-gradient-to-r from-cyan-400 to-cyan-500 text-slate-950 font-semibold hover:brightness-105 transition-all"
              >
                Get started
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Render LoginDialog in body using portal */}
      {typeof window !== 'undefined' && createPortal(
        <LoginDialog
          isOpen={showLoginDialog}
          onClose={() => setShowLoginDialog(false)}
          onSuccess={() => {
            setShowLoginDialog(false);
            router.push('/dashboard');
          }}
        />,
        document.body
      )}
    </header>
  );
}
