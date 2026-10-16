'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  LinkIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import {
  decideComplianceAgentRecommendation,
  listComplianceAgentRecommendations,
  type ComplianceAgentRecommendation,
} from '@/lib/api/compliance';

type WorkbenchFilter = 'all' | 'missing_evidence' | 'high_risk_gaps' | 'collection_tasks' | 'report_drafts';

type SourceLink = {
  href: string;
  label: string;
};

const FILTER_LABELS: Record<WorkbenchFilter, string> = {
  all: 'All',
  missing_evidence: 'Missing evidence',
  high_risk_gaps: 'High-risk gaps',
  collection_tasks: 'Collection tasks',
  report_drafts: 'Report drafts',
};

function normalizeLabel(value?: string | null) {
  if (!value) return 'Not set';
  return value.replace(/_/g, ' ');
}

function formatDateTime(value?: string | null) {
  if (!value) return 'Not set';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function priorityClasses(priority?: string | null) {
  switch ((priority || '').toLowerCase()) {
    case 'critical':
      return 'border-rose-200 bg-rose-50 text-rose-700';
    case 'high':
      return 'border-orange-200 bg-orange-50 text-orange-700';
    case 'low':
      return 'border-slate-200 bg-slate-50 text-slate-700';
    default:
      return 'border-amber-200 bg-amber-50 text-amber-700';
  }
}

function hasAction(recommendation: ComplianceAgentRecommendation, expected: string) {
  const needle = expected.toLowerCase();
  return recommendation.proposed_actions.some((action) =>
    [action.action, action.tool]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(needle))
  );
}

function isMissingEvidence(recommendation: ComplianceAgentRecommendation) {
  return (
    recommendation.source_type === 'evidence' ||
    recommendation.trigger_type === 'evidence_expired' ||
    recommendation.trigger_type === 'evidence_expiring'
  );
}

function isHighRiskGap(recommendation: ComplianceAgentRecommendation) {
  return (
    recommendation.source_type === 'control_gap' ||
    recommendation.trigger_type === 'high_priority_control_gap_detected' ||
    recommendation.priority === 'critical' ||
    recommendation.priority === 'high'
  );
}

function isCollectionTask(recommendation: ComplianceAgentRecommendation) {
  return (
    recommendation.recommendation_type === 'create_evidence_collection_task' ||
    hasAction(recommendation, 'create_evidence_collection_task') ||
    hasAction(recommendation, 'collect_evidence')
  );
}

function isReportDraft(recommendation: ComplianceAgentRecommendation) {
  return (
    recommendation.source_type === 'report' ||
    recommendation.trigger_type === 'report_generation_requested' ||
    recommendation.recommendation_type === 'generate_compliance_report' ||
    hasAction(recommendation, 'report')
  );
}

function matchesFilter(recommendation: ComplianceAgentRecommendation, filter: WorkbenchFilter) {
  if (filter === 'all') return true;
  if (filter === 'missing_evidence') return isMissingEvidence(recommendation);
  if (filter === 'high_risk_gaps') return isHighRiskGap(recommendation);
  if (filter === 'collection_tasks') return isCollectionTask(recommendation);
  return isReportDraft(recommendation);
}

function sourceLinkFor(recommendation: ComplianceAgentRecommendation): SourceLink {
  const reportId = recommendation.report_id || (recommendation.source_type === 'report' ? recommendation.source_id : null);
  if (reportId) {
    return {
      href: `/dashboard/compliance/reports?report_id=${encodeURIComponent(reportId)}`,
      label: 'Open report',
    };
  }

  const evidenceId = recommendation.evidence_item_id || (recommendation.source_type === 'evidence' ? recommendation.source_id : null);
  if (evidenceId) {
    return {
      href: `/dashboard/compliance/evidence?evidence_id=${encodeURIComponent(evidenceId)}`,
      label: 'Open evidence',
    };
  }

  if (recommendation.evidence_package_id) {
    return {
      href: `/dashboard/compliance/evidence?package_id=${encodeURIComponent(recommendation.evidence_package_id)}`,
      label: 'Open evidence package',
    };
  }

  if (recommendation.control_id) {
    return {
      href: `/dashboard/compliance?control=${encodeURIComponent(recommendation.control_id)}`,
      label: 'Open control',
    };
  }

  if (recommendation.framework_id) {
    return {
      href: `/dashboard/compliance?framework=${encodeURIComponent(recommendation.framework_id)}`,
      label: 'Open framework',
    };
  }

  return {
    href: '/dashboard/compliance',
    label: 'Open compliance context',
  };
}

