/**
 * AI Insights Widget Component
 * Displays AI-generated key findings and recommendations
 */

'use client';

import { SecuritySnapshot } from '@/lib/api/orchestrator';
import { useState, useId } from 'react';
import clsx from 'clsx';

interface AIInsightsWidgetProps {
  snapshot: SecuritySnapshot;
}

export default function AIInsightsWidget({ snapshot }: AIInsightsWidgetProps) {
  const { ai_analysis } = snapshot;
  const [expandedSection, setExpandedSection] = useState<'findings' | 'recommendations' | null>('findings');
  const findingsId = useId();
  const recsId = useId();

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'text-red-500';
      case 'medium':
        return 'text-yellow-500';
      case 'low':
        return 'text-green-500';
      default:
        return 'text-text-muted';
    }
  };

  return (
    <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
      <h2 className="text-xl font-semibold text-text-main mb-4">AI Insights</h2>

      {/* Key Findings */}
      <div className="mb-4">
        <button
          onClick={() => setExpandedSection(expandedSection === 'findings' ? null : 'findings')}
          className="w-full flex items-center justify-between text-left mb-2 min-h-[44px] py-2 rounded-lg hover:bg-surface-hover/30 px-2 -mx-2 transition-colors"
          aria-expanded={expandedSection === 'findings'}
          aria-controls={findingsId}
        >
          <h3 className="text-sm font-semibold text-text-main">Key Findings</h3>
          <svg
            className={clsx(
              'w-4 h-4 text-text-muted transition-transform',
              expandedSection === 'findings' && 'rotate-180'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div
          id={findingsId}
          role="region"
          aria-label="Key findings"
          hidden={expandedSection !== 'findings'}
        >
          {ai_analysis.key_findings && ai_analysis.key_findings.length > 0 && (
            <ul className="space-y-2 pl-4">
              {ai_analysis.key_findings.map((finding, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm text-text-muted">
                  <span className="text-primary mt-1" aria-hidden="true">•</span>
                  <span>{finding}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Recommendations */}
      <div>
        <button
          onClick={() =>
            setExpandedSection(expandedSection === 'recommendations' ? null : 'recommendations')
          }
          className="w-full flex items-center justify-between text-left mb-2 min-h-[44px] py-2 rounded-lg hover:bg-surface-hover/30 px-2 -mx-2 transition-colors"
          aria-expanded={expandedSection === 'recommendations'}
          aria-controls={recsId}
        >
          <h3 className="text-sm font-semibold text-text-main">Recommendations</h3>
          <svg
            className={clsx(
              'w-4 h-4 text-text-muted transition-transform',
              expandedSection === 'recommendations' && 'rotate-180'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <div
          id={recsId}
          role="region"
          aria-label="Recommendations"
          hidden={expandedSection !== 'recommendations'}
        >
          {ai_analysis.recommendations && ai_analysis.recommendations.length > 0 && (
            <ul className="space-y-2 pl-4">
              {ai_analysis.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className={clsx('mt-1 font-semibold', getPriorityColor(rec.priority))}>
                    [{rec.priority}]
                  </span>
                  <span className="text-text-muted">{rec.action}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
