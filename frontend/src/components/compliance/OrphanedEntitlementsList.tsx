/**
 * Orphaned Entitlements List Component
 * Lists entitlements that should be revoked (expired, users no longer exist, etc.)
 */

'use client';

import { useOrphanedEntitlements } from '@/lib/hooks/useCompliance';
import { format } from 'date-fns';
import Link from 'next/link';

interface OrphanedEntitlementsListProps {
  tenantId: string;
}

export function OrphanedEntitlementsList({ tenantId }: OrphanedEntitlementsListProps) {
  const { data: orphaned, isLoading, error, refetch } = useOrphanedEntitlements(tenantId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Error loading orphaned entitlements. Please try again.</p>
      </div>
    );
  }

  if (!orphaned || orphaned.orphaned_count === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <div className="text-4xl mb-2">✅</div>
        <p className="text-green-800 font-medium">No orphaned entitlements found</p>
        <p className="text-sm text-green-600 mt-1">All entitlements are properly managed.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-text-main">Orphaned Entitlements</h3>
          <p className="text-sm text-text-muted mt-1">
            {orphaned.orphaned_count} entitlement{orphaned.orphaned_count !== 1 ? 's' : ''} found that should be reviewed
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="px-3 py-2 text-sm border border-border rounded-md text-text-muted hover:bg-surface-hover"
        >
          Refresh
        </button>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-yellow-800">
              Orphaned entitlements are entitlements that have expired or are granted to users who may no longer exist.
              Review and revoke these entitlements to maintain compliance.
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-surface-hover">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Resource
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Action
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Granted To
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Expired At
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-surface-card divide-y divide-border">
            {orphaned.entitlements.map((entitlement) => (
              <tr key={entitlement.id} className="hover:bg-surface-hover">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-text-main">{entitlement.resource_type}</div>
                  <div className="text-sm text-text-muted font-mono">
                    {entitlement.resource_id === '*' ? '*' : entitlement.resource_id.substring(0, 16) + '...'}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="text-sm text-text-main">{entitlement.action}</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-text-main">{entitlement.granted_to_type}</div>
                  <div className="text-sm text-text-muted font-mono">{entitlement.granted_to_id.substring(0, 8)}...</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                  {entitlement.expired_at ? (
                    <span className="text-red-600 font-medium">
                      {format(new Date(entitlement.expired_at), 'MMM d, yyyy')}
                    </span>
                  ) : (
                    <span className="text-text-muted">-</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  <Link
                    href={`/dashboard/entitlements?filter=${entitlement.id}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

