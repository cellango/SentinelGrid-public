/**
 * Finding Detail Component
 * Show finding details with remediation tab
 */

'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  enhanceFinding,
  createRemediationPlan,
  executeRemediation,
  getRemediationStatus,
  RemediationPlan,
} from '@/lib/api/compliance-remediation';
import { createTicket, type Ticket } from '@/lib/api/tickets';
import { useAuth } from '@/lib/providers/AuthProvider';
import RemediationPlanEditor from './RemediationPlanEditor';
import RemediationHistory from './RemediationHistory';
import { toast } from 'react-hot-toast';
import { buildEntityGraphHref } from '@/lib/security/graph-context';

interface FindingDetailProps {
  findingId: string;
  findingType: 'iam_finding' | 'posture_finding';
  onBack: () => void;
}

export default function FindingDetail({
  findingId,
  findingType,
  onBack,
}: FindingDetailProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'remediation' | 'history'>('overview');
  const [createdTicket, setCreatedTicket] = useState<Ticket | null>(null);

  // Get finding details (would come from IAM/Posture Agent)
  const { data: finding } = useQuery({
    queryKey: ['finding', findingId, findingType],
    queryFn: async () => {
      // Placeholder - would call IAM/Posture Agent API
      return {
        id: findingId,
        type: findingType,
        severity: 'high',
        description: 'Sample finding description',
        status: 'open',
      };
    },
  });

  // Get remediation status
  const { data: remediationStatus } = useQuery({
    queryKey: ['remediation-status', findingId, findingType],
    queryFn: () => getRemediationStatus(findingId, findingType),
  });

  // Enhance finding mutation
  const enhanceFindingMutation = useMutation({
    mutationFn: () => enhanceFinding(findingId, findingType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finding', findingId, findingType] });
      toast.success('Finding enhanced with compliance metadata');
    },
    onError: (error: any) => {
      toast.error(`Failed to enhance finding: ${error.message}`);
    },
  });

  // Execute remediation mutation
  const executeRemediationMutation = useMutation({
    mutationFn: (playbookId?: string) =>
      executeRemediation(findingId, findingType, {
        playbook_id: playbookId,
        auto_approve: false,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['remediation-status', findingId, findingType] });
      toast.success('Remediation started');
    },
    onError: (error: any) => {
      toast.error(`Failed to execute remediation: ${error.message}`);
    },
  });

  const createTicketMutation = useMutation({
    mutationFn: async () =>
      createTicket({
        title: `Remediate ${findingType === 'iam_finding' ? 'IAM' : 'posture'} finding ${findingId}`,
        description: finding?.description || 'Operator-created remediation ticket from finding detail.',
        severity: finding?.severity,
        priority: finding?.severity,
        category: findingType,
        source: 'compliance',
        created_by: user?.email || undefined,
        assigned_to: user?.email || undefined,
      }),
    onSuccess: (ticket) => {
      setCreatedTicket(ticket);
      toast.success(`Remediation ticket ${ticket.id} created`);
    },
    onError: (error: any) => {
      toast.error(`Failed to create remediation ticket: ${error.message}`);
    },
  });

  const handleEnhance = () => {
    enhanceFindingMutation.mutate();
  };

  const handleExecuteRemediation = (playbookId?: string) => {
    executeRemediationMutation.mutate(playbookId);
  };
  const findingGraphHref = buildEntityGraphHref({
    entityType: findingType === 'iam_finding' ? 'identity' : 'resource',
    entityId: findingId,
    entityLabel: `${findingType === 'iam_finding' ? 'IAM' : 'Posture'} finding ${findingId}`,
    entityDomain: findingType === 'iam_finding' ? 'identity' : 'cloud',
    title: `Finding ${findingId} graph`,
    severity: finding?.severity,
    summary: finding?.description,
    sourceLabel: 'Back to finding',
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={onBack}
            className="mb-2 text-sm text-text-muted hover:text-text-main"
          >
            ← Back to Findings
          </button>
          <h1 className="text-2xl font-bold text-text-main">
            Finding Details
          </h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={findingGraphHref}
            className="rounded-md border border-border px-4 py-2 text-sm text-text-main hover:border-primary/40"
          >
            Open finding graph
          </Link>
          {createdTicket ? (
            <Link
              href={`/dashboard/tickets/${createdTicket.id}`}
              className="rounded-md border border-border px-4 py-2 text-sm text-text-main hover:border-primary/40"
            >
              Open remediation ticket
            </Link>
          ) : (
            <button
              onClick={() => createTicketMutation.mutate()}
              disabled={createTicketMutation.isPending}
              className="rounded-md border border-border px-4 py-2 text-sm text-text-main hover:border-primary/40 disabled:opacity-50"
            >
              {createTicketMutation.isPending ? 'Creating ticket...' : 'Create remediation ticket'}
            </button>
          )}
          <button
            onClick={handleEnhance}
            disabled={enhanceFindingMutation.isPending}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-bg hover:brightness-110 focus:outline-none disabled:opacity-50"
          >
            {enhanceFindingMutation.isPending ? 'Enhancing...' : 'Enhance with Compliance'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-border">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'overview', name: 'Overview' },
            { id: 'remediation', name: 'Remediation' },
            { id: 'history', name: 'History' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-text-muted hover:border-border hover:text-text-main'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'overview' && (
          <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow-sm">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium text-text-muted">
                  Finding Type
                </label>
                <p className="mt-1 text-sm text-text-main">
                  {findingType === 'iam_finding' ? 'IAM Finding' : 'Posture Finding'}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-text-muted">
                  Severity
                </label>
                <p className="mt-1 text-sm text-text-main">
                  {finding?.severity}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-text-muted">
                  Description
                </label>
                <p className="mt-1 text-sm text-text-main">
                  {finding?.description}
                </p>
              </div>
              {createdTicket && (
                <div className="rounded-lg border border-primary/20 bg-primary/10 px-4 py-3 text-sm text-text-main">
                  Remediation ticket ready:{' '}
                  <Link href={`/dashboard/tickets/${createdTicket.id}`} className="text-primary hover:text-primary/80">
                    {createdTicket.id}
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'remediation' && (
          <div className="space-y-6">
            <RemediationPlanEditor
              findingId={findingId}
              findingType={findingType}
              onExecute={handleExecuteRemediation}
            />
          </div>
        )}

        {activeTab === 'history' && (
          <RemediationHistory findingId={findingId} findingType={findingType} />
        )}
      </div>
    </div>
  );
}
