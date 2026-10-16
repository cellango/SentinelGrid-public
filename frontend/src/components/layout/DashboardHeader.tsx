'use client';

import { useAuth } from '@/lib/providers/AuthProvider';
import { usePartnerTenantContext } from '@/lib/partner/tenantContext';
import { usePathname, useRouter } from 'next/navigation';
import { useTheme } from '@/lib/providers/ThemeProvider';
import { useState, useRef, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { getOnboardingStatus } from '@/lib/api/onboarding';
import { playbooksApi } from '@/lib/api/playbooks';
import { firstIncompleteIndex, normalizeOnboardingSteps } from '@/lib/onboarding/steps';
import { openCommandPalette } from '@/lib/command-palette';
import { Bars3Icon, MagnifyingGlassIcon } from '@heroicons/react/24/outline';

interface DashboardHeaderProps {
  onMobileMenuToggle?: () => void;
}

type WorkflowLabel = 'Detect' | 'Respond' | 'Govern' | 'Admin' | 'Setup';

type PageMeta = {
  workflow: WorkflowLabel;
  title: string;
  subtitle: string;
};

type PageRoute = {
  match: RegExp;
} & PageMeta;

const PAGE_ROUTES: PageRoute[] = [
  {
    match: /^\/dashboard\/now(?:\/|$)/,
    workflow: 'Detect',
    title: 'Now',
    subtitle: 'One prioritized queue across alerts, incidents, telemetry, identity, cloud, and AI work.',
  },
  {
    match: /^\/dashboard$/,
    workflow: 'Setup',
    title: 'Workspace Routing',
    subtitle: 'Choose the landing view that best matches the role you play in SentinelGrid.',
  },
  {
    match: /^\/dashboard\/alerts\/[^/]+/,
    workflow: 'Detect',
    title: 'Alert Investigation',
    subtitle: 'Review evidence, signal quality, and the next action before the alert becomes a broader case.',
  },
  {
    match: /^\/dashboard\/alerts/,
    workflow: 'Detect',
    title: 'Alert Queue',
    subtitle: 'Triage detections, confirm relevance, and escalate only the work that deserves operator attention.',
  },
  {
    match: /^\/dashboard\/incidents\/[^/]+/,
    workflow: 'Detect',
    title: 'Incident Detail',
    subtitle: 'Track owners, evidence, and downstream handoff from a single case workspace.',
  },
  {
    match: /^\/dashboard\/incidents/,
    workflow: 'Detect',
    title: 'Incident Queue',
    subtitle: 'Monitor active cases, assignees, and escalations without leaving the main queue.',
  },
  {
    match: /^\/dashboard\/security-graph/,
    workflow: 'Detect',
    title: 'Security Graph',
    subtitle: 'Pivot through entity relationships and blast radius without context switching.',
  },
  {
    match: /^\/dashboard\/log-management/,
    workflow: 'Detect',
    title: 'Telemetry Search',
    subtitle: 'Search telemetry, validate detections, and trace suspicious activity across your environment.',
  },
  {
    match: /^\/dashboard\/siem/,
    workflow: 'Detect',
    title: 'Detection Coverage',
    subtitle: 'Tune detections and response triggers for the work that matters most.',
  },
  {
    match: /^\/dashboard\/iam\/security-events/,
    workflow: 'Detect',
    title: 'Identity Events',
    subtitle: 'Investigate identity-centric activity alongside the rest of your security queue.',
  },
  {
    match: /^\/dashboard\/scans/,
    workflow: 'Detect',
    title: 'Exposure Scans',
    subtitle: 'Review exposure findings, scan drift, and validation results in one place.',
  },
  {
    match: /^\/dashboard\/penetration-testing/,
    workflow: 'Detect',
    title: 'Pen Tests',
    subtitle: 'This route stays outside the self-serve launch until the delivery workflow, evidence handling, and approvals are fully productized.',
  },
  {
    match: /^\/dashboard\/ai-security\/events/,
    workflow: 'Detect',
    title: 'AI Events',
    subtitle: 'This dedicated AI event log stays gated until runtime event APIs are exposed through the main launch path.',
  },
  {
    match: /^\/dashboard\/ai-security\/alerts/,
    workflow: 'Detect',
    title: 'AI Alerts',
    subtitle: 'AI-originated detections belong in the shared alert and incident queues for launch.',
  },
  {
    match: /^\/dashboard\/war-room/,
    workflow: 'Respond',
    title: 'War Room',
    subtitle: 'Coordinate the active response, shared timeline, and team handoffs from one space.',
  },
  {
    match: /^\/dashboard\/playbooks/,
    workflow: 'Respond',
    title: 'Response Playbooks',
    subtitle: 'Run repeatable response packs, approvals, and automated follow-through.',
  },
  {
    match: /^\/dashboard\/iam\/people/,
    workflow: 'Respond',
    title: 'People & Access',
    subtitle: 'Review identities, apps, and access relationships that create operator work.',
  },
  {
    match: /^\/dashboard\/iam\/privileged-access/,
    workflow: 'Respond',
    title: 'Privileged Access',
    subtitle: 'Control elevated access, privileged sessions, and the highest-impact identities.',
  },
  {
    match: /^\/dashboard\/iam\/access-reviews/,
    workflow: 'Respond',
    title: 'Access Reviews',
    subtitle: 'Run attestations and close the highest-risk review gaps first.',
  },
  {
    match: /^\/dashboard\/iam\/my-account/,
    workflow: 'Respond',
    title: 'My Account',
    subtitle: 'Review your profile, sign-in posture, and personal security settings.',
  },
  {
    match: /^\/dashboard\/iam\/my-access/,
    workflow: 'Respond',
    title: 'My Access',
    subtitle: 'See what you can access and request the changes you need.',
  },
  {
    match: /^\/dashboard\/iam\/apps/,
    workflow: 'Respond',
    title: 'App Access',
    subtitle: 'Review connected apps, profiles, and access coverage tied to your workforce.',
  },
  {
    match: /^\/dashboard\/iam\/devices/,
    workflow: 'Respond',
    title: 'Device Trust',
    subtitle: 'Check workforce devices and the trust signals attached to them.',
  },
  {
    match: /^\/dashboard\/iam\/policies/,
    workflow: 'Respond',
    title: 'Access Policies',
    subtitle: 'Shape the policies and approvals that govern access decisions.',
  },
  {
    match: /^\/dashboard\/iam\/chat/,
    workflow: 'Respond',
    title: 'Identity Assistant',
    subtitle: 'Work through identity questions and follow-up actions without leaving the dashboard.',
  },
  {
    match: /^\/dashboard\/iam\/api-keys/,
    workflow: 'Respond',
    title: 'API Keys',
    subtitle: 'Review API credentials, reduce key sprawl, and respond to risky exposure.',
  },
  {
    match: /^\/dashboard\/iam\/certificates/,
    workflow: 'Respond',
    title: 'Certificates',
    subtitle: 'Track certificate inventory, enrollment, and trust state across the fleet.',
  },
  {
    match: /^\/dashboard\/iam/,
    workflow: 'Respond',
    title: 'Identity Operations',
    subtitle: 'Identity work tied directly to operator outcomes instead of a separate admin silo.',
  },
  {
    match: /^\/dashboard\/posture/,
    workflow: 'Govern',
    title: 'Cloud Posture',
    subtitle: 'Prioritize posture gaps and drive the fixes that reduce cloud risk fastest.',
  },
  {
    match: /^\/dashboard\/compliance\/reports/,
    workflow: 'Govern',
    title: 'Reports',
    subtitle: 'Turn work already done in SentinelGrid into customer-facing proof and reporting.',
  },
  {
    match: /^\/dashboard\/compliance\/ai-activity/,
    workflow: 'Govern',
    title: 'AI Activity',
    subtitle: 'Review AI usage evidence and policy-relevant activity in one place.',
  },
  {
    match: /^\/dashboard\/compliance/,
    workflow: 'Govern',
    title: 'Compliance',
    subtitle: 'Translate operational work into controls evidence and reporting readiness.',
  },
  {
    match: /^\/dashboard\/iam\/reports/,
    workflow: 'Govern',
    title: 'IAM Reports',
    subtitle: 'Package identity evidence into audit-ready reporting for internal and external reviewers.',
  },
  {
    match: /^\/dashboard\/ai-governance/,
    workflow: 'Govern',
    title: 'AI Governance',
    subtitle: 'Translate AI activity, AI Shield findings, and governance pressure into leadership-ready reporting.',
  },
  {
    match: /^\/dashboard\/ai-security\/apps/,
    workflow: 'Govern',
    title: 'AI Apps',
    subtitle: 'This self-serve registry remains gated until tenant-scoped AI app management is exposed through the main product path.',
  },
  {
    match: /^\/dashboard\/ai-security\/policies/,
    workflow: 'Govern',
    title: 'AI Guardrails',
    subtitle: 'This authoring surface remains gated until AI policy storage and runtime enforcement are unified behind the launch path.',
  },
  {
    match: /^\/dashboard\/ai-security\/setup/,
    workflow: 'Govern',
    title: 'AI Shield Setup',
    subtitle: 'Connect runtime AI telemetry and review the findings in the shared operator and governance surfaces.',
  },
  {
    match: /^\/dashboard\/ai-security\/chat/,
    workflow: 'Govern',
    title: 'AI Security Assistant',
    subtitle: 'This assistant remains gated until it is backed by real tenant data and observable execution.',
  },
  {
    match: /^\/dashboard\/ai-security/,
    workflow: 'Govern',
    title: 'AI Security',
    subtitle: 'AI Shield launch support centers on truthful runtime ingestion into the main queue and governance views.',
  },
  {
    match: /^\/dashboard\/partner/,
    workflow: 'Admin',
    title: 'Partner Workflows',
    subtitle: 'This route stays outside the default self-serve launch and requires explicit qualification.',
  },
  {
    match: /^\/dashboard\/operations\/marketing-funnel/,
    workflow: 'Admin',
    title: 'Revenue & Activation',
    subtitle: 'Track the commercial and activation pipeline behind the product.',
  },
  {
    match: /^\/dashboard\/operations/,
    workflow: 'Admin',
    title: 'Platform Operations',
    subtitle: 'Internal-only route. It remains outside the customer-facing launch surface until production-backed analytics replace placeholder metrics.',
  },
  {
    match: /^\/dashboard\/settings(?:\/|$)/,
    workflow: 'Admin',
    title: 'Usage & Billing',
    subtitle: 'Review tenant usage, billing signals, and the settings surfaces tied to your subscription.',
  },
  {
    match: /^\/dashboard\/welcome/,
    workflow: 'Setup',
    title: 'First Week',
    subtitle: 'Get to first value fast and finish the remaining setup work that matters.',
  },
];

const DEFAULT_PAGE_META: PageMeta = {
  workflow: 'Detect',
  title: 'Now',
  subtitle: '',
};

function getPageMeta(path: string | null): PageMeta {
  if (!path) {
    return DEFAULT_PAGE_META;
  }

  const matchedRoute = PAGE_ROUTES.find((route) => route.match.test(path));
  if (matchedRoute) {
    return matchedRoute;
  }

  if (path.startsWith('/dashboard/')) {
    return {
      workflow: 'Detect',
      title: 'Operator Plane',
      subtitle: 'Move between detection, response, and governance work from one shared control surface.',
    };
  }

  return DEFAULT_PAGE_META;
}

export default function DashboardHeader({ onMobileMenuToggle }: DashboardHeaderProps) {
  const { user, logout } = useAuth();
  const { activeTenant, isInPartnerTenantContext, clearTenantContext } = usePartnerTenantContext();
  const router = useRouter();
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const [approvalsCount, setApprovalsCount] = useState<number>(0);
  const [configLink, setConfigLink] = useState<string>('/onboarding');
  const userRoles = user?.roles || [];
  const roleLabel = userRoles.length > 0 ? userRoles.join(', ') : 'No roles assigned';

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

  // Keyboard navigation for user menu dropdown
  const handleMenuKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setShowUserMenu(false);
      menuButtonRef.current?.focus();
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const items = menuRef.current?.querySelectorAll<HTMLElement>('a, button[role="menuitem"]');
      if (!items?.length) return;
      const currentIdx = Array.from(items).indexOf(document.activeElement as HTMLElement);
      const nextIdx = e.key === 'ArrowDown'
        ? Math.min(currentIdx + 1, items.length - 1)
        : Math.max(currentIdx - 1, 0);
      items[nextIdx]?.focus();
    }
  }, []);

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
  const pageMeta = getPageMeta(pathname);
  const partnerDeliveryModeLabel = activeTenant
    ? activeTenant.deliveryMode.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
    : null;
  const partnerContextEnteredLabel = activeTenant
    ? new Date(activeTenant.enteredAt).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
    : null;

  const handleExitTenantContext = () => {
    clearTenantContext();
    router.push('/dashboard/now');
  };

  useEffect(() => {
    let isMounted = true;

    const loadApprovalsCount = async () => {
      try {
        const pendingApprovals = await playbooksApi.listExecutions({
          status: 'pending',
          approval_status: 'pending',
          limit: 25,
        });
        if (isMounted) {
          setApprovalsCount(pendingApprovals.length);
        }
      } catch {
        if (isMounted) {
          setApprovalsCount(0);
        }
      }
    };

    void loadApprovalsCount();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    // Precompute configuration link to resume onboarding/config steps
    const loadStatus = async () => {
      try {
        const status = await getOnboardingStatus();
        const steps = normalizeOnboardingSteps(status);
        if (steps.length > 0) {
          const idx = firstIncompleteIndex(steps);
          setConfigLink(`/onboarding?step=${idx + 1}`);
          return;
        }
        setConfigLink('/onboarding');
      } catch (e) {
        setConfigLink('/onboarding');
      }
    };
    loadStatus();
  }, []);

  const workspaceMenuLinks = [
    {
      href: configLink,
      label: 'Resume Setup',
    },
    {
      href: 'mailto:support@sentinelgrid.ai',
      label: 'Help',
    },
    {
      href: '/dashboard/settings/usage',
      label: 'Usage & Billing',
    },
  ];

  const searchShortcutLabel = 'Cmd/Ctrl+K';

  return (
    <header className="sticky top-0 z-30 border-b border-surface-card bg-surface-card-border">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-3">
          {/* Mobile hamburger menu button */}
          <button
            onClick={onMobileMenuToggle}
            className="lg:hidden min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-text-muted hover:text-text-main transition-colors"
            aria-label="Open navigation menu"
          >
            <Bars3Icon className="w-6 h-6" />
          </button>

          <Link href="/dashboard">
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="hidden rounded-full border border-border-faint bg-surface-hover px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-text-muted md:inline-flex">
                  {pageMeta.workflow}
                </span>
                <h1 className="text-lg font-semibold leading-tight text-text-main">{pageMeta.title}</h1>
              </div>
              {pageMeta.subtitle && <p className="hidden text-[13px] leading-tight text-text-muted sm:block">{pageMeta.subtitle}</p>}
            </div>
          </Link>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          {/* Search bar - hidden on small screens */}
          <button
            type="button"
            onClick={() => openCommandPalette({ source: 'header-search' })}
            className="hidden min-h-[44px] min-w-[320px] items-center justify-between gap-3 rounded-lg border border-border-faint bg-surface-hover px-3 py-2.5 text-left transition-colors hover:border-primary lg:inline-flex"
            aria-label="Open universal search"
          >
            <span className="flex items-center gap-2">
              <MagnifyingGlassIcon className="h-4 w-4 text-text-muted" aria-hidden="true" />
              <span className="text-sm text-text-muted">Search alerts, incidents, rules, people, policies, and reports</span>
            </span>
            <span className="rounded border border-border-faint px-1.5 py-0.5 text-[10px] font-mono text-text-muted">
              {searchShortcutLabel}
            </span>
          </button>

          {/* Approvals link */}
          <Link
            href="/dashboard/playbooks/executions?status=pending&approval_status=pending"
            className="relative inline-flex min-h-[44px] items-center gap-2 rounded-lg border border-border-faint bg-surface-hover px-3 py-2.5 text-sm text-text-main transition-colors hover:border-primary"
            title="Approvals queue"
            aria-label={`Approvals queue, ${approvalsCount} pending`}
          >
            <span className="hidden sm:inline">Approvals</span>
            {approvalsCount > 0 && (
              <span className="inline-flex h-6 min-w-[24px] items-center justify-center rounded-full bg-primary text-slate-950 text-xs font-semibold px-2" aria-hidden="true">
                {approvalsCount}
              </span>
            )}
          </Link>

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            className="hidden sm:inline-flex items-center gap-2 px-3 py-2.5 min-h-[44px] rounded-lg border border-border-muted text-text-main text-sm hover:border-primary transition-colors"
            aria-label={`Switch theme, currently ${theme}`}
          >
            <span className="inline-block h-2 w-2 rounded-full bg-primary" aria-hidden="true" />
            {theme === 'dark' ? 'Dark' : theme === 'light' ? 'Light' : 'System'}
          </button>

          {/* User menu */}
          {user && (
            <div className="relative" ref={menuRef} onKeyDown={handleMenuKeyDown}>
              <button
                ref={menuButtonRef}
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 sm:gap-3 px-2 sm:px-3 py-2 min-h-[44px] rounded-lg border border-border-strong bg-transparent hover:border-primary transition-colors"
                aria-expanded={showUserMenu}
                aria-haspopup="menu"
                aria-label={`User menu for ${user.email}`}
              >
                <div className="w-9 h-9 rounded-full bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center text-slate-950 text-sm font-semibold" aria-hidden="true">
                  {getInitials(user.email)}
                </div>
                <div className="text-right hidden md:block">
                  <p className="text-sm font-medium text-text-main">{user.email}</p>
                  <p className="text-xs text-text-muted">{roleLabel}</p>
                </div>
              </button>

              {showUserMenu && (
                <div
                  className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-border-strong bg-surface-card py-2 shadow-xl"
                  role="menu"
                  aria-label="User menu"
                >
                  <div className="border-b border-border-faint px-4 py-3">
                    <p className="text-sm font-medium text-text-main">{user.email}</p>
                    <p className="mt-1 text-xs text-text-muted">
                      {roleLabel}
                    </p>
                  </div>
                  <div className="px-4 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-[0.08em] text-text-muted">
                    Workspace
                  </div>
                  {workspaceMenuLinks.map((link) => (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setShowUserMenu(false)}
                      className="flex min-h-[44px] items-center px-4 py-2.5 text-sm text-text-main transition-colors hover:bg-surface-hover"
                      role="menuitem"
                      aria-current={pathname === link.href ? 'page' : undefined}
                    >
                      {link.label}
                    </Link>
                  ))}
                  <div className="my-2 border-t border-border-faint" />
                  <button
                    onClick={handleLogout}
                    className="flex min-h-[44px] w-full items-center px-4 py-2.5 text-left text-sm text-text-main transition-colors hover:bg-surface-hover"
                    role="menuitem"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {isInPartnerTenantContext && activeTenant && (
        <div className="border-t border-primary/20 bg-primary/10 px-4 py-3 sm:px-6">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                Managed Tenant Context Active
              </p>
              <p className="mt-1 text-sm font-medium text-text-main">
                {activeTenant.tenantName} is the active client scope for this session.
              </p>
              <p className="mt-1 text-xs text-text-muted">
                Delivery mode: {partnerDeliveryModeLabel} · Approval policy: {activeTenant.approvalMode} · Entered {partnerContextEnteredLabel}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={handleExitTenantContext}
                className="inline-flex min-h-[40px] items-center rounded-lg bg-primary px-3 py-2 text-sm font-medium text-slate-950 transition-all hover:brightness-110"
              >
                Exit Tenant Context
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
