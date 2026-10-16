/**
 * Request Timeline Component
 * Shows the history/timeline of an access request
 */

'use client';

import { useAccessRequestHistory } from '@/lib/hooks/useAccessRequests';
import { format } from 'date-fns';

interface RequestTimelineProps {
  requestId: string;
}

export function RequestTimeline({ requestId }: RequestTimelineProps) {
  const { data: history, isLoading, error } = useAccessRequestHistory(requestId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !history || history.length === 0) {
    return (
      <div className="bg-surface-hover border border-surface-card-border rounded-lg p-4">
        <p className="text-sm text-text-muted">No history available</p>
      </div>
    );
  }

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'created':
        return '📝';
      case 'approved':
        return '✅';
      case 'denied':
        return '❌';
      case 'cancelled':
        return '🚫';
      default:
        return '📌';
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'created':
        return 'bg-blue-100 text-blue-800';
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'denied':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
        return 'bg-bg-alt text-text-main';
      default:
        return 'bg-bg-alt text-text-main';
    }
  };

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
      <h3 className="text-lg font-semibold text-text-main mb-4">Timeline</h3>
      <div className="flow-root">
        <ul className="-mb-8">
          {history.map((item, itemIdx) => (
            <li key={item.id}>
              <div className="relative pb-8">
                {itemIdx !== history.length - 1 ? (
                  <span
                    className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-surface-hover"
                    aria-hidden="true"
                  />
                ) : null}
                <div className="relative flex space-x-3">
                  <div>
                    <span
                      className={`h-8 w-8 rounded-full flex items-center justify-center ${getEventColor(
                        item.event_type
                      )}`}
                    >
                      <span className="text-lg">{getEventIcon(item.event_type)}</span>
                    </span>
                  </div>
                  <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                    <div className="flex-1">
                      <p className="text-sm font-medium text-text-main capitalize">
                        {item.event_type.replace('_', ' ')}
                      </p>
                      {item.comments && (
                        <p className="mt-1 text-sm text-text-muted">{item.comments}</p>
                      )}
                      {item.new_status && (
                        <span className="mt-1 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-bg-alt text-text-main">
                          {item.new_status}
                        </span>
                      )}
                    </div>
                    <div className="text-right text-sm whitespace-nowrap text-text-muted">
                      {format(new Date(item.performed_at), 'MMM d, yyyy HH:mm')}
                    </div>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

