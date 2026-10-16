'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import {
  HomeIcon,
  BellAlertIcon,
  ShieldExclamationIcon,
  SparklesIcon,
  EllipsisHorizontalIcon,
} from '@heroicons/react/24/outline';
import { openCommandPalette } from '@/lib/command-palette';

interface MobileBottomNavProps {
  onMore: () => void;
}

const ITEMS = [
  {
    id: 'now',
    label: 'Dashboard',
    href: '/dashboard/now',
    icon: HomeIcon,
    matches: ['/dashboard/now'],
  },
  {
    id: 'alerts',
    label: 'Alerts',
    href: '/dashboard/alerts',
    icon: BellAlertIcon,
    matches: ['/dashboard/alerts'],
  },
  {
    id: 'incidents',
    label: 'Incidents',
    href: '/dashboard/incidents',
    icon: ShieldExclamationIcon,
    matches: ['/dashboard/incidents'],
  },
];

function matchesPath(pathname: string | null, prefixes: string[]) {
  if (!pathname) return false;
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export default function MobileBottomNav({ onMore }: MobileBottomNavProps) {
  const pathname = usePathname();

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border-faint bg-surface-card/95 px-2 pb-[calc(env(safe-area-inset-bottom)+0.5rem)] pt-2 backdrop-blur-md lg:hidden"
      aria-label="Mobile navigation"
    >
      <div className="grid grid-cols-5 gap-1">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const active = matchesPath(pathname, item.matches);
          return (
            <Link
              key={item.id}
              href={item.href}
              className={clsx(
                'flex min-h-[56px] flex-col items-center justify-center rounded-xl px-2 py-2 text-[11px] font-medium transition-colors',
                active
                  ? 'bg-primary/15 text-primary'
                  : 'text-text-muted hover:bg-surface-hover hover:text-text-main'
              )}
              aria-current={active ? 'page' : undefined}
            >
              <Icon className="mb-1 h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => openCommandPalette({ source: 'mobile-bottom-nav' })}
          className="flex min-h-[56px] flex-col items-center justify-center rounded-xl px-2 py-2 text-[11px] font-medium text-text-muted transition-colors hover:bg-surface-hover hover:text-text-main"
          aria-label="Open AI search"
        >
          <SparklesIcon className="mb-1 h-5 w-5" />
          <span>AI Chat</span>
        </button>
        <button
          type="button"
          onClick={onMore}
          className="flex min-h-[56px] flex-col items-center justify-center rounded-xl px-2 py-2 text-[11px] font-medium text-text-muted transition-colors hover:bg-surface-hover hover:text-text-main"
          aria-label="Open more navigation"
        >
          <EllipsisHorizontalIcon className="mb-1 h-5 w-5" />
          <span>More</span>
        </button>
      </div>
    </nav>
  );
}
