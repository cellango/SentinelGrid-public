import React from 'react';
import { PhishingReport } from '@/lib/api/phishing';
import clsx from 'clsx';
import { format } from 'date-fns';

interface PhishingReportCardProps {
  report: PhishingReport;
  onClick: () => void;
}

const getClassificationColor = (classification?: string) => {
  switch (classification?.toLowerCase()) {
    case 'phishing':
      return 'bg-red-600 text-white';
    case 'benign':
      return 'bg-green-600 text-white';
    case 'suspicious':
      return 'bg-yellow-600 text-white';
    default:
      return 'bg-border text-white';
  }
};

const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'new':
      return 'bg-blue-500';
    case 'in_review':
      return 'bg-yellow-500';
    case 'confirmed_phishing':
      return 'bg-red-500';
    case 'confirmed_benign':
      return 'bg-green-500';
    case 'resolved':
      return 'bg-surface-hover0';
    default:
      return 'bg-border-muted';
  }
};

const getSeverityColor = (severity?: string) => {
  switch (severity?.toLowerCase()) {
    case 'critical':
      return 'text-red-400';
    case 'high':
      return 'text-orange-400';
    case 'medium':
      return 'text-yellow-400';
    case 'low':
      return 'text-green-400';
    default:
      return 'text-text-muted';
  }
};

const PhishingReportCard: React.FC<PhishingReportCardProps> = ({ report, onClick }) => {
  return (
    <div
      onClick={onClick}
      className="bg-surface-dark border border-surface-card-border rounded-lg p-4 hover:border-primary cursor-pointer transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-text-main mb-1">
            {report.subject || '(No Subject)'}
          </h3>
          <p className="text-sm text-text-muted mb-2">
            From: <span className="text-text-main">{report.from_address}</span>
          </p>
          {report.reported_by && (
            <p className="text-xs text-text-muted">
              Reported by: {report.reported_by}
            </p>
          )}
        </div>
        <div className="flex flex-col items-end gap-2">
          {report.classification && (
            <span
              className={clsx(
                'px-2 py-1 rounded-full text-xs font-medium',
                getClassificationColor(report.classification)
              )}
            >
              {report.classification}
            </span>
          )}
          <span
            className={clsx(
              'px-2 py-1 rounded-full text-xs font-medium text-white',
              getStatusColor(report.status)
            )}
          >
            {report.status.replace('_', ' ')}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-4">
          {report.severity && (
            <span className={clsx('font-medium', getSeverityColor(report.severity))}>
              {report.severity.toUpperCase()}
            </span>
          )}
          {report.classification_confidence !== undefined && (
            <span className="text-text-muted">
              Confidence: {report.classification_confidence.toFixed(1)}%
            </span>
          )}
        </div>
        <div className="text-text-muted">
          {format(new Date(report.received_date), 'MMM dd, yyyy HH:mm')}
        </div>
      </div>

      {report.ai_summary && (
        <div className="mt-3 pt-3 border-t border-surface-card-border">
          <p className="text-sm text-text-muted line-clamp-2">{report.ai_summary}</p>
        </div>
      )}
    </div>
  );
};

export default PhishingReportCard;

