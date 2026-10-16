'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { listAlerts, Alert, AlertListResponse } from '@/lib/api/siem';

export default function DetectionEventsPage() {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<string>('24h');

  const { data: alertsResponse, isLoading } = useQuery<AlertListResponse>({
    queryKey: ['detection-events', selectedSeverity, selectedCategory, timeRange],
    queryFn: async () => {
      return listAlerts({ limit: 50 });
    },
    refetchInterval: 30000 // Auto-refresh every 30 seconds
  });

  const filteredEvents = alertsResponse?.alerts.filter(event => {
    if (selectedSeverity !== 'all' && event.severity !== selectedSeverity) return false;
    // No category concept on alerts yet; keep pass-through for now
    return true;
  }) || [];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/30';
      case 'high': return 'text-orange-500 bg-orange-500/10 border-orange-500/30';
      case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
      case 'low': return 'text-blue-500 bg-blue-500/10 border-blue-500/30';
      default: return 'text-text-muted bg-surface-hover0/10 border-border-muted';
    }
  };

  const getPlaybookStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-500 bg-green-500/10';
      case 'executed': return 'text-green-500 bg-green-500/10';
      case 'running': return 'text-blue-500 bg-blue-500/10';
      case 'pending': return 'text-yellow-500 bg-yellow-500/10';
      case 'failed': return 'text-red-500 bg-red-500/10';
      default: return 'text-text-muted bg-surface-hover0/10';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-bg-alt rounded w-1/3"></div>
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-bg-alt rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-text-main mb-2">
          Detection Events
        </h1>
        <p className="text-text-muted">
          Real-time stream of detection events from your rules
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Severity Filter */}
        <div>
          <label className="block text-sm font-medium text-text-muted mb-2">
            Severity
          </label>
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="w-full px-3 py-2 bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] rounded-lg text-text-main focus:outline-none focus:border-primary"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Category Filter */}
        <div>
          <label className="block text-sm font-medium text-text-muted mb-2">
            Category
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="w-full px-3 py-2 bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] rounded-lg text-text-main focus:outline-none focus:border-primary"
          >
            <option value="all">All Categories</option>
            <option value="identity">Identity</option>
            <option value="email">Email</option>
            <option value="endpoint">Endpoint</option>
            <option value="cloud">Cloud</option>
            <option value="network">Network</option>
            <option value="device">Device</option>
          </select>
        </div>

        {/* Time Range */}
        <div>
          <label className="block text-sm font-medium text-text-muted mb-2">
            Time Range
          </label>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="w-full px-3 py-2 bg-[rgba(15,23,42,0.9)] border border-[rgba(15,23,42,0.95)] rounded-lg text-text-main focus:outline-none focus:border-primary"
          >
            <option value="1h">Last 1 hour</option>
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
          </select>
        </div>
      </div>

      {/* Detection Events List */}
      <div className="space-y-4">
        {filteredEvents.map((event: Alert) => (
          <div
            key={event.id}
            className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6 hover:border-primary/30 transition-colors"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold text-text-main">
                    {event.title}
                  </h3>
                  <span className={`px-2 py-1 text-xs rounded-full border ${getSeverityColor(event.severity)}`}>
                    {event.severity.toUpperCase()}
                  </span>
                  <span className="px-2 py-1 text-xs rounded-full bg-primary/10 border border-primary/30 text-primary">
                    {event.detection_rule_id || 'Manual'}
                  </span>
                </div>
                
                {/* Entity Information */}
                <div className="flex items-center gap-4 text-sm text-text-muted mb-3">
                  {event.user_id && (
                    <span>👤 User: {event.user_id}</span>
                  )}
                  {event.source_ip && (
                    <span>
                      🌐 {event.source_ip}
                    </span>
                  )}
                  <span>Status: {event.status}</span>
                </div>

                <div className="flex items-center gap-4 text-xs text-text-muted">
                  <span>Alert ID: {event.id.slice(0, 8)}...</span>
                  <span>Source: {event.source}</span>
                  <span>{formatTimestamp(event.timestamp || event.created_at)}</span>
                </div>
              </div>

              <div className="flex flex-col items-end gap-2">
                <span className="px-3 py-1 text-xs rounded-full bg-primary/10 border border-primary/30 text-primary">
                  Count: {event.count ?? 1}
                </span>
              </div>
            </div>

            {/* NIST Phase Indicator */}
            <div className="flex items-center gap-2 pt-3 border-t border-[rgba(15,23,42,0.9)]">
              <span className="text-xs text-text-muted">NIST Phase:</span>
              <span className="px-2 py-1 text-xs rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-500">
                Detection & Analysis
              </span>
              <span className="text-xs text-text-muted ml-auto">
                Rule ID: {event.detection_rule_id || 'N/A'}
              </span>
            </div>
          </div>
        ))}
      </div>

      {filteredEvents.length === 0 && (
        <div className="text-center py-12 bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)]">
          <p className="text-text-muted">No detection events found for the selected filters.</p>
        </div>
      )}

      {/* Auto-refresh indicator */}
      <div className="mt-6 text-center">
        <p className="text-xs text-text-muted">
          Auto-refreshing every 30 seconds
        </p>
      </div>
    </div>
  );
}
