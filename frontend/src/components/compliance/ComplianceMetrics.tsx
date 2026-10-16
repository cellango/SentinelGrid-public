/**
 * Compliance Metrics Component
 * Charts and KPIs for compliance dashboard
 */

'use client';

import { ComplianceReport } from '@/lib/api/compliance';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface ComplianceMetricsProps {
  report: ComplianceReport;
}

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

function formatPieLabel(name: string, percent?: number) {
  return `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`;
}

export function ComplianceMetrics({ report }: ComplianceMetricsProps) {
  // Status distribution data
  const statusData = [
    { name: 'Active', value: report.active_entitlements, color: '#10B981' },
    { name: 'Revoked', value: report.revoked_entitlements, color: '#EF4444' },
    { name: 'Expired', value: report.expired_entitlements, color: '#F59E0B' },
    { name: 'Pending Review', value: report.pending_review, color: '#3B82F6' },
  ].filter((item) => item.value > 0);

  // Resource type distribution
  const resourceTypeData = Object.entries(report.entitlements_by_resource_type)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10); // Top 10

  // Action distribution
  const actionData = Object.entries(report.entitlements_by_action)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);

  return (
    <div className="space-y-6">
      {/* Status Distribution Pie Chart */}
      <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
        <h3 className="text-lg font-semibold text-text-main mb-4">Entitlement Status Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={statusData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => formatPieLabel(String(name), percent)}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {statusData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Resource Type Distribution */}
      {resourceTypeData.length > 0 && (
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <h3 className="text-lg font-semibold text-text-main mb-4">Entitlements by Resource Type</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={resourceTypeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#3B82F6" name="Count" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Action Distribution */}
      {actionData.length > 0 && (
        <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
          <h3 className="text-lg font-semibold text-text-main mb-4">Entitlements by Action</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={actionData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#10B981" name="Count" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
