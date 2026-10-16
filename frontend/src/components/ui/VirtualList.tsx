/**
 * Virtual List Component
 * Virtualized scrolling for large datasets (alerts, incidents, logs).
 * Uses @tanstack/react-virtual for efficient DOM rendering.
 */

'use client';

import { useRef, useCallback } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import clsx from 'clsx';

interface VirtualListProps<T> {
  items: T[];
  estimateSize: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  overscan?: number;
  className?: string;
  getItemKey?: (index: number) => string | number;
  onEndReached?: () => void;
  endReachedThreshold?: number;
}

export default function VirtualList<T>({
  items,
  estimateSize,
  renderItem,
  overscan = 10,
  className,
  getItemKey,
  onEndReached,
  endReachedThreshold = 5,
}: VirtualListProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);
  const onEndReachedCalled = useRef(false);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize,
    overscan,
    getItemKey: getItemKey,
  });

  const virtualItems = virtualizer.getVirtualItems();

  // Infinite scroll detection
  const handleScroll = useCallback(() => {
    if (!onEndReached || !parentRef.current) return;
    const lastItem = virtualItems[virtualItems.length - 1];
    if (!lastItem) return;

    if (lastItem.index >= items.length - endReachedThreshold && !onEndReachedCalled.current) {
      onEndReachedCalled.current = true;
      onEndReached();
      // Reset after a short delay to allow new items
      setTimeout(() => { onEndReachedCalled.current = false; }, 1000);
    }
  }, [virtualItems, items.length, endReachedThreshold, onEndReached]);

  if (items.length === 0) return null;

  return (
    <div
      ref={parentRef}
      className={clsx('overflow-auto', className)}
      onScroll={handleScroll}
      role="list"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualItems.map((virtualItem) => (
          <div
            key={virtualItem.key}
            role="listitem"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: `${virtualItem.size}px`,
              transform: `translateY(${virtualItem.start}px)`,
            }}
          >
            {renderItem(items[virtualItem.index], virtualItem.index)}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Virtual Table — Virtualized table body for large datasets.
 * Renders table rows efficiently while keeping thead/tfoot static.
 */
interface VirtualTableProps<T> {
  items: T[];
  rowHeight: number;
  renderRow: (item: T, index: number) => React.ReactNode;
  header: React.ReactNode;
  overscan?: number;
  className?: string;
  maxHeight?: string;
}

export function VirtualTable<T>({
  items,
  rowHeight,
  renderRow,
  header,
  overscan = 15,
  className,
  maxHeight = '600px',
}: VirtualTableProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan,
  });

  return (
    <div className={clsx('overflow-hidden', className)}>
      <table className="w-full text-sm">
        {header}
      </table>
      <div
        ref={parentRef}
        className="overflow-auto"
        style={{ maxHeight }}
      >
        <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
          <table className="w-full text-sm" style={{ position: 'absolute', top: 0 }}>
            <tbody>
              {virtualizer.getVirtualItems().map((virtualItem) => (
                <tr
                  key={virtualItem.key}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${virtualItem.size}px`,
                    transform: `translateY(${virtualItem.start}px)`,
                    display: 'table-row',
                  }}
                >
                  {renderRow(items[virtualItem.index], virtualItem.index)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
