/**
 * Slide-Over Panel
 * Contextual investigation panel that slides in from the right.
 * Used for drill-down on incidents, alerts, entities, compliance criteria.
 */

'use client';

import { useEffect, useRef, useCallback } from 'react';
import clsx from 'clsx';

interface SlideOverPanelProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  width?: 'sm' | 'md' | 'lg' | 'xl';
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const WIDTH_MAP = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
};

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

export default function SlideOverPanel({
  open,
  onClose,
  title,
  subtitle,
  width = 'md',
  children,
  footer,
}: SlideOverPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  // Trap focus and handle Escape
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !panelRef.current) return;

      const focusable = panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (focusable.length === 0) {
        e.preventDefault();
        panelRef.current.focus();
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
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      previousFocus.current = document.activeElement as HTMLElement;
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';

      // Focus first focusable element
      requestAnimationFrame(() => {
        const firstFocusable = panelRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
        if (firstFocusable) {
          firstFocusable.focus();
        } else {
          panelRef.current?.focus();
        }
      });
    } else {
      document.body.style.overflow = '';
      previousFocus.current?.focus();
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={title}>
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-surface-overlay-strong transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={clsx(
          'absolute right-0 top-0 bottom-0 w-full flex flex-col',
          'bg-surface-card border-l border-border-faint shadow-2xl',
          'animate-in slide-in-from-right duration-300',
          WIDTH_MAP[width]
        )}
        tabIndex={-1}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-faint flex-shrink-0">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-text-main truncate">{title}</h2>
            {subtitle && <p className="text-xs text-text-muted mt-0.5 truncate">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="ml-3 p-2 rounded-lg hover:bg-surface-hover text-text-muted hover:text-text-main transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center flex-shrink-0"
            aria-label="Close panel"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="border-t border-border-faint px-5 py-3 flex-shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
