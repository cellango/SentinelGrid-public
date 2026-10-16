/**
 * IAM Portal Layout
 * Provides navigation for IAM portal pages
 */

'use client';

import Link from 'next/link';
import type { ComponentType, SVGProps } from 'react';
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent as ReactKeyboardEvent } from 'react';
import { usePathname } from 'next/navigation';
import { clsx } from 'clsx';
import {
  UserIcon,
  KeyIcon,
  Cog6ToothIcon,
  ClipboardDocumentCheckIcon,
  UserCircleIcon,
  DevicePhoneMobileIcon,
  ShieldExclamationIcon,
  DocumentChartBarIcon,
  ShieldCheckIcon,
  LockClosedIcon,
  DocumentTextIcon,
  ScaleIcon,
} from '@heroicons/react/24/outline';

type WidthPreset = {
  id: string;
  label: string;
  shortLabel: string;
  width: number;
};

type NavItem = {
  name: string;
  href: string;
  icon?: ComponentType<SVGProps<SVGSVGElement>> | null;
};

type NavGroup = {
  label: string;
  items: NavItem[];
};

const iamNavGroups: NavGroup[] = [
  {
    label: 'Me',
    items: [
      { name: 'My Account', href: '/dashboard/iam/my-account', icon: UserCircleIcon },
      { name: 'My Access', href: '/dashboard/iam/my-access', icon: KeyIcon },
      { name: 'My Devices', href: '/dashboard/iam/my-devices', icon: DevicePhoneMobileIcon },
    ],
  },
  {
    label: 'People & Teams',
    items: [
      { name: 'People', href: '/dashboard/iam/people', icon: UserIcon },
    ],
  },
  {
    label: 'Apps & Policies',
    items: [
      { name: 'Apps & Profiles', href: '/dashboard/iam/apps', icon: Cog6ToothIcon },
      { name: 'Birthrights', href: '/dashboard/iam/birthrights', icon: ShieldCheckIcon },
      { name: 'API Keys', href: '/dashboard/iam/api-keys', icon: KeyIcon },
      { name: 'Certificates', href: '/dashboard/iam/certificates', icon: DocumentTextIcon },
      { name: 'Policies', href: '/dashboard/iam/policies', icon: ScaleIcon },
      { name: 'Secrets', href: '/dashboard/iam/secrets', icon: LockClosedIcon },
    ],
  },
];

const IAM_NAV_WIDTH_PRESETS: WidthPreset[] = [
  { id: 'compact', label: 'Compact', shortLabel: 'C', width: 220 },
  { id: 'comfortable', label: 'Comfort', shortLabel: 'M', width: 260 },
  { id: 'wide', label: 'Wide', shortLabel: 'W', width: 320 },
];

