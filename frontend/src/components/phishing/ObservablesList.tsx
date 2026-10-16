import React from 'react';
import { PhishingObservable } from '@/lib/api/phishing';
import clsx from 'clsx';

interface ObservablesListProps {
  observables: PhishingObservable[];
}

const getObservableTypeColor = (type: string) => {
  switch (type.toLowerCase()) {
    case 'url':
      return 'bg-blue-600';
    case 'domain':
      return 'bg-purple-600';
    case 'ip':
      return 'bg-orange-600';
    case 'email':
      return 'bg-green-600';
    case 'hash':
      return 'bg-border';
    default:
      return 'bg-surface-hover0';
  }
};

const getReputationColor = (score?: number) => {
  if (!score) return 'text-text-muted';
  if (score >= 70) return 'text-red-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-green-400';
};

const ObservablesList: React.FC<ObservablesListProps> = ({ observables }) => {
  if (observables.length === 0) {
    return (
      <div className="bg-surface-dark border border-surface-card-border rounded-lg p-6">
        <h2 className="text-xl font-semibold text-text-main mb-4">Observables</h2>
        <p className="text-text-muted">No observables extracted from this email.</p>
      </div>
    );
  }

  // Group observables by type
  const grouped = observables.reduce((acc, obs) => {
    if (!acc[obs.observable_type]) {
      acc[obs.observable_type] = [];
    }
    acc[obs.observable_type].push(obs);
    return acc;
  }, {} as Record<string, PhishingObservable[]>);

  return (
    <div className="bg-surface-dark border border-surface-card-border rounded-lg p-6">
      <h2 className="text-xl font-semibold text-text-main mb-4">
        Observables ({observables.length})
      </h2>

      <div className="space-y-6">
        {Object.entries(grouped).map(([type, items]) => (
          <div key={type}>
            <h3 className="text-sm font-medium text-text-main mb-2 flex items-center gap-2">
              <span
                className={clsx(
                  'px-2 py-1 rounded text-xs font-medium text-white',
                  getObservableTypeColor(type)
                )}
              >
                {type.toUpperCase()}
              </span>
              <span className="text-text-muted">({items.length})</span>
            </h3>
            <div className="space-y-2">
              {items.map((obs) => (
                <div
                  key={obs.id}
                  className="bg-surface-light border border-surface-card-border rounded-lg p-3"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-mono text-text-main break-all">
                        {obs.observable_value}
                      </p>
                      {obs.observable_context && (
                        <p className="text-xs text-text-muted mt-1">
                          {obs.observable_context}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1 ml-4">
                      {obs.reputation_score !== undefined && (
                        <span
                          className={clsx(
                            'text-xs font-medium',
                            getReputationColor(obs.reputation_score)
                          )}
                        >
                          Rep: {obs.reputation_score}
                        </span>
                      )}
                      {obs.is_malicious && (
                        <span className="px-2 py-1 rounded text-xs font-medium bg-red-600 text-white">
                          Malicious
                        </span>
                      )}
                    </div>
                  </div>
                  {obs.threat_intel && Object.keys(obs.threat_intel).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-text-muted cursor-pointer hover:text-text-main">
                        Threat Intelligence
                      </summary>
                      <pre className="mt-2 p-2 bg-surface-card rounded text-xs overflow-auto max-h-32">
                        {JSON.stringify(obs.threat_intel, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ObservablesList;

