/**
 * Campaign Progress Component
 * Visual progress tracking for audit campaigns
 */

'use client';

import { useCampaignProgress } from '@/lib/hooks/useCampaigns';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface CampaignProgressProps {
  campaignId: string;
}

const COLORS = {
  pending: '#F59E0B', // Yellow
  approved: '#10B981', // Green
  revoked: '#EF4444', // Red
};

function formatPieLabel(name: string, percent?: number) {
  return `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`;
}

export function CampaignProgress({ campaignId }: CampaignProgressProps) {
  const { data: progress, isLoading, error } = useCampaignProgress(campaignId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error || !progress) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800 text-sm">Error loading campaign progress</p>
      </div>
    );
  }

  const chartData = [
    { name: 'Approved/Retained', value: progress.approved, color: COLORS.approved },
    { name: 'Pending', value: progress.pending, color: COLORS.pending },
    { name: 'Revoked', value: progress.revoked, color: COLORS.revoked },
  ].filter((item) => item.value > 0);

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border p-6">
      <h3 className="text-lg font-semibold text-text-main mb-4">Campaign Progress</h3>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-text-muted">Overall Progress</span>
          <span className="text-sm font-semibold text-text-main">
            {progress.percentage_complete.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-surface-hover rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${progress.percentage_complete}%` }}
          />
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="text-center p-4 bg-surface-hover rounded-lg">
          <div className="text-2xl font-bold text-text-main">{progress.total}</div>
          <div className="text-sm text-text-muted mt-1">Total</div>
        </div>
        <div className="text-center p-4 bg-yellow-50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-800">{progress.pending}</div>
          <div className="text-sm text-yellow-600 mt-1">Pending</div>
        </div>
        <div className="text-center p-4 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-800">{progress.approved}</div>
          <div className="text-sm text-green-600 mt-1">Approved</div>
        </div>
        <div className="text-center p-4 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-800">{progress.revoked}</div>
          <div className="text-sm text-red-600 mt-1">Revoked</div>
        </div>
      </div>

      {/* Pie Chart */}
      {chartData.length > 0 && (
        <div className="mt-6">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => formatPieLabel(String(name), percent)}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
