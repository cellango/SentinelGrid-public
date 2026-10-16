/**
 * Recommended Actions Section
 * Shows AI-generated prioritized action recommendations
 */

'use client';

import { Recommendation } from '@/lib/api/dashboard';
import Link from 'next/link';
import { getRecommendationActionHref, formatRecommendationClass } from '@/lib/dashboard/recommendations';

interface RecommendedActionsProps {
  recommendations: Recommendation[];
}

export default function RecommendedActions({ recommendations }: RecommendedActionsProps) {
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      case 'high':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      default:
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    }
  };
  if (recommendations.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold text-text-main mb-2">Recommended Next Steps</h2>
      <p className="text-text-muted mb-6">Here&apos;s what we recommend doing next</p>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 hover:border-primary/40 transition-all"
          >
            <div className="flex items-start justify-between mb-3">
              <span className={`px-2 py-1 rounded-lg text-xs font-semibold border ${getPriorityColor(rec.priority)}`}>
                {rec.priority.toUpperCase()}
              </span>
              <span className="text-xs text-text-muted">{rec.estimated_time_minutes} min</span>
            </div>

            {rec.finding_class && (
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                {formatRecommendationClass(rec.finding_class)}
              </p>
            )}
            <h3 className="text-lg font-semibold text-text-main mb-2">{rec.title}</h3>
            <p className="text-sm text-text-muted mb-4">{rec.description}</p>

            {rec.remediation && (
              <div className="mb-4 rounded-xl border border-primary/10 bg-slate-950/50 p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
                      Guided remediation
                    </p>
                    <h4 className="mt-1 text-sm font-semibold text-text-main">
                      {rec.remediation.title}
                    </h4>
                  </div>
                  <span className="rounded-full border border-primary/20 px-2.5 py-1 text-[11px] font-medium text-text-muted">
                    Owner: {rec.remediation.owner}
                  </span>
                </div>

                <p className="mb-3 text-sm leading-6 text-text-muted">
                  {rec.remediation.why_now}
                </p>

                <ol className="space-y-2 text-sm text-text-muted">
                  {rec.remediation.steps.map((step, index) => (
                    <li key={`${rec.id}-${index}`} className="rounded-lg border border-primary/5 bg-slate-950/60 p-3">
                      <p className="font-medium text-text-main">
                        {index + 1}. {step.title}
                      </p>
                      <p className="mt-1 leading-6">{step.description}</p>
                    </li>
                  ))}
                </ol>

                <div className="mt-3 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
                  <span className="font-medium text-emerald-200">Success looks like:</span>{' '}
                  {rec.remediation.success_criteria}
                </div>
              </div>
            )}

            <div className="flex flex-wrap gap-2">
              {rec.actions.map((action, idx) => {
                const href = getRecommendationActionHref(action);
                if ((action.type === 'fix_now' || action.type === 'view_details' || action.type === 'open_ticket') && href) {
                  return (
                    <Link
                      key={idx}
                      href={href}
                      className={
                        action.type === 'fix_now'
                          ? 'px-3 py-1.5 bg-gradient-to-r from-primary to-secondary text-slate-950 rounded-lg hover:brightness-110 transition-all text-sm font-medium'
                          : 'px-3 py-1.5 bg-primary/20 text-primary rounded-lg hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30'
                      }
                    >
                      {action.label}
                    </Link>
                  );
                }
                return (
                  <button
                    key={idx}
                    className="px-3 py-1.5 bg-[rgba(15,23,42,0.9)] border border-primary/10 text-text-main rounded-lg hover:border-primary/30 transition-colors text-sm font-medium"
                  >
                    {action.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
