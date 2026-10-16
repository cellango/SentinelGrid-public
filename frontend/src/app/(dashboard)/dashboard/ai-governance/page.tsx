/**
 * AI Governance Reporting — Leadership View
 * P5-07: AI usage, policy, and governance reporting for leadership
 */

'use client';

import { useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import clsx from 'clsx';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import AgentBadge from '@/components/ui/AgentBadge';
import {
  generateReport,
  getAIGovernanceSummary,
  getReportDownload,
  listReports,
  listTemplates,
} from '@/lib/api/reports';
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import { toast } from 'react-hot-toast';

const AIGovernanceInsights = dynamic(
  () => import('@/components/ai-governance/AIGovernanceInsights'),
  {
    loading: () => (
      <div className="rounded-xl border border-border-faint bg-surface-card p-8 text-sm text-text-muted">
        Loading AI governance insights…
      </div>
    ),
  }
);

function normalizeStatus(status?: string) {
  const value = (status || '').toLowerCase();
  return value === 'completed' ? 'ready' : value || 'unknown';
}

function triggerDownload(url: string, filename?: string) {
  const anchor = document.createElement('a');
  anchor.href = url;
  if (filename) anchor.download = filename;
  anchor.target = '_blank';
  anchor.rel = 'noopener noreferrer';
  anchor.click();
}

export default function AIGovernancePage() {
  const queryClient = useQueryClient();
  const [lookbackDays, setLookbackDays] = useState<number>(30);
  const [stateFilter, setStateFilter] = useState<'all' | 'needs_review' | 'guardrail_watch' | 'monitored' | 'unclassified'>('all');

  const { data, isLoading, error } = useQuery({
    queryKey: ['ai-governance-summary', lookbackDays],
    queryFn: () => getAIGovernanceSummary(lookbackDays),
  });

  const { data: templates = [] } = useQuery({
    queryKey: ['ai-governance-templates'],
    queryFn: () => listTemplates('ai_governance'),
  });

  const { data: reports = [] } = useQuery({
    queryKey: ['ai-governance-reports'],
    queryFn: () => listReports({ limit: 10, report_type: 'ai_governance' }),
  });

  const latestReadyReport = useMemo(
    () => reports.find((report) => normalizeStatus(report.status) === 'ready' && report.download_url),
    [reports]
  );

  const executiveTemplate = useMemo(
    () => templates.find((template) => template.name === 'AI Governance Executive Summary') || templates[0],
    [templates]
  );

  const exportMutation = useMutation({
    mutationFn: ({ format }: { format: 'pdf' | 'csv' }) => {
      if (!executiveTemplate) {
        throw new Error('No AI governance template available');
      }
      return generateReport({
        template_id: executiveTemplate.id,
        format,
      });
    },
    onSuccess: () => {
      toast.success('AI governance export generation started.');
      queryClient.invalidateQueries({ queryKey: ['ai-governance-reports'] });
    },
    onError: (mutationError: any) => {
      toast.error(mutationError?.response?.data?.detail || mutationError?.message || 'Failed to generate AI governance export');
    },
  });

  const filteredApps = useMemo(() => {
    const items = data?.app_inventory || [];
    if (stateFilter === 'all') return items;
    return items.filter((item) => item.governance_state === stateFilter);
  }, [data?.app_inventory, stateFilter]);

  const maxTrendRequests = useMemo(
    () => Math.max(...(data?.usage_trend || []).map((item) => item.requests), 1),
    [data?.usage_trend]
  );

  const handleDownloadLatest = async () => {
    if (!latestReadyReport?.download_url) return;
    try {
      const download = await getReportDownload(latestReadyReport.id);
      triggerDownload(download.download_url, `ai-governance-${latestReadyReport.id}.${String(latestReadyReport.format).toLowerCase()}`);
    } catch (downloadError: any) {
      toast.error(downloadError?.response?.data?.detail || 'Failed to prepare AI governance export download');
    }
  };

  return (
    <div className="px-6 py-6 max-w-7xl mx-auto">
      <Breadcrumbs />
      <div className="mt-2 mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-xl font-bold text-text-main flex items-center gap-2">
            AI Governance
            <AgentBadge agentId="ai_shield_agent" variant="pill" />
          </h1>
          <p className="text-sm text-text-muted mt-0.5">
            Leadership reporting for AI usage, policy pressure, and elevated AI risk across the tenant
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {[30, 60, 90].map((days) => (
            <button
              key={days}
              onClick={() => setLookbackDays(days)}
              className={clsx(
                'min-h-[40px] rounded-lg border px-3 py-2 text-sm transition-colors',
                lookbackDays === days
                  ? 'border-primary/30 bg-primary/15 text-primary'
                  : 'border-border-faint text-text-muted hover:border-border-strong hover:text-text-main'
              )}
            >
              {days}d window
            </button>
          ))}
          <button
            onClick={() => exportMutation.mutate({ format: 'pdf' })}
            disabled={!executiveTemplate || exportMutation.isPending}
            className="inline-flex min-h-[40px] items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-950 transition-all hover:brightness-110 disabled:opacity-60"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Export PDF
          </button>
          <button
            onClick={() => exportMutation.mutate({ format: 'csv' })}
            disabled={!executiveTemplate || exportMutation.isPending}
            className="inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-border-strong px-4 py-2 text-sm text-text-main transition-colors hover:border-primary disabled:opacity-60"
          >
            Export CSV
          </button>
        </div>
      </div>

      {data?.top_risk && (
        <div className="mb-6 rounded-xl border border-rose-500/20 bg-rose-500/10 p-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rose-300">
            Highest current AI case
          </p>
          <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-text-main">{data.top_risk.title}</h2>
              <p className="mt-2 text-sm text-text-muted">{data.top_risk.summary}</p>
            </div>
            <a
              href={data.top_risk.href}
              className="inline-flex min-h-[40px] items-center rounded-lg border border-border-strong px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
            >
              Open case
            </a>
          </div>
        </div>
      )}

      {latestReadyReport && (
        <div className="mb-6 rounded-xl border border-border-faint bg-surface-card p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">Latest leadership export</p>
              <p className="mt-1 text-sm font-medium text-text-main">{latestReadyReport.name}</p>
              <p className="mt-1 text-xs text-text-muted">
                Generated {latestReadyReport.generated_at ? new Date(latestReadyReport.generated_at).toLocaleString() : 'recently'}
              </p>
            </div>
            <button
              onClick={handleDownloadLatest}
              className="inline-flex min-h-[40px] items-center gap-2 rounded-lg border border-border-strong px-3 py-2 text-sm text-text-main transition-colors hover:border-primary"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Download latest
            </button>
          </div>
        </div>
      )}

      {isLoading && (
        <div className="rounded-xl border border-border-faint bg-surface-card p-8 text-sm text-text-muted">
          Loading AI governance reporting...
        </div>
      )}

      {error && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-8 text-sm text-rose-200">
          Failed to load AI governance reporting.
        </div>
      )}

      {data && (
        <AIGovernanceInsights
          data={data}
          filteredApps={filteredApps}
          lookbackDays={lookbackDays}
          maxTrendRequests={maxTrendRequests}
          stateFilter={stateFilter}
          setStateFilter={setStateFilter}
        />
      )}
    </div>
  );
}