export default function IAMLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const minNavWidth = 180;
  const maxNavWidth = 360;
  const collapsedNavWidth = 88;
  const clampNavWidth = (width: number) => Math.min(maxNavWidth, Math.max(minNavWidth, width));
  const [navWidth, setNavWidth] = useState<number>(() => {
    if (typeof window === 'undefined') return 240;
    const stored = window.localStorage.getItem('sg_iam_nav_width');
    return stored ? clampNavWidth(parseInt(stored, 10)) : 240;
  });
  const [navCollapsed, setNavCollapsed] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem('sg_iam_nav_collapsed') === 'true';
  });
  const [dragging, setDragging] = useState<boolean>(false);
  const effectiveNavWidth = navCollapsed ? collapsedNavWidth : navWidth;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('sg_iam_nav_width', String(navWidth));
  }, [navWidth]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem('sg_iam_nav_collapsed', String(navCollapsed));
  }, [navCollapsed]);

  useEffect(() => {
    const handleMove = (e: MouseEvent) => {
      if (!dragging || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const raw = e.clientX - rect.left;
      const clamped = clampNavWidth(raw);
      setNavWidth(clamped);
      e.preventDefault();
    };
    const handleUp = () => setDragging(false);
    if (dragging) {
      window.addEventListener('mousemove', handleMove);
      window.addEventListener('mouseup', handleUp);
    }
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [dragging]);

  const handlePresetSelect = (width: number) => {
    setNavCollapsed(false);
    setNavWidth(width);
  };

  const toggleNavCollapsed = () => {
    setNavCollapsed((current) => !current);
  };

  const startDragging = () => {
    if (navCollapsed) {
      setNavCollapsed(false);
      setNavWidth(IAM_NAV_WIDTH_PRESETS[0].width);
    }
    setDragging(true);
  };

  const handleResizeKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 32 : 16;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleNavCollapsed();
      return;
    }
    if (event.key === 'Home') {
      event.preventDefault();
      handlePresetSelect(minNavWidth);
      return;
    }
    if (event.key === 'End') {
      event.preventDefault();
      handlePresetSelect(maxNavWidth);
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      handlePresetSelect(clampNavWidth(navWidth - step));
      return;
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      handlePresetSelect(clampNavWidth(navWidth + step));
    }
  };

  return (
    <div
      ref={containerRef}
      className="flex h-full bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 select-none md:select-auto"
    >
      {/* Sidebar */}
      <aside
        className="hidden md:flex flex-shrink-0 flex-col border-r border-slate-200 dark:border-slate-800 bg-surface-card"
        style={{ width: effectiveNavWidth, minWidth: effectiveNavWidth, maxWidth: effectiveNavWidth }}
      >
        <div className="px-4 py-4">
          <div className={clsx('flex items-center', navCollapsed ? 'justify-center' : 'justify-between gap-3')}>
            {!navCollapsed ? (
              <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">IAM Portal</h2>
            ) : (
              <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">IAM</span>
            )}
          </div>
          <div className={clsx('mt-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-100/80 dark:bg-slate-950/60', navCollapsed ? 'p-2 space-y-2' : 'p-3 space-y-2')}>
            <button
              type="button"
              onClick={toggleNavCollapsed}
              aria-pressed={navCollapsed}
              className="w-full min-h-[40px] rounded-lg border border-slate-200 bg-surface-card text-xs font-medium text-slate-700 transition-colors hover:border-blue-300 hover:text-blue-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-blue-700 dark:hover:text-blue-200"
            >
              {navCollapsed ? 'Open' : 'Hide'}
            </button>
            <div className={clsx('grid gap-1', navCollapsed ? 'grid-cols-1' : 'grid-cols-3')}>
              {IAM_NAV_WIDTH_PRESETS.map((preset) => {
                const isActive = !navCollapsed && navWidth === preset.width;
                return (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handlePresetSelect(preset.width)}
                    aria-label={`${preset.label} IAM navigation width`}
                    aria-pressed={isActive}
                    title={`${preset.label} width`}
                    className={clsx(
                      'min-h-[40px] rounded-lg border text-xs font-medium transition-colors',
                      isActive
                        ? 'border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-blue-900/40 dark:text-blue-100'
                        : 'border-slate-200 bg-surface-card text-slate-600 hover:border-blue-200 hover:text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-blue-800 dark:hover:text-slate-100'
                    )}
                  >
                    {navCollapsed ? preset.shortLabel : preset.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 pb-4">
          {iamNavGroups.map((group, index) => (
            <div key={group.label} className={clsx('mb-4', navCollapsed && index > 0 && 'pt-3 border-t border-slate-200 dark:border-slate-800')}>
              <p className={clsx('px-3 mb-2 text-xs font-semibold text-slate-500 dark:text-slate-300', navCollapsed && 'sr-only')}>{group.label}</p>
              <div className="space-y-1">
                {group.items.map((item) => {
                  const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      aria-label={navCollapsed ? item.name : undefined}
                      title={navCollapsed ? item.name : undefined}
                      className={clsx(
                        'flex items-center rounded-lg py-2 text-sm font-medium transition-colors min-h-[44px]',
                        navCollapsed ? 'justify-center px-0' : 'gap-3 px-3',
                        isActive
                          ? 'bg-blue-50 text-blue-700 border border-blue-100 dark:bg-blue-900/40 dark:text-blue-100 dark:border-blue-800'
                          : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
                      )}
                    >
                      {Icon && <Icon className="w-5 h-5" />}
                      {navCollapsed ? <span className="sr-only">{item.name}</span> : <span>{item.name}</span>}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      {/* Resize handle (desktop only) */}
      <div
        className="hidden md:block w-1 cursor-col-resize bg-transparent hover:bg-blue-200/60 dark:hover:bg-blue-900/40 transition-colors"
        onMouseDown={startDragging}
        onKeyDown={handleResizeKeyDown}
        role="separator"
        aria-label="Resize navigation pane"
        aria-orientation="vertical"
        aria-valuemin={collapsedNavWidth}
        aria-valuemax={maxNavWidth}
        aria-valuenow={effectiveNavWidth}
        tabIndex={0}
      />

      {/* Mobile nav hint (kept minimal to avoid horizontal scroll) */}
      <div className="md:hidden border-b border-slate-200 bg-surface-card px-4 py-3 text-sm text-slate-700">
        Use the IAM menu from the main dashboard nav to switch sections.
      </div>

      {/* Page Content */}
      <div className="flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  );
}
