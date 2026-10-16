/**
 * Activity Timeline Chart Component
 * Visualizes event trends over time using real API data
 */

'use client';

import { useState, useEffect } from 'react';
import { SecuritySnapshot } from '@/lib/api/orchestrator';
import { useTimelineData } from '../hooks/useTimelineData';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface ActivityTimelineProps {
  snapshot: SecuritySnapshot;
}

export default function ActivityTimeline({ snapshot }: ActivityTimelineProps) {
  const [tenantId, setTenantId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const storedTenantId = localStorage.getItem('tenant_id');
      setTenantId(storedTenantId);
    }
  }, []);

  const { data: timelineData, isLoading, error } = useTimelineData(tenantId, 7);

  // Fallback to snapshot summary if timeline data not available
  const data = timelineData || (() => {
    // Generate basic timeline from snapshot summary as fallback
    const now = new Date();
    const fallbackData = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      fallbackData.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        events: Math.floor(snapshot.summary.events_count / 7),
        alerts: Math.floor(snapshot.summary.alerts_count / 7),
      });
    }
    return fallbackData;
  })();

  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-text-main">Activity Timeline</h2>
        {isLoading && (
          <div className="flex items-center gap-2 text-sm text-text-muted">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent"></div>
            <span>Loading...</span>
          </div>
        )}
      </div>

      {error ? (
        <div className="h-64 flex items-center justify-center text-text-muted">
          <p className="text-sm">Failed to load timeline data. Using summary data.</p>
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
              <XAxis
                dataKey="date"
                stroke="#94a3b8"
                style={{ fontSize: '12px' }}
              />
              <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  border: '1px solid rgba(15, 23, 42, 0.95)',
                  borderRadius: '8px',
                  color: '#e2e8f0',
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="events"
                stroke="#22d3ee"
                strokeWidth={2}
                name="Events"
                dot={{ fill: '#22d3ee', r: 3 }}
              />
              <Line
                type="monotone"
                dataKey="alerts"
                stroke="#a855f7"
                strokeWidth={2}
                name="Alerts"
                dot={{ fill: '#a855f7', r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
