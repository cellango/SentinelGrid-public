'use client';

import { getSIEMStats } from '@/lib/api/siem';
import { useQuery } from '@tanstack/react-query';
import { PlanGate } from '@/components/PlanGate';

export default function SIEMPage() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['siem-stats'],
    queryFn: () => getSIEMStats(),
  });

  return (
    <PlanGate
      requiredTier="protect_defend"
      title="Unlock SIEM & response"
      description="Full detection engineering, alert triage, and response orchestration are available on the Protect + Defend plan."
    >
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-text-main mb-2">Detections &amp; Response</h1>
          <p className="text-text-muted">Build and monitor detection rules and recommended responses</p>
        </div>

        {isLoading ? (
          <div className="text-text-muted">Loading detection statistics...</div>
        ) : (
          <div className="grid gap-6 md:grid-cols-3">
            <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
              <h2 className="text-lg font-semibold mb-2 text-text-main">Total Events</h2>
              <p className="text-3xl font-bold text-primary">{stats?.events_count?.toLocaleString() || 0}</p>
              <p className="text-sm text-text-muted mt-2">Events processed</p>
            </div>
            <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
              <h2 className="text-lg font-semibold mb-2 text-text-main">Total Alerts</h2>
              <p className="text-3xl font-bold text-primary">{stats?.alerts_count || 0}</p>
              <p className="text-sm text-text-muted mt-2">Alerts generated</p>
            </div>
            <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
              <h2 className="text-lg font-semibold mb-2 text-text-main">Status</h2>
              <p className="text-3xl font-bold text-green-500">Active</p>
              <p className="text-sm text-text-muted mt-2">Detection pipeline is operational</p>
            </div>
          </div>
        )}

        <div className="mt-6 bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
          <h2 className="text-xl font-semibold mb-4 text-text-main">What you can do</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
              <h3 className="font-semibold text-text-main mb-2">Event Search</h3>
              <p className="text-sm text-text-muted">Search and analyze security events across your infrastructure</p>
            </div>
            <div className="p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
              <h3 className="font-semibold text-text-main mb-2">Entity Timeline</h3>
              <p className="text-sm text-text-muted">View chronological timeline of events for users, hosts, and IPs</p>
            </div>
            <div className="p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
              <h3 className="font-semibold text-text-main mb-2">Alert Management</h3>
              <p className="text-sm text-text-muted">Create, manage, and investigate security alerts</p>
            </div>
            <div className="p-4 rounded-lg border border-[rgba(15,23,42,0.9)]">
              <h3 className="font-semibold text-text-main mb-2">Statistics & Analytics</h3>
              <p className="text-sm text-text-muted">View aggregated statistics and security metrics</p>
            </div>
          </div>
        </div>
      </div>
    </PlanGate>
  );
}
