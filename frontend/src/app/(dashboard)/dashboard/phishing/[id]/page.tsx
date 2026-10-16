'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import {
  getPhishingReport,
  getPhishingObservables,
  classifyPhishingReport,
  updatePhishingReport,
  PhishingReport,
  PhishingObservable,
} from '@/lib/api/phishing';
import { runContainmentPlaybook } from '@/lib/api/phishing';
import EmailViewer from '@/components/phishing/EmailViewer';
import AIAnalysis from '@/components/phishing/AIAnalysis';
import ObservablesList from '@/components/phishing/ObservablesList';
import ActionButtons from '@/components/phishing/ActionButtons';
import { toast } from 'react-hot-toast';
import clsx from 'clsx';

export default function PhishingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const reportId = params.id as string;
  const [activeTab, setActiveTab] = useState<'overview' | 'observables' | 'timeline'>('overview');

  const tenantId = typeof window !== 'undefined'
    ? localStorage.getItem('tenant_id') || ''
    : '';

  const { data: report, isLoading, error, refetch } = useQuery<PhishingReport, Error>({
    queryKey: ['phishingReport', reportId, tenantId],
    queryFn: () => getPhishingReport(reportId, tenantId),
    enabled: !!reportId && !!tenantId,
  });

  const { data: observables } = useQuery<PhishingObservable[], Error>({
    queryKey: ['phishingObservables', reportId, tenantId],
    queryFn: () => getPhishingObservables(reportId, tenantId),
    enabled: !!reportId && !!tenantId,
  });

  const classifyMutation = useMutation({
    mutationFn: () => classifyPhishingReport(reportId, tenantId),
    onSuccess: () => {
      toast.success('Classification triggered successfully');
      queryClient.invalidateQueries({ queryKey: ['phishingReport', reportId] });
      refetch();
    },
    onError: (error: Error) => {
      toast.error(`Failed to classify: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (updates: { classification?: string; status?: string; severity?: string }) =>
      updatePhishingReport(reportId, tenantId, updates),
    onSuccess: () => {
      toast.success('Report updated successfully');
      queryClient.invalidateQueries({ queryKey: ['phishingReport', reportId] });
      refetch();
    },
    onError: (error: Error) => {
      toast.error(`Failed to update report: ${error.message}`);
    },
  });

  const containmentMutation = useMutation({
    mutationFn: () => runContainmentPlaybook(reportId, tenantId),
    onSuccess: (result) => {
      toast.success(`Containment playbook completed. ${result.similar_emails_found} similar emails found.`);
      queryClient.invalidateQueries({ queryKey: ['phishingReport', reportId] });
      refetch();
    },
    onError: (error: Error) => {
      toast.error(`Failed to run containment playbook: ${error.message}`);
    },
  });

  useEffect(() => {
    if (error) {
      toast.error(`Failed to load phishing report: ${error.message}`);
    }
  }, [error]);

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 animate-pulse">
        <div className="h-8 bg-bg-alt rounded w-3/4 mb-4"></div>
        <div className="h-4 bg-bg-alt rounded w-1/2 mb-6"></div>
        <div className="h-64 bg-bg-alt rounded"></div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="container mx-auto p-6 text-center text-text-muted">
        <h1 className="text-2xl font-bold mb-4">Report Not Found</h1>
        <p>The phishing report with ID "{reportId}" could not be loaded.</p>
        <button
          onClick={() => router.push('/dashboard/phishing')}
          className="mt-4 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-dark"
        >
          Back to Queue
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <Breadcrumbs />
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button
            onClick={() => router.push('/dashboard/phishing')}
            className="text-text-muted hover:text-text-main mb-2"
          >
            ← Back to Queue
          </button>
          <h1 className="text-3xl font-bold text-text-main">
            {report.subject || '(No Subject)'}
          </h1>
          <p className="text-text-muted mt-1">
            From: {report.from_address} • Received: {new Date(report.received_date).toLocaleString()}
          </p>
        </div>
        <ActionButtons
          report={report}
          onClassify={() => classifyMutation.mutate()}
          onUpdate={(updates) => updateMutation.mutate(updates)}
          isClassifying={classifyMutation.isPending}
          onRunContainment={() => containmentMutation.mutate()}
          isRunningContainment={containmentMutation.isPending}
        />
      </div>

      {/* Status Badges */}
      <div className="flex flex-wrap gap-2 mb-6">
        {report.classification && (
          <span
            className={clsx(
              'px-3 py-1 rounded-full text-sm font-medium',
              report.classification === 'phishing'
                ? 'bg-red-600 text-white'
                : report.classification === 'benign'
                ? 'bg-green-600 text-white'
                : 'bg-yellow-600 text-white'
            )}
          >
            {report.classification}
          </span>
        )}
        {report.severity && (
          <span
            className={clsx(
              'px-3 py-1 rounded-full text-sm font-medium',
              report.severity === 'critical'
                ? 'bg-red-500 text-white'
                : report.severity === 'high'
                ? 'bg-orange-500 text-white'
                : report.severity === 'medium'
                ? 'bg-yellow-500 text-white'
                : 'bg-green-500 text-white'
            )}
          >
            {report.severity.toUpperCase()}
          </span>
        )}
        <span className="px-3 py-1 rounded-full text-sm font-medium bg-border text-white">
          {report.status.replace('_', ' ')}
        </span>
        {report.classification_confidence !== undefined && (
          <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-600 text-white">
            {report.classification_confidence.toFixed(1)}% Confidence
          </span>
        )}
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-surface-card-border mb-6">
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {[
            { id: 'overview', label: 'Overview' },
            { id: 'observables', label: 'Observables' },
            { id: 'timeline', label: 'Timeline' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={clsx(
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:text-text-main hover:border-border',
                'whitespace-nowrap py-3 px-1 border-b-2 font-medium text-sm'
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {activeTab === 'overview' && (
          <div className="space-y-6">
            <EmailViewer report={report} />
            <AIAnalysis report={report} />
          </div>
        )}
        {activeTab === 'observables' && (
          <ObservablesList observables={observables || []} />
        )}
        {activeTab === 'timeline' && (
          <div className="bg-surface-dark p-6 rounded-lg">
            <h2 className="text-xl font-semibold text-text-main mb-4">Timeline</h2>
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="w-2 h-2 rounded-full bg-primary mt-2"></div>
                <div>
                  <p className="text-sm font-medium text-text-main">
                    Report Created
                  </p>
                  <p className="text-xs text-text-muted">
                    {new Date(report.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              {report.classified_at && (
                <div className="flex items-start gap-4">
                  <div className="w-2 h-2 rounded-full bg-green-500 mt-2"></div>
                  <div>
                    <p className="text-sm font-medium text-text-main">
                      AI Classification ({report.classified_by})
                    </p>
                    <p className="text-xs text-text-muted">
                      {new Date(report.classified_at).toLocaleString()}
                    </p>
                    <p className="text-sm text-text-muted mt-1">
                      Classification: {report.classification} ({report.classification_confidence}% confidence)
                    </p>
                  </div>
                </div>
              )}
              <div className="flex items-start gap-4">
                <div className="w-2 h-2 rounded-full bg-surface-hover0 mt-2"></div>
                <div>
                  <p className="text-sm font-medium text-text-main">
                    Last Updated
                  </p>
                  <p className="text-xs text-text-muted">
                    {new Date(report.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
