/**
 * Day 0-1 Empty State
 * Shows when data is still processing
 */

'use client';

import Link from 'next/link';

interface EmptyStateProps {
  hoursUntilData?: number;
}

export default function EmptyState({ hoursUntilData = 3 }: EmptyStateProps) {
  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-8 text-center">
      <div className="text-5xl mb-4">⏳</div>
      <h3 className="text-xl font-semibold text-text-main mb-2">Preparing Your First Findings</h3>
      <p className="text-text-muted mb-6 max-w-md mx-auto">
        SentinelGrid is normalizing the first data from your core integrations. The fastest path is your primary identity provider plus AWS, then endpoint coverage.
        Your security score and recommendations usually appear within a few hours after that data starts flowing.
      </p>

      <div className="bg-primary/10 border border-primary/20 rounded-xl p-4 mb-6 text-left max-w-md mx-auto">
        <p className="text-sm font-medium text-text-main mb-2">What you'll see here over the next 24 hours:</p>
        <ul className="space-y-1 text-sm text-text-muted">
          <li>• Your first security score</li>
          <li>• Any obvious misconfigurations or risky accounts</li>
          <li>• Recommended quick wins tailored to your setup</li>
        </ul>
      </div>

      <div className="flex flex-wrap gap-2 justify-center">
        <Link
          href="/onboarding"
          className="px-4 py-2 bg-primary/20 text-primary rounded-xl hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/30"
        >
          Complete Onboarding
        </Link>
        <Link
          href="/dashboard/endpoint-protection"
          className="px-4 py-2 bg-[rgba(15,23,42,0.9)] border border-primary/10 text-text-main rounded-xl hover:border-primary/30 transition-colors text-sm font-medium"
        >
          Install Endpoint Protection
        </Link>
      </div>
    </div>
  );
}
