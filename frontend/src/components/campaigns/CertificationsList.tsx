/**
 * Certifications List Component
 * Displays certifications for a campaign
 */

'use client';

import { useQuery } from '@tanstack/react-query';
import { certificationsApi, type Certification } from '@/lib/api/governance';
import { format } from 'date-fns';

interface CertificationsListProps {
  campaignId: string;
}

export function CertificationsList({ campaignId }: CertificationsListProps) {
  const { data: certifications, isLoading, error } = useQuery({
    queryKey: ['certifications', campaignId],
    queryFn: () => certificationsApi.list({ campaign_id: campaignId, limit: 100 }),
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'approved':
      case 'retained':
        return 'bg-green-100 text-green-800';
      case 'revoked':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-bg-alt text-text-main';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800 text-sm">Error loading certifications</p>
      </div>
    );
  }

  if (!certifications || certifications.length === 0) {
    return (
      <div className="bg-surface-hover border border-surface-card-border rounded-lg p-8 text-center">
        <p className="text-text-muted">No certifications found for this campaign.</p>
        <p className="text-sm text-text-muted mt-2">Start the campaign to generate certifications.</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-card rounded-lg shadow-sm border border-surface-card-border overflow-hidden">
      <div className="px-6 py-4 border-b border-surface-card-border">
        <h3 className="text-lg font-semibold text-text-main">Certifications</h3>
        <p className="text-sm text-text-muted mt-1">{certifications.length} total certifications</p>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-surface-hover">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Reviewed Date
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">
                Comments
              </th>
            </tr>
          </thead>
          <tbody className="bg-surface-card divide-y divide-border">
            {certifications.map((cert) => (
              <tr key={cert.id} className="hover:bg-surface-hover">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-text-main">
                    {cert.user_id.substring(0, 8)}...
                  </div>
                  <div className="text-sm text-text-muted">User ID</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(
                      cert.review_status
                    )}`}
                  >
                    {cert.review_status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted">
                  {cert.review_date ? format(new Date(cert.review_date), 'MMM d, yyyy') : '-'}
                </td>
                <td className="px-6 py-4 text-sm text-text-muted">
                  {cert.comments ? (
                    <span className="truncate max-w-xs block" title={cert.comments}>
                      {cert.comments}
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

