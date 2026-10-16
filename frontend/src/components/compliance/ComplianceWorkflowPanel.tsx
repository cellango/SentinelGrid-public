'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { campaignsApi, type Campaign } from '@/lib/api/governance';
import {
  complianceApi,
  type ComplianceCriterion,
  type ComplianceEvidenceCollectionResponse,
  type ComplianceEvidenceType,
} from '@/lib/api/compliance';
import { useTenant } from '@/lib/hooks/useTenant';
import { toast } from 'react-hot-toast';
import {
  ClipboardDocumentCheckIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
} from '@heroicons/react/24/outline';

type WorkflowState = {
  campaign?: Campaign;
  evidence?: ComplianceEvidenceCollectionResponse;
};

const REVIEW_PREFIXES = new Set(['AC', 'IA', 'PS']);

function controlPrefix(controlId: string) {
  return (controlId || '').split('-', 1)[0].toUpperCase();
}

function supportsAccessReview(criterion: ComplianceCriterion) {
  return (
    criterion.id === 'CC6.1' ||
    criterion.mapped_nist_controls.some((controlId) => REVIEW_PREFIXES.has(controlPrefix(controlId)))
  );
}

function pickPrimaryControl(criterion: ComplianceCriterion) {
  const preferred = ['IA-2', 'AC-2', 'AU-2', 'AC-3', 'AC-6'];
  for (const controlId of preferred) {
    if (criterion.mapped_nist_controls.includes(controlId)) {
      return controlId;
    }
  }
  return criterion.mapped_nist_controls[0] || null;
}

function recommendedEvidenceTypes(controlId: string | null): ComplianceEvidenceType[] {
  const prefix = controlPrefix(controlId || '');
  if (prefix === 'AU') {
    return ['audit_log', 'export', 'api_response'];
  }
  if (prefix === 'IA' || prefix === 'AC' || prefix === 'PS') {
    return ['configuration', 'audit_log', 'export'];
  }
  if (prefix === 'CM' || prefix === 'CA') {
    return ['configuration', 'policy_document', 'api_response'];
  }
  return ['configuration', 'export'];
}

function campaignWindow() {
  const start = new Date();
  const end = new Date();
  end.setDate(end.getDate() + 14);
  return {
    start: start.toISOString(),
    end: end.toISOString(),
  };
}

