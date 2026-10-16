import React from 'react';
import { PhishingReport } from '@/lib/api/phishing';
import NISTBadge from '@/components/framework/NISTBadge';
import MITREBadge from '@/components/framework/MITREBadge';
import clsx from 'clsx';

interface AIAnalysisProps {
  report: PhishingReport;
}

const AIAnalysis: React.FC<AIAnalysisProps> = ({ report }) => {
  if (!report.ai_summary && !report.classification) {
    return (
      <div className="bg-surface-dark border border-surface-card-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-text-main mb-4">AI Analysis</h2>
        <p className="text-text-muted">No AI analysis available. Click "Classify" to trigger analysis.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-dark border border-surface-card-border rounded-lg p-6">
      <h2 className="text-xl font-semibold text-text-main mb-4">AI Analysis</h2>

      {/* Classification */}
      {report.classification && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-text-main">Classification:</span>
            <span
              className={clsx(
                'px-2 py-1 rounded text-sm font-medium',
                report.classification === 'phishing'
                  ? 'bg-red-600 text-white'
                  : report.classification === 'benign'
                  ? 'bg-green-600 text-white'
                  : 'bg-yellow-600 text-white'
              )}
            >
              {report.classification.toUpperCase()}
            </span>
            {report.classification_confidence !== undefined && (
              <span className="text-sm text-text-muted">
                ({report.classification_confidence.toFixed(1)}% confidence)
              </span>
            )}
          </div>
        </div>
      )}

      {/* Reasoning */}
      {report.ai_summary && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-text-main mb-2">Analysis</h3>
          <p className="text-sm text-text-muted leading-relaxed">{report.ai_summary}</p>
        </div>
      )}

      {/* Recommended Actions */}
      {report.ai_recommended_actions && report.ai_recommended_actions.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-text-main mb-2">Recommended Actions</h3>
          <ul className="list-disc list-inside space-y-1 text-sm text-text-muted">
            {report.ai_recommended_actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Framework Mappings */}
      {(report.mitre_tactics?.length || report.mitre_techniques?.length || report.nist_controls?.length) && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-text-main mb-2">Framework Mappings</h3>
          <div className="flex flex-wrap gap-2">
            {report.nist_controls?.map((control, index) => (
              <NISTBadge key={index} controlId={control} />
            ))}
            {report.mitre_tactics?.map((tactic, index) => (
              <MITREBadge key={index} type="tactic" id={tactic} />
            ))}
            {report.mitre_techniques?.map((technique, index) => (
              <MITREBadge key={index} type="technique" id={technique} />
            ))}
          </div>
        </div>
      )}

      {/* Classification Metadata */}
      {report.classified_by && report.classified_at && (
        <div className="text-xs text-text-muted border-t border-surface-card-border pt-4 mt-4">
          Classified by {report.classified_by} on {new Date(report.classified_at).toLocaleString()}
        </div>
      )}
    </div>
  );
};

export default AIAnalysis;