function actionSummary(recommendation: ComplianceAgentRecommendation) {
  const [action] = recommendation.proposed_actions;
  if (!action) return 'No action payload recorded';
  const actionName = String(action.action || action.tool || recommendation.recommendation_type);
  const args = action.arguments || {};
  const taskName = typeof args.task_name === 'string' ? args.task_name : null;
  return taskName ? `${normalizeLabel(actionName)} - ${taskName}` : normalizeLabel(actionName);
}

function recommendationIdentity(recommendation: ComplianceAgentRecommendation) {
  return [
    recommendation.framework_id,
    recommendation.control_id,
    recommendation.source_type ? normalizeLabel(recommendation.source_type) : null,
  ]
    .filter(Boolean)
    .join(' / ');
}

export function ComplianceAgentWorkbenchPanel() {
  const queryClient = useQueryClient();
  const [activeFilter, setActiveFilter] = useState<WorkbenchFilter>('all');

  const recommendationsQuery = useQuery({
    queryKey: ['compliance-agent-recommendations', 'proposed'],
    queryFn: () => listComplianceAgentRecommendations({ state: 'proposed', limit: 50 }),
  });

  const recommendations = recommendationsQuery.data?.items || [];
  const counts = useMemo(() => {
    return (Object.keys(FILTER_LABELS) as WorkbenchFilter[]).reduce<Record<WorkbenchFilter, number>>(
      (accumulator, filter) => {
        accumulator[filter] = recommendations.filter((recommendation) => matchesFilter(recommendation, filter)).length;
        return accumulator;
      },
      {
        all: 0,
        missing_evidence: 0,
        high_risk_gaps: 0,
        collection_tasks: 0,
        report_drafts: 0,
      }
    );
  }, [recommendations]);

  const visibleRecommendations = useMemo(
    () => recommendations.filter((recommendation) => matchesFilter(recommendation, activeFilter)),
    [activeFilter, recommendations]
  );

  const decisionMutation = useMutation({
    mutationFn: ({
      recommendationId,
      state,
    }: {
      recommendationId: string;
      state: 'accepted' | 'rejected';
    }) =>
      decideComplianceAgentRecommendation(recommendationId, {
        state,
        decision_notes:
          state === 'accepted'
            ? 'Approved from the Compliance Agent workbench.'
            : 'Rejected from the Compliance Agent workbench.',
      }),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({ queryKey: ['compliance-agent-recommendations'] });
      queryClient.invalidateQueries({ queryKey: ['compliance-dashboard'] });
      toast.success(variables.state === 'accepted' ? 'Recommendation approved.' : 'Recommendation rejected.');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to update recommendation.');
    },
  });

  return (
    <div className="mb-8 rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ClipboardDocumentListIcon className="h-6 w-6 text-primary" aria-hidden="true" />
            <h2 className="text-xl font-semibold text-text-main">Compliance Agent Workbench</h2>
          </div>
          <p className="mt-1 text-sm text-text-muted">
            Review supervised recommendations for evidence, gap, collection, and report actions before anything changes.
            Generated output is not an audit attestation.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-text-muted">
          {recommendationsQuery.isFetching && <ArrowPathIcon className="h-4 w-4 animate-spin" aria-hidden="true" />}
          <span>{recommendationsQuery.data?.count ?? recommendations.length} proposed</span>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="Compliance Agent recommendation filters">
        {(Object.keys(FILTER_LABELS) as WorkbenchFilter[]).map((filter) => {
          const active = activeFilter === filter;
          return (
            <button
              key={filter}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveFilter(filter)}
              className={`inline-flex items-center rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? 'border-primary bg-primary text-white'
                  : 'border-border-faint bg-surface-hover text-text-muted hover:bg-surface-input hover:text-text-main'
              }`}
            >
              {FILTER_LABELS[filter]}
              <span
                className={`ml-2 rounded-full px-2 py-0.5 text-xs ${
                  active ? 'bg-white/20 text-white' : 'bg-surface-card text-text-muted'
                }`}
              >
                {counts[filter]}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-5">
        {recommendationsQuery.isLoading ? (
          <div className="rounded-lg border border-border-faint bg-surface-hover px-4 py-6 text-sm text-text-muted">
            Loading Compliance Agent recommendations...
          </div>
        ) : recommendationsQuery.isError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-6 text-sm text-rose-700">
            Failed to load Compliance Agent recommendations.
          </div>
        ) : visibleRecommendations.length === 0 ? (
          <div className="rounded-lg border border-border-faint bg-surface-hover px-4 py-6 text-sm text-text-muted">
            No proposed recommendations in this queue.
          </div>
        ) : (
          <div className="divide-y divide-border-faint overflow-hidden rounded-lg border border-border-faint">
            {visibleRecommendations.map((recommendation) => {
              const sourceLink = sourceLinkFor(recommendation);
              const decidingThis =
                decisionMutation.isPending &&
                decisionMutation.variables?.recommendationId === recommendation.id;
              const related = recommendationIdentity(recommendation);

              return (
                <article key={recommendation.id} className="bg-surface-card px-4 py-4">
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${priorityClasses(recommendation.priority)}`}>
                          {normalizeLabel(recommendation.priority)}
                        </span>
                        <span className="rounded-full border border-border-faint bg-surface-hover px-2 py-0.5 text-xs text-text-muted">
                          {normalizeLabel(recommendation.trigger_type)}
                        </span>
                        {recommendation.requires_approval ? (
                          <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
                            Approval required
                          </span>
                        ) : null}
                      </div>

                      <h3 className="mt-2 text-base font-semibold text-text-main">{recommendation.title}</h3>
                      <p className="mt-1 text-sm text-text-muted">{recommendation.summary}</p>

                      <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                        <div className="rounded-lg border border-border-faint bg-surface-hover px-3 py-2">
                          <div className="text-xs uppercase tracking-wide text-text-muted">Proposed action</div>
                          <div className="mt-1 font-medium text-text-main">{actionSummary(recommendation)}</div>
                        </div>
                        <div className="rounded-lg border border-border-faint bg-surface-hover px-3 py-2">
                          <div className="text-xs uppercase tracking-wide text-text-muted">Related context</div>
                          <div className="mt-1 font-medium text-text-main">{related || 'Compliance context'}</div>
                        </div>
                      </div>

                      <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-text-muted">
                        <span>Created {formatDateTime(recommendation.created_at)}</span>
                        {recommendation.agent_task_id ? <span>Task {recommendation.agent_task_id}</span> : null}
                      </div>
                    </div>

                    <div className="flex w-full flex-col gap-2 sm:w-auto sm:min-w-[220px]">
                      <Link
                        href={sourceLink.href}
                        className="inline-flex items-center justify-center rounded-lg border border-border-faint bg-surface-hover px-3 py-2 text-sm font-semibold text-text-main hover:bg-surface-input"
                      >
                        {sourceLink.label === 'Open report' ? (
                          <DocumentTextIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                        ) : (
                          <LinkIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                        )}
                        {sourceLink.label}
                      </Link>
                      <button
                        type="button"
                        onClick={() =>
                          decisionMutation.mutate({
                            recommendationId: recommendation.id,
                            state: 'accepted',
                          })
                        }
                        disabled={decidingThis}
                        className="inline-flex items-center justify-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                      >
                        {decidingThis ? (
                          <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                        ) : (
                          <CheckCircleIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                        )}
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() =>
                          decisionMutation.mutate({
                            recommendationId: recommendation.id,
                            state: 'rejected',
                          })
                        }
                        disabled={decidingThis}
                        className="inline-flex items-center justify-center rounded-lg border border-border-faint bg-surface-card px-3 py-2 text-sm font-semibold text-text-main hover:bg-surface-hover disabled:opacity-50"
                      >
                        <XCircleIcon className="mr-2 h-4 w-4" aria-hidden="true" />
                        Reject
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
