/**
 * Incidents Timeline Component
 * Shows recent incidents with sparkline chart
 */

'use client';

import Link from 'next/link';
import { OpenIncident } from '@/lib/api/dashboard';

interface IncidentsTimelineProps {
  incidents: OpenIncident[];
}

export default function IncidentsTimeline({ incidents }: IncidentsTimelineProps) {
  // Group incidents by day for sparkline (last 7 days)
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return date.toISOString().split('T')[0];
  });

  const incidentsByDay = last7Days.map((day) => {
    return incidents.filter((inc) => inc.created_at.startsWith(day)).length;
  });

  const maxCount = Math.max(...incidentsByDay, 1);
  const sparklineHeight = 40;

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-main">Incidents Last 7 Days</h3>
        <Link
          href="/dashboard/incidents"
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          View all →
        </Link>
      </div>

      {/* Sparkline Chart */}
      <div className="mb-4">
        <div className="flex items-end justify-between h-12 gap-1">
          {incidentsByDay.map((count, idx) => (
            <div
              key={idx}
              className="flex-1 bg-primary/20 rounded-t transition-all hover:bg-primary/30"
              style={{
                height: `${(count / maxCount) * sparklineHeight}px`,
                minHeight: count > 0 ? '4px' : '2px',
              }}
              title={`${last7Days[idx]}: ${count} ${count === 1 ? 'incident' : 'incidents'}`}
            />
          ))}
        </div>
        <div className="flex justify-between text-xs text-text-muted mt-1">
          <span>7d ago</span>
          <span>Today</span>
        </div>
      </div>

      {/* Recent Incidents List */}
      <div className="space-y-2">
        {incidents.slice(0, 3).map((incident) => (
          <Link
            key={incident.id}
            href={`/dashboard/incidents/${incident.id}`}
            className="block p-2 rounded-lg border border-primary/10 hover:border-primary/30 transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm text-text-main truncate flex-1">{incident.title}</span>
              <span className="text-xs text-text-muted ml-2">
                {new Date(incident.created_at).toLocaleDateString()}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

