'use client'

import { useEffect, useState } from 'react'
import { FindingsTable } from '@/components/posture/FindingsTable'
import { apiClient, type Finding } from '@/lib/api-client'

export default function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    loadFindings();
  }, [severityFilter, statusFilter]);

  const loadFindings = async () => {
    try {
      setLoading(true);
      const tenantId = 'default-tenant';

      const data = await apiClient.listFindings({
        tenant_id: tenantId,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit: 100,
      });

      setFindings(data);
    } catch (error) {
      console.error('Error loading findings:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Security Findings</h1>
        <p className="text-muted-foreground">
          All security findings from posture scans
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium mb-2">Severity</label>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="border rounded-md px-3 py-2"
          >
            <option value="">All</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="border rounded-md px-3 py-2"
          >
            <option value="">All</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="fixed">Fixed</option>
            <option value="accepted">Accepted Risk</option>
          </select>
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading findings...</p>
        </div>
      ) : (
        <>
          <div className="mb-4 text-sm text-muted-foreground">
            Showing {findings.length} findings
          </div>
          <FindingsTable findings={findings} />
        </>
      )}
    </div>
  );
}