export function ComplianceWorkflowPanel({ criteria }: { criteria: ComplianceCriterion[] }) {
  const queryClient = useQueryClient();
  const { tenant } = useTenant();
  const [workflowState, setWorkflowState] = useState<Record<string, WorkflowState>>({});

  const activeCriteria = useMemo(
    () =>
      criteria
        .filter((criterion) => criterion.open_findings > 0 || criterion.status !== 'compliant')
        .slice(0, 4),
    [criteria]
  );

  const launchReviewMutation = useMutation({
    mutationFn: async (criterion: ComplianceCriterion) => {
      if (!tenant?.id) {
        throw new Error('Tenant context is missing. Sign in again and retry.');
      }

      const { start, end } = campaignWindow();
      const created = await campaignsApi.create({
        tenant_id: tenant.id,
        name: `${criterion.id} Access Review`,
        description: `Compliance-triggered access review for ${criterion.title}. Mapped controls: ${criterion.mapped_nist_controls.join(', ') || 'n/a'}.`,
        start_date: start,
        end_date: end,
        reviewer_type: 'admin',
        auto_revoke_days: 7,
      });

      const started = await campaignsApi.start(created.id);
      return { criterionId: criterion.id, campaign: started };
    },
    onSuccess: ({ criterionId, campaign }) => {
      setWorkflowState((current) => ({
        ...current,
        [criterionId]: {
          ...current[criterionId],
          campaign,
        },
      }));
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Access review campaign launched from compliance.');
    },
    onError: (error: any) => {
      toast.error(error?.message || error?.response?.data?.detail || 'Failed to launch access review');
    },
  });

  const collectEvidenceMutation = useMutation({
    mutationFn: async (criterion: ComplianceCriterion) => {
      const controlId = pickPrimaryControl(criterion);
      if (!controlId) {
        throw new Error('No mapped NIST control is available for evidence collection.');
      }

      const evidence = await complianceApi.collectEvidence({
        control_id: controlId,
        evidence_types: recommendedEvidenceTypes(controlId),
        tenant_id: tenant?.id || undefined,
      });
      return { criterionId: criterion.id, evidence };
    },
    onSuccess: ({ criterionId, evidence }) => {
      setWorkflowState((current) => ({
        ...current,
        [criterionId]: {
          ...current[criterionId],
          evidence,
        },
      }));
      toast.success('Evidence collected for the selected control.');
    },
    onError: (error: any) => {
      toast.error(error?.message || error?.response?.data?.detail || 'Failed to collect evidence');
    },
  });

  if (activeCriteria.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-text-main">Access Review and Evidence Workflows</h3>
          <p className="mt-1 text-sm text-text-muted">
            Start an access review or collect evidence directly from the criteria that still need work.
          </p>
        </div>
        <Link href="/dashboard/iam/access-reviews" className="text-sm font-medium text-primary hover:text-primary/80">
          Open access reviews →
        </Link>
      </div>

      <div className="mt-5 space-y-4">
        {activeCriteria.map((criterion) => {
          const primaryControl = pickPrimaryControl(criterion);
          const currentState = workflowState[criterion.id];
          const collectingThis = collectEvidenceMutation.isPending && collectEvidenceMutation.variables?.id === criterion.id;
          const launchingThis = launchReviewMutation.isPending && launchReviewMutation.variables?.id === criterion.id;

          return (
            <div key={criterion.id} className="rounded-lg border border-border-faint p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-text-main">{criterion.id}</span>
                    <span className="rounded-full border border-border-faint bg-surface-hover px-2 py-0.5 text-xs text-text-muted">
                      {criterion.open_findings} open findings
                    </span>
                  </div>
                  <h4 className="mt-2 text-base font-semibold text-text-main">{criterion.title}</h4>
                  <p className="mt-1 text-sm text-text-muted">{criterion.description}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {criterion.mapped_nist_controls.slice(0, 4).map((controlId) => (
                      <span key={`${criterion.id}-${controlId}`} className="rounded-full border border-border-faint bg-surface-hover px-2.5 py-1 text-xs text-text-muted">
                        {controlId}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-1 gap-2 min-w-[220px]">
                  <button
                    type="button"
                    onClick={() => collectEvidenceMutation.mutate(criterion)}
                    disabled={collectingThis}
                    className="inline-flex items-center justify-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                  >
                    {collectingThis ? (
                      <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <DocumentDuplicateIcon className="mr-2 h-4 w-4" />
                    )}
                    Collect evidence
                  </button>

                  <button
                    type="button"
                    onClick={() => launchReviewMutation.mutate(criterion)}
                    disabled={!supportsAccessReview(criterion) || launchingThis}
                    className="inline-flex items-center justify-center rounded-lg border border-border-faint bg-surface-hover px-3 py-2 text-sm font-semibold text-text-main hover:bg-surface-input disabled:opacity-40"
                  >
                    {launchingThis ? (
                      <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <ClipboardDocumentCheckIcon className="mr-2 h-4 w-4" />
                    )}
                    Launch access review
                  </button>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 xl:grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg border border-border-faint bg-surface-hover p-3">
                  <div className="text-xs uppercase tracking-wide text-text-muted">Evidence target</div>
                  <div className="mt-1 font-medium text-text-main">{primaryControl || 'No mapped control available'}</div>
                  <div className="mt-1 text-text-muted">
                    {recommendedEvidenceTypes(primaryControl).join(', ').replace(/_/g, ' ')}
                  </div>
                  {currentState?.evidence && (
                    <div className="mt-2 text-emerald-700">
                      Collected {Object.keys(currentState.evidence.evidence || {}).length} evidence artifact groups.
                    </div>
                  )}
                </div>

                <div className="rounded-lg border border-border-faint bg-surface-hover p-3">
                  <div className="text-xs uppercase tracking-wide text-text-muted">Access review workflow</div>
                  <div className="mt-1 text-text-muted">
                    {supportsAccessReview(criterion)
                      ? 'Use a compliance-triggered review to validate identity access before the next export.'
                      : 'This criterion is not strongly identity-driven, so access review is deprioritized.'}
                  </div>
                  {currentState?.campaign && (
                    <Link href={`/dashboard/campaigns/${currentState.campaign.id}`} className="mt-2 inline-flex font-medium text-emerald-400 hover:text-emerald-300">
                      View launched campaign →
                    </Link>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
