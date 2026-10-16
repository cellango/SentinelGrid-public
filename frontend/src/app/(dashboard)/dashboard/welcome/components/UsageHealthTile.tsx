/**
 * Usage & Health Tile
 * Shows system usage and integration health
 */

'use client';

import Link from 'next/link';
import { DashboardHealth } from '@/lib/api/dashboard';

interface UsageHealthTileProps {
  health: DashboardHealth;
}

export default function UsageHealthTile({ health }: UsageHealthTileProps) {
  const safeHealthStatus = typeof health.health_status === 'string' ? health.health_status : 'unknown';
  const getIntegrationIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return '✅';
      case 'partial':
        return '🟡';
      default:
        return '❌';
    }
  };

  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-400';
      case 'degraded':
        return 'text-yellow-400';
      default:
        return 'text-red-400';
    }
  };

  const logUsagePercent = Math.round(health.log_usage.percentage_used);
  const agentOnlinePercent = Math.round(health.agents.percentage_online);

  return (
    <div className="bg-[rgba(15,23,42,0.9)] backdrop-blur-md rounded-2xl border border-primary/20 p-6 hover:border-primary/40 transition-all">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-text-main mb-1">System Health</h3>
        <p className={`text-sm font-medium ${getHealthColor(safeHealthStatus)}`}>
          {safeHealthStatus.charAt(0).toUpperCase() + safeHealthStatus.slice(1)}
        </p>
      </div>

      <div className="space-y-3 mb-4">
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-muted">Log Usage</span>
            <span className="text-sm font-semibold text-text-main">
              {health.log_usage.current_gb_per_day.toFixed(1)} / {health.log_usage.limit_gb_per_day} GB/day
            </span>
          </div>
          <div className="h-2 bg-[rgba(15,23,42,0.9)] rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                logUsagePercent < 80
                  ? 'bg-green-500/20 border-green-500/30'
                  : logUsagePercent < 95
                  ? 'bg-yellow-500/20 border-yellow-500/30'
                  : 'bg-red-500/20 border-red-500/30'
              }`}
              style={{ width: `${logUsagePercent}%` }}
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-text-muted">Agents Online</span>
            <span className="text-sm font-semibold text-text-main">
              {health.agents.online} / {health.agents.total}
            </span>
          </div>
          <div className="h-2 bg-[rgba(15,23,42,0.9)] rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                agentOnlinePercent >= 80
                  ? 'bg-green-500/20 border-green-500/30'
                  : agentOnlinePercent >= 50
                  ? 'bg-yellow-500/20 border-yellow-500/30'
                  : 'bg-red-500/20 border-red-500/30'
              }`}
              style={{ width: `${agentOnlinePercent}%` }}
            />
          </div>
        </div>

        <div className="pt-2 border-t border-primary/10">
          <p className="text-xs text-text-muted mb-2">Integrations</p>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5">
              <span>{getIntegrationIcon(health.integrations.aws)}</span>
              <span className="text-text-muted">AWS</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span>{getIntegrationIcon(health.integrations.idp)}</span>
              <span className="text-text-muted">IdP</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span>{getIntegrationIcon(health.integrations.endpoint)}</span>
              <span className="text-text-muted">Endpoint</span>
            </div>
          </div>
        </div>
      </div>

      {logUsagePercent < 80 && agentOnlinePercent >= 80 && (
        <p className="text-xs text-text-muted mb-3">
          ✓ Within plan limits
        </p>
      )}

      <Link
        href="/dashboard/settings/usage"
        className="text-xs text-primary hover:text-primary/80 transition-colors"
      >
        View usage details →
      </Link>
    </div>
  );
}
