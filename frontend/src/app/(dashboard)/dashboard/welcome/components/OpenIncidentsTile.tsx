/**
 * Open Security Incidents Tile
 * Shows active incidents with quick actions
 */

'use client';

import Link from 'next/link';
import { OpenIncident } from '@/lib/api/dashboard';
import StorySummaryInline from '@/components/operator/StorySummaryInline';

interface OpenIncidentsTileProps {
  incidents: OpenIncident[];
}

export default function OpenIncidentsTile({ incidents }: OpenIncidentsTileProps) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 hover:border-primary/40 transition-all">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-text-main mb-1">Active Incidents</h3>
          <p className="text-sm text-text-muted">{incidents.length} requiring attention</p>
        </div>
        <Link
          href="/dashboard/incidents"
          className="text-xs text-primary hover:text-primary/80 transition-colors"
        >
          View all →
        </Link>
      </div>

      {incidents.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-3xl mb-2">✅</div>
          <p className="text-text-muted text-sm">No active incidents</p>
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.slice(0, 3).map((incident) => {
            const quickActions = incident.quick_actions || [];
            return (
            <div
              key={incident.id}
              className="bg-[rgba(15,23,42,0.9)] border border-primary/10 rounded-xl p-3 hover:border-primary/30 transition-all"
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-medium text-text-main truncate">{incident.title}</h4>
                  <p className="text-xs text-text-muted mt-0.5">
                    {incident.affected_count} {incident.affected_count === 1 ? 'entity' : 'entities'} affected
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded-lg text-xs font-semibold border flex-shrink-0 ${getSeverityColor(incident.severity)}`}>
                  {incident.severity}
                </span>
              </div>

              <StorySummaryInline
                summary={incident.story_summary}
                domains={incident.story_domains}
              />

              {incident.ai_summary && (
                <Link
                  href={`/dashboard/incidents/${incident.id}`}
                  className="text-xs text-primary hover:text-primary/80 mt-2 inline-block"
                >
                  View AI Summary →
                </Link>
              )}

              {quickActions.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {quickActions.slice(0, 2).map((action, idx) => (
                    <button
                      key={idx}
                      className="px-2 py-1 text-xs bg-primary/10 text-primary rounded-lg hover:bg-primary/20 transition-colors border border-primary/20"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )})}
        </div>
      )}
    </div>
  );
}
