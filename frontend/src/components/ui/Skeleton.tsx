'use client';

import { clsx } from 'clsx';

interface SkeletonProps {
  className?: string;
  /** Width class (e.g., 'w-24', 'w-full') */
  width?: string;
  /** Height class (e.g., 'h-4', 'h-8') */
  height?: string;
  /** Use circle shape */
  circle?: boolean;
}

/**
 * Base skeleton shimmer block.
 */
export function Skeleton({ className, width, height, circle }: SkeletonProps) {
  return (
    <div
      className={clsx(
        'animate-pulse bg-slate-700/50 rounded',
        circle && 'rounded-full',
        width,
        height,
        className
      )}
      aria-hidden="true"
    />
  );
}

/**
 * Skeleton for a stats card (number + label).
 */
export function StatsCardSkeleton() {
  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
      <Skeleton width="w-24" height="h-4" className="mb-3" />
      <Skeleton width="w-16" height="h-8" className="mb-2" />
      <Skeleton width="w-32" height="h-3" />
    </div>
  );
}

/**
 * Grid of stats card skeletons.
 */
export function StatsGridSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8" role="status" aria-label="Loading statistics">
      {Array.from({ length: count }).map((_, i) => (
        <StatsCardSkeleton key={i} />
      ))}
      <span className="sr-only">Loading statistics...</span>
    </div>
  );
}

/**
 * Skeleton for a table row.
 */
export function TableRowSkeleton({ columns = 6 }: { columns?: number }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-6 py-4">
          <Skeleton width={i === 0 ? 'w-16' : i === 1 ? 'w-32' : 'w-20'} height="h-4" />
        </td>
      ))}
    </tr>
  );
}

/**
 * Skeleton for a full table.
 */
export function TableSkeleton({ rows = 5, columns = 6 }: { rows?: number; columns?: number }) {
  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border overflow-hidden" role="status" aria-label="Loading table data">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-surface-card-border border-b border-surface-card">
            <tr>
              {Array.from({ length: columns }).map((_, i) => (
                <th key={i} className="px-6 py-3">
                  <Skeleton width="w-16" height="h-3" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-card">
            {Array.from({ length: rows }).map((_, i) => (
              <TableRowSkeleton key={i} columns={columns} />
            ))}
          </tbody>
        </table>
      </div>
      <span className="sr-only">Loading table data...</span>
    </div>
  );
}

/**
 * Skeleton for the security snapshot panel.
 */
export function SecuritySnapshotSkeleton() {
  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6" role="status" aria-label="Loading security snapshot">
      <div className="flex items-center gap-3 mb-6">
        <Skeleton width="w-40" height="h-6" />
        <Skeleton width="w-20" height="h-5" className="rounded-full" />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-3">
          <Skeleton width="w-24" height="h-4" />
          <Skeleton width="w-full" height="h-20" className="rounded-lg" />
        </div>
        <div className="space-y-3">
          <Skeleton width="w-24" height="h-4" />
          <Skeleton width="w-full" height="h-20" className="rounded-lg" />
        </div>
        <div className="space-y-3">
          <Skeleton width="w-24" height="h-4" />
          <Skeleton width="w-full" height="h-20" className="rounded-lg" />
        </div>
      </div>
      <span className="sr-only">Loading security snapshot...</span>
    </div>
  );
}

/**
 * Skeleton for the AI insights widget.
 */
export function InsightsSkeleton() {
  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6" role="status" aria-label="Loading AI insights">
      <Skeleton width="w-28" height="h-6" className="mb-4" />
      <div className="space-y-3 mb-4">
        <Skeleton width="w-full" height="h-3" />
        <Skeleton width="w-3/4" height="h-3" />
        <Skeleton width="w-5/6" height="h-3" />
      </div>
      <Skeleton width="w-32" height="h-6" className="mb-3" />
      <div className="space-y-3">
        <Skeleton width="w-full" height="h-3" />
        <Skeleton width="w-2/3" height="h-3" />
      </div>
      <span className="sr-only">Loading AI insights...</span>
    </div>
  );
}
