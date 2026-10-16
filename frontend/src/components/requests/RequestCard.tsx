/**
 * Request Card Component
 * Displays an access request summary
 */

'use client';

import { AccessRequest } from '@/lib/api/accessRequests';
import { format } from 'date-fns';
import Link from 'next/link';

interface RequestCardProps {
  request: AccessRequest;
}

export function RequestCard({ request }: RequestCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'approved':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'denied':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'cancelled':
        return 'bg-bg-alt text-text-main border-surface-card-border';
      default:
        return 'bg-bg-alt text-text-main border-surface-card-border';
    }
  };

  return (
    <Link href={`/dashboard/requests/${request.id}`}>
      <div className={`bg-surface-card rounded-lg border-2 p-6 hover:shadow-md transition-shadow cursor-pointer ${getStatusColor(request.status)}`}>
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-text-main mb-2">
              {request.resource_type}:{request.resource_id === '*' ? '*' : request.resource_id.substring(0, 8) + '...'}
              {' '}
              <span className="text-blue-600">{request.action}</span>
            </h3>
            <p className="text-sm text-text-muted line-clamp-2">{request.justification}</p>
          </div>
          <span
            className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(request.status)}`}
          >
            {request.status.toUpperCase()}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm text-text-muted mt-4 pt-4 border-t border-surface-card-border">
          <div>
            <span className="font-medium">Requested:</span>
            <p className="text-text-main">{format(new Date(request.created_at), 'MMM d, yyyy')}</p>
          </div>
          {request.reviewed_at && (
            <div>
              <span className="font-medium">Reviewed:</span>
              <p className="text-text-main">{format(new Date(request.reviewed_at), 'MMM d, yyyy')}</p>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

