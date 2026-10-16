import React from 'react';

interface StepTicketingProps {
  ticketingChoice: 'sentinelgrid' | 'jira' | 'servicenow';
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
}

export default function StepTicketing({
  ticketingChoice,
  onNext,
  onBack,
  onSkip,
}: StepTicketingProps) {
  const showIntegration = ticketingChoice === 'jira' || ticketingChoice === 'servicenow';

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-300">
        Ticketing integration for incident and scan findings. If you chose Jira or ServiceNow, add a connection;
        otherwise we&apos;ll use SentinelGrid ticketing.
      </p>

      {showIntegration ? (
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-300 mb-1">Base URL</label>
            <input
              type="text"
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
              placeholder={ticketingChoice === 'jira' ? 'https://your-domain.atlassian.net' : 'https://instance.service-now.com'}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">
              {ticketingChoice === 'jira' ? 'Project Key' : 'Assignment group / short description prefix'}
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
              placeholder={ticketingChoice === 'jira' ? 'SEC' : 'Security Incidents'}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-300 mb-1">API Token / Credentials</label>
            <input
              type="password"
              className="w-full rounded-lg border border-slate-700 bg-slate-950/60 px-3 py-2 text-sm text-slate-200"
              placeholder="API token"
            />
            <p className="text-xs text-slate-400 mt-1">
              We store credentials securely and use them only to create/update tickets.
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-800 rounded-lg px-4 py-3 text-xs text-slate-300">
          Using SentinelGrid ticketing by default. You can switch to Jira or ServiceNow later in Settings.
        </div>
      )}

      <div className="flex justify-between pt-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs text-slate-300 hover:text-slate-100"
        >
          ← Back
        </button>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onSkip}
            className="text-xs text-slate-300 hover:text-slate-100"
          >
            Skip for now →
          </button>
          <button
            type="button"
            onClick={onNext}
            className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}
