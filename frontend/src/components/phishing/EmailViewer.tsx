import React, { useState } from 'react';
import clsx from 'clsx';
import { PhishingReport } from '@/lib/api/phishing';

interface EmailViewerProps {
  report: PhishingReport;
}

const EmailViewer: React.FC<EmailViewerProps> = ({ report }) => {
  const [viewMode, setViewMode] = useState<'html' | 'text' | 'raw'>('html');

  return (
    <div className="bg-surface-dark border border-surface-card-border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-text-main">Email Content</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('html')}
            className={clsx(
              'px-3 py-1 rounded text-sm',
              viewMode === 'html'
                ? 'bg-primary text-white'
                : 'bg-surface-light text-text-muted hover:text-text-main'
            )}
          >
            HTML
          </button>
          <button
            onClick={() => setViewMode('text')}
            className={clsx(
              'px-3 py-1 rounded text-sm',
              viewMode === 'text'
                ? 'bg-primary text-white'
                : 'bg-surface-light text-text-muted hover:text-text-main'
            )}
          >
            Text
          </button>
          <button
            onClick={() => setViewMode('raw')}
            className={clsx(
              'px-3 py-1 rounded text-sm',
              viewMode === 'raw'
                ? 'bg-primary text-white'
                : 'bg-surface-light text-text-muted hover:text-text-main'
            )}
          >
            Raw
          </button>
        </div>
      </div>

      <div className="bg-surface-light rounded-lg p-4 border border-surface-card-border">
        {/* Email Headers */}
        <div className="mb-4 pb-4 border-b border-surface-card-border">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-text-muted">From:</span>
              <span className="text-text-main ml-2">{report.from_address}</span>
            </div>
            <div>
              <span className="text-text-muted">To:</span>
              <span className="text-text-main ml-2">{report.to_address}</span>
            </div>
            {report.reply_to && (
              <div>
                <span className="text-text-muted">Reply-To:</span>
                <span className="text-text-main ml-2">{report.reply_to}</span>
              </div>
            )}
            {report.reported_by && (
              <div>
                <span className="text-text-muted">Reported By:</span>
                <span className="text-text-main ml-2">{report.reported_by}</span>
              </div>
            )}
          </div>
        </div>

        {/* Email Body */}
        <div className="max-h-96 overflow-auto">
          {viewMode === 'html' && report.html_body ? (
            <div
              dangerouslySetInnerHTML={{ __html: report.html_body }}
              className="prose prose-invert max-w-none"
            />
          ) : viewMode === 'text' && report.text_body ? (
            <pre className="whitespace-pre-wrap text-sm text-text-main font-mono">
              {report.text_body}
            </pre>
          ) : (
            <pre className="whitespace-pre-wrap text-xs text-text-main font-mono">
              {report.raw_email}
            </pre>
          )}
        </div>

        {/* Attachments */}
        {report.attachments && report.attachments.length > 0 && (
          <div className="mt-4 pt-4 border-t border-surface-card-border">
            <h3 className="text-sm font-medium text-text-main mb-2">Attachments</h3>
            <ul className="space-y-1">
              {report.attachments.map((att, index) => (
                <li key={index} className="text-sm text-text-muted">
                  {att.filename || 'Unknown'} ({att.content_type || 'unknown type'})
                  {att.size && ` - ${(att.size / 1024).toFixed(2)} KB`}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default EmailViewer;

