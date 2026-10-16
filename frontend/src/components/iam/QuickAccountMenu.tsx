/**
 * Quick Account Menu Component
 * Dropdown menu for quick access to self-service features from header
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  UserIcon,
  KeyIcon,
  DevicePhoneMobileIcon,
  ArrowRightOnRectangleIcon,
} from '@heroicons/react/24/outline';
import { useAuth } from '@/lib/providers/AuthProvider';

interface QuickAccountMenuProps {
  userEmail: string;
  onClose?: () => void;
}

export default function QuickAccountMenu({
  userEmail,
  onClose,
}: QuickAccountMenuProps) {
  const router = useRouter();
  const { logout } = useAuth();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
        onClose?.();
      }
    };

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu, onClose]);

  const handleLogout = () => {
    logout();
    setShowMenu(false);
    router.push('/');
  };

  const menuItems = [
    {
      icon: UserIcon,
      label: 'Profile',
      href: '/dashboard/iam/my-account?tab=profile',
    },
    {
      icon: KeyIcon,
      label: 'Security Settings',
      href: '/dashboard/iam/my-account?tab=security',
    },
    {
      icon: DevicePhoneMobileIcon,
      label: 'Active Sessions',
      href: '/dashboard/iam/my-account?tab=sessions',
    },
  ];

  return (
    <div className="relative" ref={menuRef}>
      <div className="px-4 py-3 border-b border-slate-800">
        <p className="text-sm font-medium text-text-main">{userEmail}</p>
        <p className="text-xs text-text-muted mt-1">Quick access</p>
      </div>
      <div className="py-2">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => {
                setShowMenu(false);
                onClose?.();
              }}
              className="flex items-center gap-3 px-4 py-2 text-sm text-text-main hover:bg-slate-800 transition-colors"
            >
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
        <Link
          href="/dashboard/iam/my-account"
          onClick={() => {
            setShowMenu(false);
            onClose?.();
          }}
          className="flex items-center gap-3 px-4 py-2 text-sm text-blue-400 hover:bg-slate-800 transition-colors border-t border-slate-800 mt-2 pt-2"
        >
          <span>View Full Account Settings</span>
          <ArrowRightOnRectangleIcon className="w-4 h-4 ml-auto" />
        </Link>
      </div>
    </div>
  );
}

