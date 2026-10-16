'use client'

import { AlertCircle, AlertTriangle, Info } from 'lucide-react'
import type { Finding } from '@/lib/api-client'

interface FindingsTableProps {
  findings: Finding[];
  onFindingClick?: (finding: Finding) => void;
}

export function FindingsTable({ findings, onFindingClick }: FindingsTableProps) {
  const getSeverityBadge = (severity: string) => {
    const config = {
      critical: { color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100', icon: AlertCircle },
      high: { color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100', icon: AlertTriangle },
      medium: { color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100', icon: AlertTriangle },
      low: { color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100', icon: Info },
      info: { color: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100', icon: Info },
    };

    const { color, icon: Icon } = config[severity as keyof typeof config] || config.info;

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${color}`}>
        <Icon className="h-3 w-3" />
        {severity.toUpperCase()}
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    const config = {
      open: 'bg-red-50 text-red-700 border-red-200',
      in_progress: 'bg-yellow-50 text-yellow-700 border-yellow-200',
      fixed: 'bg-green-50 text-green-700 border-green-200',
      accepted: 'bg-blue-50 text-blue-700 border-blue-200',
      false_positive: 'bg-gray-50 text-gray-700 border-gray-200',
    };

    const color = config[status as keyof typeof config] || config.open;

    return (
      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium border ${color}`}>
        {status.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  if (findings.length === 0) {
    return (
      <div className="border rounded-lg p-12 text-center text-muted-foreground">
        <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>No findings to display</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full">
        <thead className="bg-muted">
          <tr>
            <th className="text-left p-4 font-semibold">Severity</th>
            <th className="text-left p-4 font-semibold">Title</th>
            <th className="text-left p-4 font-semibold">Tool</th>
            <th className="text-left p-4 font-semibold">Status</th>
            <th className="text-left p-4 font-semibold">Found</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((finding) => (
            <tr
              key={finding.id}
              onClick={() => onFindingClick?.(finding)}
              className="border-t hover:bg-muted/50 cursor-pointer transition-colors"
            >
              <td className="p-4">
                {getSeverityBadge(finding.severity)}
              </td>
              <td className="p-4">
                <div className="font-medium">{finding.title}</div>
                {finding.description && (
                  <div className="text-sm text-muted-foreground truncate max-w-md">
                    {finding.description}
                  </div>
                )}
              </td>
              <td className="p-4">
                <span className="text-sm font-mono bg-muted px-2 py-1 rounded">
                  {finding.tool}
                </span>
              </td>
              <td className="p-4">
                {getStatusBadge(finding.status)}
              </td>
              <td className="p-4 text-sm text-muted-foreground">
                {new Date(finding.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

