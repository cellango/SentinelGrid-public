"use client";

import Link from "next/link";
import { Logo } from "./Logo";
import { useAuth } from "@/lib/providers/AuthProvider";
import { useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { trackMarketingEvent } from "@/lib/marketing/analytics";
import { TrackedLink } from "@/components/marketing/TrackedLink";
const navLinks = [
  { href: "/product", label: "Product" },
  { href: "/solutions", label: "Solutions" },
  { href: "/pricing", label: "Pricing" },
  { href: "/partners", label: "Partners" },
  { href: "/trust", label: "Trust Center" },
  { href: "/product/ai-shield", label: "AI Shield" },
  { href: "/compare/point-tools", label: "Compare" },
];

export function Header() {
  const { isAuthenticated, user, logout } = useAuth();
  const router = useRouter();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
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
    <header className="border-b border-border sticky top-0 bg-bg/80 backdrop-blur-md z-50">
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-16">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo className="w-7 h-7" />
          <span className="font-semibold tracking-wide text-lg">
            Sentinel<span className="text-cyan-400">Grid</span>
          </span>
        </Link>
        <nav className="hidden md:flex gap-6 text-sm">
          {navLinks.map((link) => (
            <TrackedLink
              key={link.href}
              href={link.href}
              eventName="marketing_nav_click"
              eventProps={{ source: "header_nav", target: link.href.replace(/\//g, "_").slice(1) }}
              className="text-text-muted/70 hover:text-text-main/80 transition-colors"
            >
              {link.label}
            </TrackedLink>
          ))}
        </nav>
        <div className="flex gap-3 items-center">
          <button
            type="button"
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden flex items-center justify-center w-9 h-9 rounded-lg border border-border-muted text-text-muted hover:text-text-main hover:border-slate-500 transition-colors"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
          >
            {mobileOpen ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
          {isAuthenticated && user ? (
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-3 py-2 rounded-full border border-border-muted bg-transparent text-text-main/80 hover:border-cyan-400 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 text-xs font-semibold">
                  {getInitials(user.email)}
                </div>
                <span className="hidden md:inline text-sm text-text-main/80">
                  {user.email.split("@")[0]}
                </span>
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-bg-alt border border-border rounded-lg shadow-xl py-2 z-50">
                  <div className="px-4 py-3 border-b border-border">
                    <p className="text-sm font-medium text-text-main/80">{user.email}</p>
                    <p className="text-xs text-text-muted/70 mt-1">
                      {user.roles.join(", ")}
                    </p>
                  </div>
                  <Link
                    href="/dashboard"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-text-main/80 hover:bg-bg-alt transition-colors"
                  >
                    Dashboard
                  </Link>
                  <Link
                    href="/settings"
                    onClick={() => setShowUserMenu(false)}
                    className="block px-4 py-2 text-sm text-text-main/80 hover:bg-bg-alt transition-colors"
                  >
                    Settings
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-text-main/80 hover:bg-bg-alt transition-colors"
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
                       onClick={() => trackMarketingEvent("marketing_nav_click", { source: "header_cta", target: "login" })}
                       className="px-4 py-2 rounded-full text-sm border border-border-muted bg-transparent text-text-main/80 hover:border-cyan-400 transition-colors"
                     >
                       Sign in
                     </Link>
              <TrackedLink
                href="/demo"
                eventName="marketing_cta_click"
                eventProps={{ source: "header_cta", target: "demo" }}
                className="px-4 py-2 rounded-full text-sm border border-border-muted bg-transparent text-text-main/80 hover:border-cyan-400 transition-colors"
              >
                Book a demo
              </TrackedLink>
              <TrackedLink
                href="/signup"
                eventName="marketing_cta_click"
                eventProps={{ source: "header_cta", target: "signup" }}
                className="px-4 py-2 rounded-full text-sm bg-gradient-to-r from-cyan-400 to-cyan-500 text-slate-950 font-semibold hover:brightness-105 transition-all"
              >
                Get started
              </TrackedLink>
            </>
          )}
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-bg/95 backdrop-blur-md">
          <nav className="max-w-7xl mx-auto px-6 py-4 space-y-1">
            {navLinks.map((link) => (
              <TrackedLink
                key={link.href}
                href={link.href}
                eventName="marketing_nav_click"
                eventProps={{ source: "header_mobile", target: link.href.replace(/\//g, "_").slice(1) }}
                className="block rounded-lg px-3 py-2.5 text-sm text-text-muted hover:text-text-main hover:bg-bg-alt/60 transition-colors"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </TrackedLink>
            ))}
            {!isAuthenticated && (
              <div className="flex flex-col gap-2 pt-3 border-t border-border">
                <TrackedLink
                  href="/signup"
                  eventName="marketing_cta_click"
                  eventProps={{ source: "header_mobile_cta", target: "signup" }}
                  className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
                  onClick={() => setMobileOpen(false)}
                >
                  Get started
                </TrackedLink>
                <TrackedLink
                  href="/demo"
                  eventName="marketing_cta_click"
                  eventProps={{ source: "header_mobile_cta", target: "demo" }}
                  className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-2.5 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
                  onClick={() => setMobileOpen(false)}
                >
                  Book a demo
                </TrackedLink>
              </div>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
