'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldCheckIcon,
  DocumentTextIcon,
  ClipboardDocumentCheckIcon,
} from '@heroicons/react/24/outline';
import { PlanGate } from '@/components/PlanGate';
import { FrameworkStarterPacksPanel } from '@/components/compliance/FrameworkStarterPacksPanel';
import { FrameworkSelectionPanel } from '@/components/compliance/FrameworkSelectionPanel';
import { ComplianceAgentWorkbenchPanel } from '@/components/compliance/ComplianceAgentWorkbenchPanel';
import { ComplianceWorkflowPanel } from '@/components/compliance/ComplianceWorkflowPanel';
import {
  getComplianceDashboard,
  type ComplianceControlCoverage,
  type ComplianceCriterion,
  type ComplianceFrameworkCoverage,
  type ComplianceSignal,
} from '@/lib/api/compliance';
import { complianceFeatureFlags, getComplianceRuntimeLabels } from '@/lib/compliance/features';
import SlideOverPanel from '@/components/ui/SlideOverPanel';

const ComplianceHeatmap = dynamic(() => import('@/components/compliance/ComplianceHeatmap'), { ssr: false });

function statusClasses(status: ComplianceCriterion['status']) {
  switch (status) {
    case 'compliant':
      return 'bg-emerald-50 border-emerald-200 text-emerald-700';
    case 'partial':
      return 'bg-amber-50 border-amber-200 text-amber-700';
    case 'non_compliant':
      return 'bg-rose-50 border-rose-200 text-rose-700';
    default:
      return 'bg-surface-hover border-border-faint text-text-muted';
  }
}

function formatStatus(status: string) {
  return status.replace(/_/g, ' ');
}

function coverageStatusClasses(status: string) {
  switch (status) {
    case 'accepted':
    case 'ready_for_review':
      return 'bg-emerald-50 border-emerald-200 text-emerald-700';
    case 'partially_supported':
      return 'bg-blue-50 border-blue-200 text-blue-700';
    case 'needs_evidence':
    case 'exception':
      return 'bg-amber-50 border-amber-200 text-amber-700';
    case 'not_started':
      return 'bg-surface-hover border-border-faint text-text-muted';
    default:
      return 'bg-surface-hover border-border-faint text-text-muted';
  }
}

function frameworkCode(framework: ComplianceFrameworkCoverage) {
  return framework.framework_code || framework.framework_id.toUpperCase();
}

function formatPercent(value: number) {
  const normalized = value > 1 ? value : value * 100;
  return `${Math.round(normalized)}%`;
}

function countStatuses(framework: ComplianceFrameworkCoverage, statuses: string[]) {
  return statuses.reduce((total, status) => total + (framework.status_counts?.[status] || 0), 0);
}

function controlGapCount(control: ComplianceControlCoverage) {
  return control.gaps?.length || 0;
}

function controlEvidenceRequirementCount(control: ComplianceControlCoverage) {
  return control.evidence_requirements?.length || 0;
}

function controlNeedsWork(control: ComplianceControlCoverage) {
  return control.status !== 'accepted' && control.status !== 'not_applicable';
}

function recordStringValue(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim().length > 0) {
      return value;
    }
  }
  return null;
}

function gapLabel(gap: Record<string, unknown>, index: number) {
  return recordStringValue(gap, ['title', 'summary', 'description', 'requirement', 'type']) || `Gap ${index + 1}`;
}

function getFrameworkMetrics(framework: ComplianceFrameworkCoverage) {
  const totalControls = framework.control_count || framework.controls.length;
  const returnedControls = framework.returned_control_count || framework.controls.length;
  const readyControls = countStatuses(framework, ['accepted', 'ready_for_review']);
  const needsAttention = countStatuses(framework, [
    'needs_evidence',
    'partially_supported',
    'not_started',
    'exception',
  ]);
  const openGaps = framework.controls.reduce((total, control) => total + controlGapCount(control), 0);
  const evidenceRequirements = framework.controls.reduce(
    (total, control) => total + controlEvidenceRequirementCount(control),
    0
  );
  const controlsWithFreshEvidence = framework.controls.filter((control) => Boolean(control.last_activity)).length;
  const reportReadyPercent = totalControls > 0 ? Math.round((readyControls / totalControls) * 100) : 0;

  return {
    totalControls,
    returnedControls,
    readyControls,
    needsAttention,
    openGaps,
    evidenceRequirements,
    controlsWithFreshEvidence,
    reportReadyPercent,
  };
}

function FrameworkMetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail: string;
}) {
  return (
    <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-2 text-3xl font-bold text-text-main">{value}</p>
      <p className="mt-1 text-sm text-text-muted">{detail}</p>
    </div>
  );
}

function FrameworkScopeOverview({
  frameworks,
  activeFrameworkId,
  onSelectFramework,
  isLoading,
}: {
  frameworks: ComplianceFrameworkCoverage[];
  activeFrameworkId: string | null;
  onSelectFramework: (frameworkId: string) => void;
  isLoading: boolean;
}) {
  const selectedFramework =
    frameworks.find((framework) => framework.framework_id === activeFrameworkId) || frameworks[0] || null;

  if (isLoading) {
    return (
      <section className="mb-8" aria-labelledby="framework-status-heading">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-text-muted">Framework scope</p>
            <h2 id="framework-status-heading" className="mt-1 text-2xl font-bold text-text-main">
              Selected framework status
            </h2>
            <p className="mt-1 text-text-muted">Loading selected frameworks and coverage posture.</p>
          </div>
        </div>
        <div className="mt-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {['Coverage', 'Open gaps', 'Evidence freshness', 'Report readiness'].map((label) => (
            <FrameworkMetricCard key={label} label={label} value="..." detail="Loading framework coverage" />
          ))}
        </div>
      </section>
    );
  }

  if (!selectedFramework) {
    return (
      <section className="mb-8 rounded-lg border border-surface-card-border bg-surface-card p-6 shadow">
        <p className="text-xs uppercase tracking-wide text-text-muted">Framework scope</p>
        <h2 id="framework-status-heading" className="mt-1 text-2xl font-bold text-text-main">
          No selected frameworks yet
        </h2>
        <p className="mt-2 text-sm text-text-muted">
          Select at least one compliance framework to see coverage, gaps, evidence freshness, and report readiness.
        </p>
      </section>
    );
  }

  const selectedMetrics = getFrameworkMetrics(selectedFramework);
  const controlsNeedingWork = selectedFramework.controls.filter(controlNeedsWork).slice(0, 5);
  const returnedControls = selectedFramework.controls.slice(0, 6);

  return (
    <section className="mb-8" aria-labelledby="framework-status-heading">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-text-muted">Framework scope</p>
          <h2 id="framework-status-heading" className="mt-1 text-2xl font-bold text-text-main">
            Selected framework status
          </h2>
          <p className="mt-1 text-text-muted">
            Switch frameworks to review coverage, gaps, evidence freshness, and report readiness in one view.
          </p>
        </div>
        <Link
          href="/dashboard/compliance/reports"
          className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
        >
          <DocumentTextIcon className="h-5 w-5 mr-2" />
          Reports & Scheduling
        </Link>
      </div>

      <div className="mt-5 flex gap-2 overflow-x-auto pb-2" role="tablist" aria-label="Compliance frameworks">
        {frameworks.map((framework) => {
          const tabMetrics = getFrameworkMetrics(framework);
          const selected = framework.framework_id === selectedFramework.framework_id;
          return (
            <button
              key={framework.framework_id}
              type="button"
              role="tab"
              aria-selected={selected}
              aria-controls={`framework-panel-${framework.framework_id}`}
              onClick={() => onSelectFramework(framework.framework_id)}
              className={`min-w-[220px] rounded-lg border px-4 py-3 text-left transition-colors ${
                selected
                  ? 'border-primary bg-primary/10 text-text-main shadow-sm'
                  : 'border-surface-card-border bg-surface-card text-text-muted hover:border-primary/40'
              }`}
            >
              <span className="block text-xs font-semibold uppercase tracking-wide">{frameworkCode(framework)}</span>
              <span className="mt-1 block text-sm font-semibold">{framework.framework_name}</span>
              <span className="mt-1 block text-xs">
                {tabMetrics.readyControls}/{tabMetrics.totalControls} report ready
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <FrameworkMetricCard
          label="Coverage"
          value={formatPercent(selectedFramework.average_confidence)}
          detail={`${selectedMetrics.readyControls}/${selectedMetrics.totalControls} controls ready or accepted`}
        />
        <FrameworkMetricCard
          label="Open gaps"
          value={selectedMetrics.openGaps}
          detail={`${selectedMetrics.needsAttention} controls need evidence or work`}
        />
        <FrameworkMetricCard
          label="Evidence freshness"
          value={`${selectedMetrics.controlsWithFreshEvidence}/${selectedMetrics.returnedControls}`}
          detail="Returned controls with recent mapped activity"
        />
        <FrameworkMetricCard
          label="Report readiness"
          value={`${selectedMetrics.reportReadyPercent}%`}
          detail={`${selectedMetrics.evidenceRequirements} evidence requirements tracked`}
        />
      </div>

      <div
        id={`framework-panel-${selectedFramework.framework_id}`}
        role="tabpanel"
        className="mt-5 grid grid-cols-1 xl:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)] gap-5"
      >
        <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-text-muted">{frameworkCode(selectedFramework)}</p>
              <h3 className="mt-1 text-lg font-semibold text-text-main">{selectedFramework.framework_name}</h3>
              <p className="mt-1 text-sm text-text-muted">
                {formatStatus(selectedFramework.runtime_support)} support - {formatStatus(selectedFramework.selection_status)} selection
              </p>
            </div>
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${coverageStatusClasses(selectedFramework.status)}`}>
              {formatStatus(selectedFramework.status)}
            </span>
          </div>

          <div className="mt-5 divide-y divide-border-faint">
            {returnedControls.length > 0 ? (
              returnedControls.map((control) => (
                <div key={`${selectedFramework.framework_id}-${control.control_id}`} className="py-4 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-semibold text-text-main">{control.control_id}</span>
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${coverageStatusClasses(control.status)}`}>
                          {formatStatus(control.status)}
                        </span>
                      </div>
                      <h4 className="mt-1 text-base font-semibold text-text-main">{control.title}</h4>
                      {control.description ? <p className="mt-1 text-sm text-text-muted">{control.description}</p> : null}
                    </div>
                    <div className="text-right text-sm text-text-muted">
                      <div>{formatPercent(control.confidence)} confidence</div>
                      <div>{controlGapCount(control)} gaps</div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-text-muted">No controls returned for this framework yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
          <h3 className="text-lg font-semibold text-text-main">Gap Focus</h3>
          <p className="mt-1 text-sm text-text-muted">Highest-value items to close before report generation.</p>
          <div className="mt-4 space-y-3">
            {controlsNeedingWork.length > 0 ? (
              controlsNeedingWork.map((control) => (
                <div key={`gap-${selectedFramework.framework_id}-${control.control_id}`} className="rounded-lg border border-border-faint px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-text-main">{control.control_id}</p>
                      <p className="mt-1 text-sm text-text-muted">{control.title}</p>
                    </div>
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${coverageStatusClasses(control.status)}`}>
                      {formatStatus(control.status)}
                    </span>
                  </div>
                  {control.gaps.length > 0 ? (
                    <ul className="mt-3 space-y-1 text-sm text-text-muted">
                      {control.gaps.slice(0, 2).map((gap, index) => (
                        <li key={`${control.control_id}-gap-${index}`}>{gapLabel(gap, index)}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-3 text-sm text-text-muted">
                      {controlEvidenceRequirementCount(control)} evidence requirements still need review.
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="text-sm text-text-muted">No open gaps in the returned controls for this framework.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function SignalList({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: ComplianceSignal[];
  emptyText: string;
}) {
  return (
    <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
      <h3 className="text-lg font-semibold text-text-main">{title}</h3>
      <div className="mt-4 space-y-3">
        {items.length > 0 ? (
          items.map((item) => (
            <div key={item.id} className="rounded-lg border border-border-faint px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-text-main">{item.title}</span>
                {item.severity && (
                  <span className="rounded-full border border-border-faint bg-surface-hover px-2 py-0.5 text-xs text-text-muted">
                    {item.severity}
                  </span>
                )}
                {item.status && (
                  <span className="rounded-full border border-border-faint bg-surface-hover px-2 py-0.5 text-xs text-text-muted">
                    {formatStatus(item.status)}
                  </span>
                )}
              </div>
              <div className="mt-2 text-sm text-text-muted">
                {item.source_label || item.source || 'Signal'}
                {item.nist_control_id ? ` • ${item.nist_control_id}` : ''}
                {item.detected_at ? ` • ${new Date(item.detected_at).toLocaleString()}` : ''}
              </div>
              {item.href && (
                <Link href={item.href} className="mt-2 inline-flex text-sm font-medium text-primary hover:text-primary/80">
                  Open source →
                </Link>
              )}
            </div>
          ))
        ) : (
          <p className="text-sm text-text-muted">{emptyText}</p>
        )}
      </div>
    </div>
  );
}

export default function ComplianceDashboardPage() {
  const [selectedCriterion, setSelectedCriterion] = useState<ComplianceCriterion | null>(null);
  const [activeFrameworkId, setActiveFrameworkId] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ['compliance-dashboard'],
    queryFn: getComplianceDashboard,
  });

  const reportingSummary = data?.reporting_summary || {
    criteria_ready: 0,
    criteria_partial: 0,
    criteria_needing_attention: 0,
    criteria_not_assessed: 0,
    key_detection_count: 0,
    control_check_count: 0,
    playbook_count: 0,
    playbook_execution_count: 0,
    reportable_evidence_items: 0,
    top_detection_sources: [],
  };
  const soc2Summary = data?.soc2?.summary || {
    total_criteria: 0,
    open_criteria: 0,
    total_findings: 0,
    open_findings: 0,
    status: 'unknown',
  };
  const priorityCriteria = data?.priority_criteria || [];
  const starterPacks = data?.framework_starter_packs || [];
  const runtimeLabels = getComplianceRuntimeLabels();
  const frameworkCoverageItems = data?.framework_coverage?.items || [];
  const selectedFramework = useMemo(
    () =>
      frameworkCoverageItems.find((framework) => framework.framework_id === activeFrameworkId) ||
      frameworkCoverageItems[0] ||
      null,
    [activeFrameworkId, frameworkCoverageItems]
  );
  const selectedFrameworkMetrics = selectedFramework ? getFrameworkMetrics(selectedFramework) : null;
  const selectedFrameworkIsSoc2 = selectedFramework?.framework_id === 'soc2';
  const selectedFrameworkControls = selectedFramework?.controls || [];
  const hasFrameworkCoverage = frameworkCoverageItems.length > 0;

  return (
    <PlanGate requiredTier="protect_defend_comply">
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-text-main">{runtimeLabels.dashboardTitle}</h1>
          <p className="mt-2 text-text-muted">
            {runtimeLabels.dashboardDescription}
          </p>
        </div>

        <FrameworkScopeOverview
          frameworks={frameworkCoverageItems}
          activeFrameworkId={activeFrameworkId}
          onSelectFramework={setActiveFrameworkId}
          isLoading={isLoading}
        />

        <FrameworkSelectionPanel editable={complianceFeatureFlags.multiFramework} />

        {!isLoading && !hasFrameworkCoverage && (
          <FrameworkStarterPacksPanel
            starterPacks={starterPacks}
            multiFrameworkEnabled={complianceFeatureFlags.multiFramework}
          />
        )}

        <ComplianceAgentWorkbenchPanel />

        {/* Compliance Heatmap */}
        {selectedFrameworkIsSoc2 && (data?.soc2?.controls?.length ?? 0) > 0 && (
          <div className="mb-8">
            <div className="mb-4">
              <h2 className="text-2xl font-bold text-text-main">SOC 2 Criteria Heatmap</h2>
              <p className="text-text-muted">
                SOC 2 remains a selected readiness framework, with the detailed criteria heatmap shown when SOC 2 is active.
              </p>
            </div>
            <ComplianceHeatmap
              criteria={data?.soc2?.controls || []}
              onCellClick={(c) => setSelectedCriterion(c)}
            />
          </div>
        )}

        {/* Criterion drill-down slide-over */}
        <SlideOverPanel
          open={!!selectedCriterion}
          onClose={() => setSelectedCriterion(null)}
          title={selectedCriterion ? `${selectedCriterion.id}: ${selectedCriterion.title}` : ''}
          subtitle={selectedCriterion ? formatStatus(selectedCriterion.status) : ''}
          width="lg"
        >
          {selectedCriterion && (
            <div className="space-y-6">
              {selectedCriterion.description && (
                <div>
                  <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Description</h4>
                  <p className="text-sm text-text-main">{selectedCriterion.description}</p>
                </div>
              )}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-lg bg-surface-hover border border-border-faint">
                  <p className="text-xs text-text-muted">Open Findings</p>
                  <p className="text-lg font-bold text-text-main tabular-nums">{selectedCriterion.open_findings}</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-hover border border-border-faint">
                  <p className="text-xs text-text-muted">Evidence Items</p>
                  <p className="text-lg font-bold text-text-main tabular-nums">{selectedCriterion.evidence_items}</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-hover border border-border-faint">
                  <p className="text-xs text-text-muted">Playbooks</p>
                  <p className="text-lg font-bold text-text-main tabular-nums">{selectedCriterion.playbook_count}</p>
                </div>
              </div>
              {selectedCriterion.mapped_nist_controls.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">NIST Controls</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedCriterion.mapped_nist_controls.map((id) => (
                      <span key={id} className="px-2 py-0.5 text-xs rounded-full bg-surface-hover text-text-main border border-border-faint">{id}</span>
                    ))}
                  </div>
                </div>
              )}
              {selectedCriterion.key_detections.length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Key Detections</h4>
                  <div className="space-y-2">
                    {selectedCriterion.key_detections.map((d) => (
                      <div key={d.id} className="p-2.5 rounded-lg border border-border-faint text-sm">
                        <p className="text-text-main font-medium">{d.title}</p>
                        <p className="text-xs text-text-muted mt-0.5">{d.source_label || d.source}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </SlideOverPanel>

        <div className="mb-8 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-text-main">
                {selectedFramework ? `${selectedFramework.framework_name} Report Readiness` : 'Report Readiness'}
              </h2>
              <p className="text-text-muted">
                Evidence, gaps, and mapped signals for the active selected framework.
              </p>
            </div>
            <Link
              href="/dashboard/compliance/reports"
              className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
            >
              <DocumentTextIcon className="h-5 w-5 mr-2" />
              Reports & Scheduling
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
              <p className="text-xs uppercase tracking-wide text-text-muted">Controls needing work</p>
              <p className="mt-2 text-3xl font-bold text-text-main">
                {selectedFrameworkMetrics?.needsAttention ?? reportingSummary.criteria_needing_attention}
              </p>
              <p className="text-xs text-text-muted">Evidence gaps or partial support</p>
            </div>
            <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
              <p className="text-xs uppercase tracking-wide text-text-muted">Open gaps</p>
              <p className="mt-2 text-3xl font-bold text-text-main">
                {selectedFrameworkMetrics?.openGaps ?? soc2Summary.open_findings}
              </p>
              <p className="text-xs text-text-muted">Returned controls with unresolved requirements</p>
            </div>
            <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
              <p className="text-xs uppercase tracking-wide text-text-muted">Evidence freshness</p>
              <p className="mt-2 text-3xl font-bold text-text-main">
                {selectedFrameworkMetrics
                  ? `${selectedFrameworkMetrics.controlsWithFreshEvidence}/${selectedFrameworkMetrics.returnedControls}`
                  : '0/0'}
              </p>
              <p className="text-xs text-text-muted">Controls with recent mapped activity</p>
            </div>
            <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
              <p className="text-xs uppercase tracking-wide text-text-muted">Report readiness</p>
              <p className="mt-2 text-3xl font-bold text-text-main">
                {selectedFrameworkMetrics ? `${selectedFrameworkMetrics.reportReadyPercent}%` : '0%'}
              </p>
              <p className="text-xs text-text-muted">Ready or accepted controls</p>
            </div>
          </div>

          {selectedFrameworkIsSoc2 ? (
            <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-text-main">SOC 2 Priority Criteria</h3>
                  <p className="text-sm text-text-muted">The most useful SOC 2 controls to discuss in a trust review or audit-prep conversation right now.</p>
                </div>
                <span className="text-xs uppercase tracking-wide text-text-muted">Top {priorityCriteria.length}</span>
              </div>
              {isLoading ? (
                <p className="text-sm text-text-muted">Loading compliance criteria...</p>
              ) : (
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                  {priorityCriteria.map((control) => (
                    <div key={control.id} className="rounded-lg border border-border-faint p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-text-main">{control.id}</span>
                            <span className={`rounded-full border px-2 py-0.5 text-xs ${statusClasses(control.status)}`}>
                              {formatStatus(control.status)}
                            </span>
                          </div>
                          <h4 className="mt-2 text-lg font-semibold text-text-main">{control.title}</h4>
                          <p className="mt-1 text-sm text-text-muted">{control.description}</p>
                        </div>
                        <div className="text-right text-sm text-text-muted">
                          <div>{control.open_findings} open</div>
                          <div>{control.evidence_items} evidence items</div>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {control.mapped_nist_controls.slice(0, 4).map((controlId) => (
                          <span key={`${control.id}-${controlId}`} className="rounded-full border border-border-faint bg-surface-hover px-2.5 py-1 text-xs text-text-muted">
                            {controlId}
                          </span>
                        ))}
                      </div>
                      <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                        <div className="rounded-lg border border-border-faint bg-surface-hover p-3">
                          <div className="text-text-muted">Detections</div>
                          <div className="mt-1 font-semibold text-text-main">{control.detection_count}</div>
                        </div>
                        <div className="rounded-lg border border-border-faint bg-surface-hover p-3">
                          <div className="text-text-muted">Control checks</div>
                          <div className="mt-1 font-semibold text-text-main">{control.control_check_count}</div>
                        </div>
                        <div className="rounded-lg border border-border-faint bg-surface-hover p-3">
                          <div className="text-text-muted">Supporting playbooks</div>
                          <div className="mt-1 font-semibold text-text-main">{control.playbook_count}</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-text-main">Selected Framework Controls</h3>
                  <p className="text-sm text-text-muted">Catalog controls and evidence requirements for the active framework.</p>
                </div>
                <span className="text-xs uppercase tracking-wide text-text-muted">
                  {selectedFrameworkControls.length} returned
                </span>
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {selectedFrameworkControls.slice(0, 8).map((control) => (
                  <div key={`${control.framework_id}-${control.control_id}`} className="rounded-lg border border-border-faint p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-text-main">{control.control_id}</span>
                          <span className={`rounded-full border px-2 py-0.5 text-xs ${coverageStatusClasses(control.status)}`}>
                            {formatStatus(control.status)}
                          </span>
                        </div>
                        <h4 className="mt-2 text-lg font-semibold text-text-main">{control.title}</h4>
                        {control.description ? <p className="mt-1 text-sm text-text-muted">{control.description}</p> : null}
                      </div>
                      <div className="text-right text-sm text-text-muted">
                        <div>{formatPercent(control.confidence)} confidence</div>
                        <div>{controlEvidenceRequirementCount(control)} evidence requirements</div>
                      </div>
                    </div>
                  </div>
                ))}
                {selectedFrameworkControls.length === 0 && (
                  <p className="text-sm text-text-muted">No controls returned for the active framework yet.</p>
                )}
              </div>
            </div>
          )}

          {selectedFrameworkIsSoc2 && <ComplianceWorkflowPanel criteria={priorityCriteria} />}
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-8">
          <SignalList
            title="Key detections feeding reports"
            items={data?.key_detections || []}
            emptyText="Detections will appear here once SOC 2 criteria have mapped security signals."
          />
          <SignalList
            title="Control checks feeding reports"
            items={data?.control_checks || []}
            emptyText="Control checks will appear here once IAM or posture findings are mapped into the reporting view."
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/dashboard/compliance/reports"
            className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow transition-[border-color,box-shadow] hover:border-primary/40 hover:shadow-lg"
          >
            <DocumentTextIcon className="mb-3 h-10 w-10 text-primary" />
            <h3 className="mb-2 text-lg font-semibold text-text-main">Compliance Reports</h3>
            <p className="mb-3 text-sm text-text-muted">
              Generate trust-facing exports using the mapped detections and control checks from this dashboard.
            </p>
            <span className="text-sm font-medium text-primary">View Reports →</span>
          </Link>

          <Link
            href="/dashboard/iam/access-reviews"
            className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow transition-[border-color,box-shadow] hover:border-primary/40 hover:shadow-lg"
          >
            <ClipboardDocumentCheckIcon className="mb-3 h-10 w-10 text-secondary" />
            <h3 className="mb-2 text-lg font-semibold text-text-main">Access Reviews</h3>
            <p className="mb-3 text-sm text-text-muted">
              Run access reviews when identity findings need a formal evidence trail for auditors or customers.
            </p>
            <span className="text-sm font-medium text-secondary">Open Reviews →</span>
          </Link>

          <Link
            href="/dashboard/playbooks"
            className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow transition-[border-color,box-shadow] hover:border-primary/40 hover:shadow-lg"
          >
            <ShieldCheckIcon className="mb-3 h-10 w-10 text-emerald-400" />
            <h3 className="mb-2 text-lg font-semibold text-text-main">Response Playbooks</h3>
            <p className="mb-3 text-sm text-text-muted">
              Review the playbooks and executions that back the compliance story for common SMB attack patterns.
            </p>
            <span className="text-sm font-medium text-emerald-400">Open Playbooks →</span>
          </Link>
        </div>
      </div>
    </PlanGate>
  );
}
