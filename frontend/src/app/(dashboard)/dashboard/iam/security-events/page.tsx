/**
 * Security Events Page
 * View security events and anomalies with filters and export
 */

'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  ExclamationTriangleIcon,
  ShieldExclamationIcon,
  CheckCircleIcon,
  ArrowDownTrayIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';

// Use relative URLs to leverage Next.js rewrites
const API_BASE = '';

interface SecurityEvent {
  id: string;
  timestamp: string;
  event_type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  user_id?: string;
  user_email?: string;
  ip_address?: string;
  status: 'open' | 'acknowledged' | 'resolved';
}

async function getSecurityEvents(
  startDate?: string,
  endDate?: string,
  eventType?: string,
  severity?: string,
  page: number = 1,
  limit: number = 50
): Promise<{ items: SecurityEvent[]; total: number; page: number; limit: number; pages: number }> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (eventType) params.append('event_type', eventType);
  if (severity) params.append('severity', severity);

  const response = await fetch(`/api/v1/audit-logs/security-events?${params.toString()}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    return { items: [], total: 0, page, limit, pages: 1 };
  }
  return response.json().catch(() => ({ items: [], total: 0, page, limit, pages: 1 }));
}

async function acknowledgeEvent(eventId: string): Promise<void> {
  await fetch(`/api/v1/security/anomalies/${eventId}/acknowledge`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({}),
  });
}

export default function SecurityEventsPage() {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [showFilters, setShowFilters] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');

  const { data: eventsData, isLoading } = useQuery({
    queryKey: ['security-events', startDate, endDate, eventTypeFilter, severityFilter],
    queryFn: () => getSecurityEvents(startDate || undefined, endDate || undefined, eventTypeFilter || undefined, severityFilter || undefined),
    enabled: isAuthenticated,
  });

  const acknowledgeMutation = useMutation({
    mutationFn: (eventId: string) => acknowledgeEvent(eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['security-events'] });
    },
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-bg-alt text-text-main border-surface-card-border';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return ShieldExclamationIcon;
      case 'medium':
        return ExclamationTriangleIcon;
      default:
        return CheckCircleIcon;
    }
  };

  const events = eventsData?.items ?? [];

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-slate-600 dark:text-slate-300">Loading security events...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto text-slate-900 dark:text-slate-100">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Security Events</h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1">
            View and manage security events and anomalies
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-surface-hover transition-colors"
          >
            <FunnelIcon className="w-5 h-5" />
            Filters
          </button>
          <button
            onClick={() => {
              // Export to CSV
              const params = new URLSearchParams();
              if (startDate) params.append('start_date', startDate);
              if (endDate) params.append('end_date', endDate);
              window.open(`${API_BASE}/api/v1/audit-logs/security-events/export?${params.toString()}`, '_blank');
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowDownTrayIcon className="w-5 h-5" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="mb-6 bg-surface-card border border-surface-card-border rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Event Type
              </label>
              <select
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              >
                <option value="">All Types</option>
                <option value="login">Login</option>
                <option value="logout">Logout</option>
                <option value="failed_login">Failed Login</option>
                <option value="anomaly">Anomaly</option>
                <option value="policy_violation">Policy Violation</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-muted mb-1">
                Severity
              </label>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-surface-card text-slate-900 dark:text-slate-100"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Events List */}
      {events.length > 0 ? (
        <div className="space-y-4">
          {events.map((event) => {
            const SeverityIcon = getSeverityIcon(event.severity);
            return (
              <div
                key={event.id}
                className={`bg-surface-card border-2 rounded-lg p-4 ${getSeverityColor(event.severity)}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <SeverityIcon className="w-6 h-6 mt-1" />
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-semibold">{event.title}</h3>
                        <span className={`px-2 py-1 text-xs font-medium rounded ${getSeverityColor(event.severity)}`}>
                          {event.severity}
                        </span>
                        <span className="text-xs text-text-muted">
                          {event.timestamp ? new Date(event.timestamp).toLocaleString() : ''}
                        </span>
                      </div>
                      <p className="text-sm text-text-muted mb-2">{event.description}</p>
                      <div className="flex items-center gap-4 text-xs text-text-muted">
                        {event.user_email && (
                          <span>User: {event.user_email}</span>
                        )}
                        {event.ip_address && (
                          <span>IP: {event.ip_address}</span>
                        )}
                        <span>Type: {event.event_type}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {event.status === 'open' && (
                      <button
                        onClick={() => acknowledgeMutation.mutate(event.id)}
                        disabled={acknowledgeMutation.isPending}
                        className="px-3 py-1 text-sm bg-surface-card text-text-muted rounded hover:bg-surface-hover transition-colors disabled:opacity-50"
                      >
                        Acknowledge
                      </button>
                    )}
                    {event.status === 'acknowledged' && (
                      <span className="px-3 py-1 text-sm bg-bg-alt text-text-muted rounded">
                        Acknowledged
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center py-12 bg-surface-card border border-surface-card-border rounded-lg">
          <ShieldExclamationIcon className="w-12 h-12 text-text-muted mx-auto mb-4" />
          <p className="text-text-muted">No security events found</p>
        </div>
      )}
    </div>
  );
}
