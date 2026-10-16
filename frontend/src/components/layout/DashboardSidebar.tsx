'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import type { ComponentType, SVGProps } from 'react';
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent, MouseEvent as ReactMouseEvent } from 'react';
import {
  HomeIcon,
  ShieldExclamationIcon,
  BellAlertIcon,
  UserGroupIcon,
  ExclamationCircleIcon,
  SparklesIcon,
  DocumentTextIcon,
  ArchiveBoxIcon,
  ClipboardDocumentCheckIcon,
  ShieldCheckIcon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/lib/providers/AuthProvider';
import { getPlanTierRank, type PlanTier } from '@/lib/product/catalog';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

type NavItem = {
  id: string;
  name: string;
  href: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  adminOnly?: boolean;
  minPlanTier?: PlanTier;
  matchPrefixes?: string[];
};

type NavSection = {
  id: string;
  title: string;
  items: NavItem[];
};

type WidthPreset = {
  id: string;
  label: string;
  shortLabel: string;
  width: number;
};

const SIDEBAR_WIDTH_PRESETS: WidthPreset[] = [
  { id: 'compact', label: 'Compact', shortLabel: 'C', width: 224 },
  { id: 'comfortable', label: 'Comfort', shortLabel: 'M', width: 256 },
  { id: 'wide', label: 'Wide', shortLabel: 'W', width: 304 },
];

const navSections: NavSection[] = [
  {
    id: 'detect',
    title: 'Detect',
    items: [
      { id: 'now', name: 'Now', href: '/dashboard/now', icon: HomeIcon, matchPrefixes: ['/dashboard/now'] },
      { id: 'alerts', name: 'Alert Queue', href: '/dashboard/alerts', icon: BellAlertIcon },
      { id: 'incidents', name: 'Incident Queue', href: '/dashboard/incidents', icon: ShieldExclamationIcon },
      { id: 'security-graph', name: 'Security Graph', href: '/dashboard/security-graph', icon: ShieldCheckIcon },
      { id: 'telemetry-search', name: 'Telemetry Search', href: '/dashboard/log-management', icon: ExclamationCircleIcon },
      { id: 'detection-rules', name: 'Detection Coverage', href: '/dashboard/siem/detection-rules', icon: ShieldExclamationIcon, minPlanTier: 'protect_defend', matchPrefixes: ['/dashboard/siem'] },
      { id: 'identity-events', name: 'Identity Events', href: '/dashboard/iam/security-events', icon: ShieldExclamationIcon, minPlanTier: 'protect_defend_comply' },
      { id: 'scans', name: 'Exposure Scans', href: '/dashboard/scans', icon: ExclamationCircleIcon },
    ],
  },
  {
    id: 'respond',
    title: 'Respond',
    items: [
      { id: 'war-room', name: 'War Room', href: '/dashboard/war-room', icon: ExclamationCircleIcon },
      { id: 'response-playbooks', name: 'Response Playbooks', href: '/dashboard/playbooks', icon: SparklesIcon, minPlanTier: 'protect_defend' },
      { id: 'people-access', name: 'People & Access', href: '/dashboard/iam/people', icon: UserGroupIcon, matchPrefixes: ['/dashboard/iam/people', '/dashboard/iam'] },
      { id: 'privileged-access', name: 'Privileged Access', href: '/dashboard/iam/privileged-access', icon: ShieldCheckIcon, minPlanTier: 'protect_defend_comply' },
      { id: 'access-reviews', name: 'Access Reviews', href: '/dashboard/iam/access-reviews', icon: ClipboardDocumentCheckIcon, minPlanTier: 'protect_defend_comply' },
    ],
  },
  {
    id: 'govern',
    title: 'Govern',
    items: [
      { id: 'posture', name: 'Cloud Posture', href: '/dashboard/posture', icon: ShieldCheckIcon },
      { id: 'compliance', name: 'Compliance', href: '/dashboard/compliance', icon: ShieldExclamationIcon, minPlanTier: 'protect_defend_comply', matchPrefixes: ['/dashboard/compliance'] },
      { id: 'evidence-center', name: 'Evidence Center', href: '/dashboard/compliance/evidence', icon: ArchiveBoxIcon, minPlanTier: 'protect_defend_comply' },
      { id: 'reports', name: 'Reports', href: '/dashboard/compliance/reports', icon: DocumentTextIcon, minPlanTier: 'protect_defend_comply' },
      { id: 'ai-activity', name: 'AI Activity', href: '/dashboard/compliance/ai-activity', icon: SparklesIcon, minPlanTier: 'protect_defend_comply' },
      { id: 'ai-governance', name: 'AI Governance', href: '/dashboard/ai-governance', icon: SparklesIcon, minPlanTier: 'protect_defend_comply' },
    ],
  },
];

interface DashboardSidebarProps {
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export default function DashboardSidebar({ mobileOpen, onMobileClose }: DashboardSidebarProps) {
  const pathname = usePathname();
  const { user, planTier } = useAuth();
  const [tierOverride, setTierOverride] = useState<string | null>(null);

  const effectivePlanTier =
    tierOverride ||
    (typeof window !== 'undefined' ? localStorage.getItem('plan_tier') : null) ||
    planTier;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setTierOverride(localStorage.getItem('plan_tier_override'));
  }, []);

  const minWidth = 200;
  const maxWidth = 320;
  const collapsedWidth = 88;
  const clampSidebarWidth = (width: number) => Math.min(maxWidth, Math.max(minWidth, width));
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return 224;
    const stored = window.localStorage.getItem('sg_dashboard_sidebar_width');
    return stored ? clampSidebarWidth(parseInt(stored, 10)) : 224;
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem('sg_dashboard_sidebar_collapsed') === 'true';
  });
  const [resizing, setResizing] = useState(false);
  const startX = useRef(0);
  const startWidth = useRef(sidebarWidth);

  const hasAdminRole = (() => {
    const roles = user?.roles || [];
    return roles.some((r) =>
      ['admin', 'tenant_admin', 'TENANT_ADMIN', 'soc_manager', 'SOC_MANAGER'].includes(r)
    );
  })();

  const currentPlanRank = getPlanTierRank(effectivePlanTier || 'protect');

  const visibleSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => {
        if (item.adminOnly && !hasAdminRole) {
          return false;
        }
        if (!item.minPlanTier) {
          return true;
        }
        return currentPlanRank >= getPlanTierRank(item.minPlanTier);
      }),
    }))
    .filter((section) => section.items.length > 0);

  const matchPath = (path: string | null, prefix: string) => {
    if (!path) return false;
    if (prefix === '/dashboard') {
      return path === prefix;
    }
    return path === prefix || path.startsWith(prefix + '/');
  };

  const activeItemId = visibleSections
    .flatMap((section) =>
      section.items.map((item) => ({
        item,
        matchers: item.matchPrefixes || [item.href],
      }))
    )
    .sort((left, right) => {
      const leftLongest = Math.max(...left.matchers.map((matcher) => matcher.length));
      const rightLongest = Math.max(...right.matchers.map((matcher) => matcher.length));
      return rightLongest - leftLongest;
    })
    .find(({ matchers }) => matchers.some((matcher) => matchPath(pathname, matcher)))
    ?.item.id;

  useEffect(() => {
    if (!resizing) return;
    const handleMove = (event: MouseEvent) => {
      const delta = event.clientX - startX.current;
      const nextWidth = clampSidebarWidth(startWidth.current + delta);
      setSidebarWidth(nextWidth);
    };
    const handleUp = () => setResizing(false);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [resizing]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('sg_dashboard_sidebar_width', String(sidebarWidth));
  }, [sidebarWidth]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('sg_dashboard_sidebar_collapsed', String(sidebarCollapsed));
  }, [sidebarCollapsed]);

  const startResize = (event: ReactMouseEvent<HTMLDivElement>) => {
    startX.current = event.clientX;
    if (sidebarCollapsed) {
      setSidebarCollapsed(false);
      setSidebarWidth(SIDEBAR_WIDTH_PRESETS[0].width);
      startWidth.current = SIDEBAR_WIDTH_PRESETS[0].width;
    } else {
      startWidth.current = sidebarWidth;
    }
    setResizing(true);
    event.preventDefault();
  };

  const handlePresetSelect = (width: number) => {
    setSidebarCollapsed(false);
    setSidebarWidth(width);
  };

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((current) => !current);
  };

  const handleResizeKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 32 : 16;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleSidebarCollapsed();
      return;
    }
    if (event.key === 'Home') {
      event.preventDefault();
      handlePresetSelect(minWidth);
      return;
    }
    if (event.key === 'End') {
      event.preventDefault();
      handlePresetSelect(maxWidth);
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      handlePresetSelect(clampSidebarWidth(sidebarWidth - step));
      return;
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      handlePresetSelect(clampSidebarWidth(sidebarWidth + step));
    }
  };

  // Close mobile sidebar on route change
  useEffect(() => {
    if (mobileOpen && onMobileClose) {
      onMobileClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // Trap focus in mobile drawer and handle Escape key
  const drawerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!mobileOpen) return;
    previousFocusRef.current = document.activeElement as HTMLElement;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onMobileClose) {
        onMobileClose();
        return;
      }
      if (e.key !== 'Tab' || !drawerRef.current) {
        return;
      }

      const focusable = drawerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (focusable.length === 0) {
        e.preventDefault();
        drawerRef.current.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    // Prevent body scroll when mobile drawer is open
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => {
      const focusable = drawerRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      focusable?.[0]?.focus();
    });
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
      previousFocusRef.current?.focus();
    };
  }, [mobileOpen, onMobileClose]);

  const renderNavContent = ({ collapsed = false, desktop = false }: { collapsed?: boolean; desktop?: boolean }) => (
    <div className={clsx(collapsed ? 'px-3 py-4' : 'p-5')}>
      <div className={clsx('flex items-center mb-6', collapsed ? 'justify-center' : 'justify-between')}>
        <div className={clsx('flex items-center gap-2.5', collapsed && 'justify-center')}>
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-secondary shadow-[0_0_25px_rgba(34,211,238,0.5)] relative">
            <div className="absolute inset-1 rounded-md border border-surface-card-border" />
          </div>
          {!collapsed && (
            <span className="font-semibold tracking-wide text-lg">
              Sentinel<span className="text-primary">Grid</span>
            </span>
          )}
        </div>
        {/* Mobile close button */}
        {!desktop && (
          <button
            onClick={onMobileClose}
            className="lg:hidden min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-text-muted hover:text-text-main transition-colors"
            aria-label="Close navigation menu"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        )}
      </div>

      {desktop && (
        <div
          className={clsx(
            'mb-6 rounded-xl border border-surface-card bg-bg/60',
            collapsed ? 'p-2 space-y-2' : 'p-3 space-y-2'
          )}
        >
          <button
            type="button"
            onClick={toggleSidebarCollapsed}
            aria-pressed={sidebarCollapsed}
            className={clsx(
              'w-full min-h-[40px] rounded-lg border border-surface-card-border bg-surface-card text-xs font-medium text-text-main transition-colors',
              'hover:border-primary/50 hover:text-primary'
            )}
          >
            {collapsed ? 'Open' : 'Hide'}
          </button>
          <div className={clsx('grid gap-1', collapsed ? 'grid-cols-1' : 'grid-cols-3')}>
            {SIDEBAR_WIDTH_PRESETS.map((preset) => {
              const isActive = !sidebarCollapsed && sidebarWidth === preset.width;
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => handlePresetSelect(preset.width)}
                  aria-label={`${preset.label} navigation width`}
                  aria-pressed={isActive}
                  title={`${preset.label} width`}
                  className={clsx(
                    'min-h-[40px] rounded-lg border text-xs font-medium transition-colors',
                    isActive
                      ? 'border-primary/60 bg-primary/15 text-primary'
                      : 'border-surface-card-border bg-surface-card text-text-muted hover:border-primary/40 hover:text-text-main'
                  )}
                >
                  {collapsed ? preset.shortLabel : preset.label}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <nav aria-label="Main navigation" className="space-y-4">
        {visibleSections.map((section, index) => (
          <div
            key={section.id}
            className={clsx('space-y-1', collapsed && index > 0 && 'pt-3 border-t border-surface-card')}
            data-section={section.id}
          >
            <div className={clsx('text-[11px] uppercase tracking-[0.08em] text-text-muted/70 px-3.5', collapsed && 'sr-only')}>
              {section.title}
            </div>
            {section.items.map((item) => {
              const isActive = activeItemId === item.id;
              const Icon = item.icon;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  aria-current={isActive ? 'page' : undefined}
                  data-nav-item={item.id}
                  aria-label={collapsed ? item.name : undefined}
                  title={collapsed ? item.name : undefined}
                  className={clsx(
                    'flex items-center py-2.5 text-sm font-medium rounded-lg transition-colors min-h-[44px]',
                    collapsed ? 'justify-center px-0' : 'px-3.5',
                    isActive
                      ? 'bg-primary/20 text-primary border border-primary/30'
                      : 'text-text-muted hover:text-text-main hover:bg-primary-ghost'
                  )}
                >
                  <Icon className={clsx('w-5 h-5 flex-shrink-0', !collapsed && 'mr-2.5')} />
                  {collapsed ? <span className="sr-only">{item.name}</span> : <span>{item.name}</span>}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </div>
  );

  const effectiveSidebarWidth = sidebarCollapsed ? collapsedWidth : sidebarWidth;

  return (
    <>
      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={onMobileClose}
          aria-hidden="true"
        />
      )}

      {/* Mobile drawer */}
      <div
        ref={drawerRef}
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-72 bg-surface-card-border transform transition-transform duration-200 ease-out lg:hidden overflow-y-auto',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        tabIndex={-1}
      >
        {renderNavContent({ collapsed: false, desktop: false })}
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:flex h-full">
        <aside
          className="bg-surface-card-border border-r border-surface-card min-h-screen"
          style={{
            width: `${effectiveSidebarWidth}px`,
            minWidth: `${effectiveSidebarWidth}px`,
            maxWidth: `${effectiveSidebarWidth}px`,
          }}
        >
          {renderNavContent({ collapsed: sidebarCollapsed, desktop: true })}
        </aside>
        <div
          onMouseDown={startResize}
          onKeyDown={handleResizeKeyDown}
          className={clsx(
            'group relative w-2 cursor-col-resize select-none transition-colors flex items-center justify-center',
            resizing ? 'bg-primary/20' : 'hover:bg-primary/10'
          )}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize main navigation"
          aria-valuemin={collapsedWidth}
          aria-valuemax={maxWidth}
          aria-valuenow={effectiveSidebarWidth}
          tabIndex={0}
          title="Drag to resize navigation"
        >
          <div className="h-12 w-[2px] rounded-full bg-primary/70 opacity-80 group-hover:opacity-100 transition-opacity shadow-[0_0_4px_rgba(34,211,238,0.35)]" />
        </div>
      </div>
    </>
  );
}

// Export the hamburger button for use in the header
export function MobileMenuButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="lg:hidden min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-text-muted hover:text-text-main transition-colors"
      aria-label="Open navigation menu"
    >
      <Bars3Icon className="w-6 h-6" />
    </button>
  );
}
