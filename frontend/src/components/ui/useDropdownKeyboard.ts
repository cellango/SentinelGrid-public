import { useCallback, useRef } from 'react';

interface UseDropdownKeyboardOptions {
  isOpen: boolean;
  onClose: () => void;
  /** Selector for focusable items inside the dropdown (default: 'a, button') */
  itemSelector?: string;
  /** Ref of the trigger element to return focus to on close */
  triggerRef?: React.RefObject<HTMLElement | null>;
}

/**
 * Hook that provides keyboard navigation for dropdown menus.
 * Handles ArrowUp/Down for focus movement and Escape to close.
 *
 * Usage:
 * ```tsx
 * const { containerProps } = useDropdownKeyboard({
 *   isOpen: showMenu,
 *   onClose: () => setShowMenu(false),
 *   triggerRef: buttonRef,
 * });
 * <div {...containerProps}>{menu items}</div>
 * ```
 */
export function useDropdownKeyboard({
  isOpen,
  onClose,
  itemSelector = 'a, button[role="menuitem"], button:not([disabled])',
  triggerRef,
}: UseDropdownKeyboardOptions) {
  const containerRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        triggerRef?.current?.focus();
        return;
      }

      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const items = containerRef.current?.querySelectorAll<HTMLElement>(itemSelector);
        if (!items?.length) return;

        const currentIdx = Array.from(items).indexOf(document.activeElement as HTMLElement);
        let nextIdx: number;

        if (e.key === 'ArrowDown') {
          nextIdx = currentIdx < items.length - 1 ? currentIdx + 1 : 0;
        } else {
          nextIdx = currentIdx > 0 ? currentIdx - 1 : items.length - 1;
        }

        items[nextIdx]?.focus();
      }

      if (e.key === 'Tab') {
        // Close on Tab out
        onClose();
      }
    },
    [isOpen, onClose, itemSelector, triggerRef]
  );

  return {
    containerRef,
    containerProps: {
      ref: containerRef,
      onKeyDown: handleKeyDown,
    },
  };
}
