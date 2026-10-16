/**
 * Compliance Remediation Page
 * View and manage compliance findings remediation
 */

'use client';

import { useState } from 'react';
import FindingsList from '@/components/compliance/FindingsList';
import ComplianceDashboard from '@/components/compliance/ComplianceDashboard';

export default function ComplianceRemediationPage() {
  const [selectedFinding, setSelectedFinding] = useState<{
    id: string;
    type: 'iam_finding' | 'posture_finding';
  } | null>(null);
  const [view, setView] = useState<'list' | 'dashboard'>('list');

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-main">Compliance Remediation</h1>
          <p className="mt-1 text-sm text-text-muted">View findings and manage remediation workflows</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView('list')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              view === 'list'
                ? 'bg-primary text-white'
                : 'border border-border-faint bg-surface-hover text-text-main hover:bg-surface-input'
            }`}
          >
            Findings
          </button>
          <button
            onClick={() => setView('dashboard')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              view === 'dashboard'
                ? 'bg-primary text-white'
                : 'border border-border-faint bg-surface-hover text-text-main hover:bg-surface-input'
            }`}
          >
            Dashboard
          </button>
        </div>
      </div>

      {/* Content */}
      {view === 'list' ? (
        <FindingsList
          onSelectFinding={(finding) => setSelectedFinding(finding)}
          selectedFinding={selectedFinding}
        />
      ) : (
        <ComplianceDashboard />
      )}
    </div>
  );
}
