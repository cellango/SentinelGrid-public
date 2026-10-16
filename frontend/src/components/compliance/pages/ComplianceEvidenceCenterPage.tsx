'use client';

import { useMemo, useState } from 'react';
import type { ComponentType, FormEvent, SVGProps } from 'react';
import Link from 'next/link';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import {
  ArchiveBoxIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
  ClipboardDocumentCheckIcon,
  ClockIcon,
  DocumentMagnifyingGlassIcon,
  DocumentPlusIcon,
  ExclamationTriangleIcon,
  FolderOpenIcon,
  InboxStackIcon,
} from '@heroicons/react/24/outline';
import { PlanGate } from '@/components/PlanGate';
import SlideOverPanel from '@/components/ui/SlideOverPanel';
import {
  createComplianceEvidence,
  createComplianceEvidencePackage,
  exportComplianceEvidencePackage,
  getComplianceEvidence,
  getComplianceEvidencePackage,
  listComplianceEvidence,
  listComplianceEvidenceCollectionTasks,
  listComplianceEvidencePackages,
  reviewComplianceEvidence,
  type ComplianceEvidenceCollectionTask,
  type ComplianceEvidenceItem,
  type ComplianceEvidencePackage,
  type ComplianceEvidenceReviewStatus,
  type ComplianceEvidenceSensitivity,
} from '@/lib/api/compliance';

type EvidenceTab = 'inventory' | 'tasks' | 'review' | 'expiring' | 'packages';

type ManualEvidenceForm = {
  title: string;
  controlId: string;
  frameworkId: string;
  summary: string;
  storageUri: string;
  validFrom: string;
  validUntil: string;
  sensitivity: ComplianceEvidenceSensitivity;
  sourceResourceId: string;
  sourceTaskId?: string;
};

type PackageForm = {
  packageName: string;
  frameworkId: string;
  reportPeriodStart: string;
  reportPeriodEnd: string;
};

const REVIEW_QUEUE_STATUSES: ComplianceEvidenceReviewStatus[] = ['pending', 'ready_for_review', 'needs_changes'];

function addDays(days: number) {
  const value = new Date();
  value.setDate(value.getDate() + days);
  return value;
}

function formatDateInput(value: Date) {
  return value.toISOString().slice(0, 10);
}

function startOfQuarterInput() {
  const now = new Date();
  const month = Math.floor(now.getMonth() / 3) * 3;
  return formatDateInput(new Date(now.getFullYear(), month, 1));
}

function defaultManualForm(): ManualEvidenceForm {
  return {
    title: '',
    controlId: '',
    frameworkId: 'soc2',
    summary: '',
    storageUri: '',
    validFrom: formatDateInput(new Date()),
    validUntil: formatDateInput(addDays(90)),
    sensitivity: 'internal',
    sourceResourceId: '',
  };
}

function defaultPackageForm(): PackageForm {
  return {
    packageName: 'Audit evidence package',
    frameworkId: 'soc2',
    reportPeriodStart: startOfQuarterInput(),
    reportPeriodEnd: formatDateInput(new Date()),
  };
}

function normalizeLabel(value?: string | null) {
  if (!value) return 'Not set';
  return value.replace(/_/g, ' ');
}

function formatDate(value?: string | null) {
  if (!value) return 'Not set';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
}

function formatDateTime(value?: string | null) {
  if (!value) return 'Not set';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function isExpired(item: ComplianceEvidenceItem) {
  return new Date(item.valid_until).getTime() < Date.now();
}

function statusClasses(status?: string | null) {
  switch ((status || '').toLowerCase()) {
    case 'accepted':
    case 'completed':
      return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    case 'ready_for_review':
    case 'collecting':
    case 'running':
      return 'border-blue-200 bg-blue-50 text-blue-700';
    case 'pending':
      return 'border-amber-200 bg-amber-50 text-amber-700';
    case 'needs_changes':
    case 'needs_connector':
    case 'manual_evidence_required':
      return 'border-orange-200 bg-orange-50 text-orange-700';
    case 'rejected':
    case 'expired':
    case 'failed':
      return 'border-rose-200 bg-rose-50 text-rose-700';
    default:
      return 'border-border-faint bg-surface-hover text-text-muted';
  }
}

function StatusBadge({ status }: { status?: string | null }) {
  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${statusClasses(status)}`}>
      {normalizeLabel(status)}
    </span>
  );
}

function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
}: {
  title: string;
  value: number | string;
  subtitle: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
}) {
  return (
    <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-xs uppercase tracking-wide text-text-muted">{title}</p>
        <Icon className="h-6 w-6 flex-shrink-0 text-text-muted" />
      </div>
      <p className="text-3xl font-bold text-text-main">{value}</p>
      <p className="mt-1 text-xs text-text-muted">{subtitle}</p>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-dashed border-border-faint px-4 py-10 text-center">
      <InboxStackIcon className="mx-auto mb-3 h-10 w-10 text-text-muted" />
      <p className="font-medium text-text-main">{title}</p>
      <p className="mt-1 text-sm text-text-muted">{description}</p>
    </div>
  );
}

function firstControlLabel(item: ComplianceEvidenceItem) {
  const link = item.control_links?.[0];
  return link?.control_ref || link?.control_id || item.control_id || 'Unlinked';
}

function selectedTaskControl(task: ComplianceEvidenceCollectionTask) {
  const metadata = task.metadata || {};
  const controlLinks = Array.isArray(metadata.control_links) ? metadata.control_links : [];
  const firstLink = controlLinks.find((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'));
  return {
    controlId:
      typeof firstLink?.control_id === 'string'
        ? firstLink.control_id
        : typeof metadata.nist_control_id === 'string'
        ? metadata.nist_control_id
        : '',
    frameworkId: typeof firstLink?.framework_id === 'string' ? firstLink.framework_id : 'soc2',
  };
}

function fallbackHash(input: string) {
  let hash = 0;
  for (let index = 0; index < input.length; index += 1) {
    hash = (hash * 31 + input.charCodeAt(index)) | 0;
  }
  return Math.abs(hash).toString(16).padStart(8, '0').repeat(8).slice(0, 64);
}

async function sha256Hex(input: string) {
  if (globalThis.crypto?.subtle && typeof TextEncoder !== 'undefined') {
    const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(input));
    return Array.from(new Uint8Array(digest))
      .map((byte) => byte.toString(16).padStart(2, '0'))
      .join('');
  }
  return fallbackHash(input);
}

export default function ComplianceEvidenceCenterPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<EvidenceTab>('inventory');
  const [reviewStatusFilter, setReviewStatusFilter] = useState<'all' | ComplianceEvidenceReviewStatus>('all');
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [manualOpen, setManualOpen] = useState(false);
  const [manualForm, setManualForm] = useState<ManualEvidenceForm>(() => defaultManualForm());
  const [packageForm, setPackageForm] = useState<PackageForm>(() => defaultPackageForm());
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<string[]>([]);

  const evidenceQuery = useQuery({
    queryKey: ['compliance-evidence-center', 'inventory', reviewStatusFilter],
    queryFn: () =>
      listComplianceEvidence({
        limit: 100,
        review_status: reviewStatusFilter === 'all' ? undefined : reviewStatusFilter,
      }),
  });

  const expiringQuery = useQuery({
    queryKey: ['compliance-evidence-center', 'expiring'],
    queryFn: () =>
      listComplianceEvidence({
        limit: 50,
        expires_after: new Date().toISOString(),
        expires_before: addDays(30).toISOString(),
      }),
  });

  const tasksQuery = useQuery({
    queryKey: ['compliance-evidence-center', 'tasks'],
    queryFn: () => listComplianceEvidenceCollectionTasks({ limit: 100 }),
  });

  const packagesQuery = useQuery({
    queryKey: ['compliance-evidence-center', 'packages'],
    queryFn: () => listComplianceEvidencePackages({ limit: 50 }),
  });

  const selectedEvidenceQuery = useQuery({
    queryKey: ['compliance-evidence-center', 'detail', selectedEvidenceId],
    queryFn: () => getComplianceEvidence(selectedEvidenceId!),
    enabled: Boolean(selectedEvidenceId),
  });

  const selectedPackageId = selectedEvidenceQuery.data?.package_id || null;
  const selectedEvidencePackageQuery = useQuery({
    queryKey: ['compliance-evidence-center', 'package-detail', selectedPackageId],
    queryFn: () => getComplianceEvidencePackage(selectedPackageId!),
    enabled: Boolean(selectedPackageId),
  });

  const evidenceItems = evidenceQuery.data?.items || [];
  const expiringItems = expiringQuery.data?.items || [];
  const tasks = tasksQuery.data?.items || [];
  const packages = packagesQuery.data?.items || [];
  const reviewQueue = evidenceItems.filter((item) => REVIEW_QUEUE_STATUSES.includes(item.review_status));
  const selectedEvidenceItems = evidenceItems.filter((item) => selectedEvidenceIds.includes(item.id));

  const pendingTaskCount = tasks.filter((task) =>
    ['pending', 'needs_connector', 'manual_evidence_required', 'failed'].includes(task.status)
  ).length;

  const acceptedEvidenceCount = evidenceItems.filter((item) => item.review_status === 'accepted').length;
  const packageEvidenceIds = selectedEvidenceIds.length > 0
    ? selectedEvidenceIds
    : evidenceItems.filter((item) => item.review_status === 'accepted').map((item) => item.id);

  const reviewMutation = useMutation({
    mutationFn: ({ evidenceId, reviewStatus }: { evidenceId: string; reviewStatus: 'accepted' | 'rejected' | 'needs_changes' }) =>
      reviewComplianceEvidence(evidenceId, {
        review_status: reviewStatus,
        review_notes: reviewStatus === 'accepted' ? 'Accepted from Evidence Center.' : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-evidence-center'] });
      toast.success('Evidence review updated.');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to update evidence review.');
    },
  });

  const manualMutation = useMutation({
    mutationFn: async () => {
      const nowIso = new Date().toISOString();
      const content = JSON.stringify(
        {
          title: manualForm.title,
          control_id: manualForm.controlId,
          framework_id: manualForm.frameworkId,
          summary: manualForm.summary,
          storage_uri: manualForm.storageUri,
          source_task_id: manualForm.sourceTaskId,
          attested_at: nowIso,
        },
        null,
        2
      );
      const hash = await sha256Hex(content);
      const storageUri = manualForm.storageUri.trim() || `urn:sentinelgrid:evidence:manual:${hash.slice(0, 16)}`;
      return createComplianceEvidence({
        evidence_type: 'manual_attestation',
        title: manualForm.title.trim(),
        description: manualForm.summary.trim(),
        source_system: 'customer_attestation',
        source_resource_id:
          manualForm.sourceResourceId.trim() || `${manualForm.frameworkId}:${manualForm.controlId}:${hash.slice(0, 12)}`,
        collector: 'evidence_center',
        collection_method: 'manual_attestation',
        collected_at: nowIso,
        valid_from: new Date(`${manualForm.validFrom}T00:00:00`).toISOString(),
        valid_until: new Date(`${manualForm.validUntil}T23:59:59`).toISOString(),
        hash_sha256: hash,
        storage_uri: storageUri,
        summary: manualForm.summary.trim(),
        sensitivity: manualForm.sensitivity,
        review_status: 'ready_for_review',
        control_links: manualForm.controlId.trim()
          ? [
              {
                control_id: manualForm.controlId.trim(),
                framework_id: manualForm.frameworkId.trim() || undefined,
                link_type: 'supports',
                rationale: 'Manual attestation submitted from Evidence Center.',
              },
            ]
          : [],
        metadata: {
          source: 'evidence_center_manual_attestation',
          source_task_id: manualForm.sourceTaskId,
        },
        provenance: {
          submitted_from: 'evidence_center',
          attested_at: nowIso,
        },
        integrity_metadata: {
          hash_algorithm: 'sha256',
          content_format: 'manual_attestation_json',
        },
        idempotency_key: `manual:${manualForm.frameworkId}:${manualForm.controlId}:${hash}`,
      });
    },
    onSuccess: (item) => {
      queryClient.invalidateQueries({ queryKey: ['compliance-evidence-center'] });
      setSelectedEvidenceId(item.id);
      setManualOpen(false);
      setManualForm(defaultManualForm());
      toast.success('Manual evidence is ready for review.');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create manual evidence.');
    },
  });

  const packageMutation = useMutation({
    mutationFn: () =>
      createComplianceEvidencePackage({
        package_name: packageForm.packageName.trim(),
        framework_id: packageForm.frameworkId.trim() || undefined,
        report_period_start: packageForm.reportPeriodStart,
        report_period_end: packageForm.reportPeriodEnd,
        evidence_item_ids: packageEvidenceIds,
        summary: `${packageEvidenceIds.length} evidence items included.`,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-evidence-center'] });
      setSelectedEvidenceIds([]);
      toast.success('Evidence package created.');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create evidence package.');
    },
  });

  const exportMutation = useMutation({
    mutationFn: ({ packageId, format }: { packageId: string; format: 'zip' | 'pdf' | 'csv' }) =>
      exportComplianceEvidencePackage(packageId, {
        export_format: format,
        include_sensitive: false,
        metadata: { requested_from: 'evidence_center' },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-evidence-center'] });
      toast.success('Evidence package export requested.');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to request package export.');
    },
  });

  const tabs = useMemo(
    () => [
      { id: 'inventory' as const, label: 'Inventory', count: evidenceQuery.data?.count || 0 },
      { id: 'tasks' as const, label: 'Collection tasks', count: pendingTaskCount },
      { id: 'review' as const, label: 'Review queue', count: reviewQueue.length },
      { id: 'expiring' as const, label: 'Expiring', count: expiringQuery.data?.count || 0 },
      { id: 'packages' as const, label: 'Packages', count: packagesQuery.data?.count || 0 },
    ],
    [evidenceQuery.data?.count, expiringQuery.data?.count, packagesQuery.data?.count, pendingTaskCount, reviewQueue.length]
  );

  function toggleEvidenceSelection(evidenceId: string) {
    setSelectedEvidenceIds((current) =>
      current.includes(evidenceId) ? current.filter((id) => id !== evidenceId) : [...current, evidenceId]
    );
  }

  function openManualAttestation(task?: ComplianceEvidenceCollectionTask) {
    if (!task) {
      setManualForm(defaultManualForm());
      setManualOpen(true);
      return;
    }
    const taskControl = selectedTaskControl(task);
    setManualForm({
      ...defaultManualForm(),
      title: task.task_name || 'Manual evidence attestation',
      controlId: taskControl.controlId,
      frameworkId: taskControl.frameworkId,
      summary: task.error_message || task.task_name || '',
      sourceResourceId: task.source_resource_id || task.id,
      sourceTaskId: task.id,
    });
    setManualOpen(true);
  }

  async function handleManualSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!manualForm.title.trim() || !manualForm.controlId.trim() || !manualForm.summary.trim()) {
      toast.error('Title, control, and summary are required.');
      return;
    }
    if (!manualForm.validFrom || !manualForm.validUntil) {
      toast.error('Valid from and valid until dates are required.');
      return;
    }
    await manualMutation.mutateAsync();
  }

  function handlePackageSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!packageForm.packageName.trim()) {
      toast.error('Package name is required.');
      return;
    }
    packageMutation.mutate();
  }

  return (
    <PlanGate requiredTier="protect_defend_comply">
      <div className="p-6">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-text-main">Evidence Center</h1>
            <p className="mt-2 max-w-3xl text-text-muted">
              Manage compliance evidence, collection work, review decisions, expiration risk, and export packages.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => openManualAttestation()}
              className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
            >
              <DocumentPlusIcon className="mr-2 h-5 w-5" />
              Manual attestation
            </button>
            <Link
              href="/dashboard/compliance/reports"
              className="inline-flex items-center rounded-lg border border-border-faint bg-surface-hover px-4 py-2 text-sm font-medium text-text-main hover:bg-surface-input"
            >
              <ArrowDownTrayIcon className="mr-2 h-5 w-5" />
              Reports
            </Link>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          <MetricCard
            title="Evidence items"
            value={evidenceQuery.data?.count || 0}
            subtitle={`${acceptedEvidenceCount} accepted`}
            icon={InboxStackIcon}
          />
          <MetricCard
            title="Review queue"
            value={reviewQueue.length}
            subtitle="Pending owner decision"
            icon={ClipboardDocumentCheckIcon}
          />
          <MetricCard title="Collection tasks" value={pendingTaskCount} subtitle="Open collection work" icon={ClockIcon} />
          <MetricCard title="Expiring soon" value={expiringQuery.data?.count || 0} subtitle="Valid for 30 days or less" icon={ExclamationTriangleIcon} />
          <MetricCard title="Packages" value={packagesQuery.data?.count || 0} subtitle="Prepared audit packets" icon={ArchiveBoxIcon} />
        </div>

        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary bg-primary text-white'
                    : 'border-border-faint bg-surface-card text-text-main hover:bg-surface-hover'
                }`}
              >
                {tab.label}
                <span
                  className={`ml-2 rounded-full px-2 py-0.5 text-xs ${
                    activeTab === tab.id ? 'bg-surface-card/20 text-white' : 'bg-surface-hover text-text-muted'
                  }`}
                >
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="evidence-review-filter" className="text-sm font-medium text-text-main">
              Review status
            </label>
            <select
              id="evidence-review-filter"
              value={reviewStatusFilter}
              onChange={(event) => setReviewStatusFilter(event.target.value as typeof reviewStatusFilter)}
              className="rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="ready_for_review">Ready for review</option>
              <option value="accepted">Accepted</option>
              <option value="needs_changes">Needs changes</option>
              <option value="expired">Expired</option>
            </select>
          </div>
        </div>

        {activeTab === 'inventory' && (
          <EvidenceInventory
            items={evidenceItems}
            isLoading={evidenceQuery.isLoading}
            selectedEvidenceIds={selectedEvidenceIds}
            onToggleSelect={toggleEvidenceSelection}
            onOpenEvidence={setSelectedEvidenceId}
          />
        )}

        {activeTab === 'tasks' && (
          <CollectionTasksTable
            tasks={tasks}
            isLoading={tasksQuery.isLoading}
            onManualAttestation={openManualAttestation}
          />
        )}

        {activeTab === 'review' && (
          <ReviewQueue
            items={reviewQueue}
            isLoading={evidenceQuery.isLoading}
            onOpenEvidence={setSelectedEvidenceId}
            onReview={(evidenceId, reviewStatus) => reviewMutation.mutate({ evidenceId, reviewStatus })}
            isReviewing={reviewMutation.isPending}
          />
        )}

        {activeTab === 'expiring' && (
          <EvidenceInventory
            items={expiringItems}
            isLoading={expiringQuery.isLoading}
            selectedEvidenceIds={selectedEvidenceIds}
            onToggleSelect={toggleEvidenceSelection}
            onOpenEvidence={setSelectedEvidenceId}
            emptyTitle="No evidence expiring soon"
            emptyDescription="Evidence with a validity window ending in the next 30 days appears here."
          />
        )}

        {activeTab === 'packages' && (
          <EvidencePackagesPanel
            packages={packages}
            isLoading={packagesQuery.isLoading}
            packageForm={packageForm}
            selectedEvidenceItems={selectedEvidenceItems}
            fallbackEvidenceCount={packageEvidenceIds.length}
            onPackageFormChange={setPackageForm}
            onSubmit={handlePackageSubmit}
            isCreatingPackage={packageMutation.isPending}
            onExport={(packageId, format) => exportMutation.mutate({ packageId, format })}
            isExporting={exportMutation.isPending}
          />
        )}

        <EvidenceDetailPanel
          evidence={selectedEvidenceQuery.data}
          packageDetail={selectedEvidencePackageQuery.data}
          isLoading={selectedEvidenceQuery.isLoading}
          open={Boolean(selectedEvidenceId)}
          onClose={() => setSelectedEvidenceId(null)}
          onReview={(evidenceId, reviewStatus) => reviewMutation.mutate({ evidenceId, reviewStatus })}
          isReviewing={reviewMutation.isPending}
        />

        <SlideOverPanel
          open={manualOpen}
          onClose={() => setManualOpen(false)}
          title="Manual Attestation"
          subtitle={manualForm.controlId || 'Customer-provided evidence'}
          width="lg"
        >
          <form onSubmit={handleManualSubmit} className="space-y-5">
            <div>
              <label htmlFor="manual-evidence-title" className="mb-1 block text-sm font-medium text-text-main">
                Title
              </label>
              <input
                id="manual-evidence-title"
                value={manualForm.title}
                onChange={(event) => setManualForm((current) => ({ ...current, title: event.target.value }))}
                className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="manual-evidence-control" className="mb-1 block text-sm font-medium text-text-main">
                  Control
                </label>
                <input
                  id="manual-evidence-control"
                  value={manualForm.controlId}
                  onChange={(event) => setManualForm((current) => ({ ...current, controlId: event.target.value }))}
                  placeholder="CC6.1"
                  className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label htmlFor="manual-evidence-framework" className="mb-1 block text-sm font-medium text-text-main">
                  Framework
                </label>
                <input
                  id="manual-evidence-framework"
                  value={manualForm.frameworkId}
                  onChange={(event) => setManualForm((current) => ({ ...current, frameworkId: event.target.value }))}
                  className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>
            <div>
              <label htmlFor="manual-evidence-summary" className="mb-1 block text-sm font-medium text-text-main">
                Summary
              </label>
              <textarea
                id="manual-evidence-summary"
                value={manualForm.summary}
                onChange={(event) => setManualForm((current) => ({ ...current, summary: event.target.value }))}
                rows={5}
                className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label htmlFor="manual-evidence-storage" className="mb-1 block text-sm font-medium text-text-main">
                Evidence URL or storage URI
              </label>
              <input
                id="manual-evidence-storage"
                value={manualForm.storageUri}
                onChange={(event) => setManualForm((current) => ({ ...current, storageUri: event.target.value }))}
                placeholder="s3://evidence/manual/file.pdf"
                className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <div>
                <label htmlFor="manual-evidence-valid-from" className="mb-1 block text-sm font-medium text-text-main">
                  Valid from
                </label>
                <input
                  id="manual-evidence-valid-from"
                  type="date"
                  value={manualForm.validFrom}
                  onChange={(event) => setManualForm((current) => ({ ...current, validFrom: event.target.value }))}
                  className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label htmlFor="manual-evidence-valid-until" className="mb-1 block text-sm font-medium text-text-main">
                  Valid until
                </label>
                <input
                  id="manual-evidence-valid-until"
                  type="date"
                  value={manualForm.validUntil}
                  onChange={(event) => setManualForm((current) => ({ ...current, validUntil: event.target.value }))}
                  className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label htmlFor="manual-evidence-sensitivity" className="mb-1 block text-sm font-medium text-text-main">
                  Sensitivity
                </label>
                <select
                  id="manual-evidence-sensitivity"
                  value={manualForm.sensitivity}
                  onChange={(event) =>
                    setManualForm((current) => ({
                      ...current,
                      sensitivity: event.target.value as ComplianceEvidenceSensitivity,
                    }))
                  }
                  className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="restricted">Restricted</option>
                </select>
              </div>
            </div>
            <button
              type="submit"
              disabled={manualMutation.isPending}
              className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
            >
              <DocumentPlusIcon className="mr-2 h-5 w-5" />
              {manualMutation.isPending ? 'Saving...' : 'Save attestation'}
            </button>
          </form>
        </SlideOverPanel>
      </div>
    </PlanGate>
  );
}

function EvidenceInventory({
  items,
  isLoading,
  selectedEvidenceIds,
  onToggleSelect,
  onOpenEvidence,
  emptyTitle = 'No evidence found',
  emptyDescription = 'Evidence appears here when collectors or manual attestations write to the repository.',
}: {
  items: ComplianceEvidenceItem[];
  isLoading: boolean;
  selectedEvidenceIds: string[];
  onToggleSelect: (evidenceId: string) => void;
  onOpenEvidence: (evidenceId: string) => void;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  if (isLoading) {
    return <div className="rounded-lg border border-border-faint bg-surface-card p-8 text-sm text-text-muted">Loading evidence...</div>;
  }
  if (items.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-surface-card-border bg-surface-card shadow">
      <table className="min-w-full divide-y divide-border-faint">
        <thead className="bg-surface-hover">
          <tr>
            <th className="w-12 px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">
              <span className="sr-only">Select</span>
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Evidence</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Control</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Status</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Valid until</th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-text-muted">Source</th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-text-muted">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-faint">
          {items.map((item) => (
            <tr key={item.id} className={isExpired(item) ? 'bg-rose-50/40' : undefined}>
              <td className="px-4 py-4 align-top">
                <input
                  type="checkbox"
                  aria-label={`Select ${item.title}`}
                  checked={selectedEvidenceIds.includes(item.id)}
                  onChange={() => onToggleSelect(item.id)}
                  className="h-4 w-4 rounded border-border-faint text-primary focus:ring-primary"
                />
              </td>
              <td className="px-4 py-4 align-top">
                <p className="font-medium text-text-main">{item.title}</p>
                <p className="mt-1 max-w-xl text-sm text-text-muted">{item.summary || item.description}</p>
                <p className="mt-2 text-xs text-text-muted">{normalizeLabel(item.evidence_type)} - {item.sensitivity}</p>
              </td>
              <td className="px-4 py-4 align-top text-sm text-text-main">{firstControlLabel(item)}</td>
              <td className="px-4 py-4 align-top">
                <StatusBadge status={item.review_status} />
              </td>
              <td className="px-4 py-4 align-top text-sm text-text-main">{formatDate(item.valid_until)}</td>
              <td className="px-4 py-4 align-top text-sm text-text-muted">
                <div>{item.source_system}</div>
                <div className="mt-1 text-xs">{item.collection_method}</div>
              </td>
              <td className="px-4 py-4 text-right align-top">
                <button
                  onClick={() => onOpenEvidence(item.id)}
                  className="inline-flex items-center rounded-lg border border-border-faint px-3 py-2 text-sm font-medium text-text-main hover:bg-surface-hover"
                >
                  <DocumentMagnifyingGlassIcon className="mr-2 h-4 w-4" />
                  Details
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CollectionTasksTable({
  tasks,
  isLoading,
  onManualAttestation,
}: {
  tasks: ComplianceEvidenceCollectionTask[];
  isLoading: boolean;
  onManualAttestation: (task: ComplianceEvidenceCollectionTask) => void;
}) {
  if (isLoading) {
    return <div className="rounded-lg border border-border-faint bg-surface-card p-8 text-sm text-text-muted">Loading collection tasks...</div>;
  }
  if (tasks.length === 0) {
    return <EmptyState title="No collection tasks" description="Connector gaps and manual evidence work appear here." />;
  }
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {tasks.map((task) => (
        <div key={task.id} className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-text-main">{task.task_name}</p>
              <p className="mt-1 text-sm text-text-muted">{task.error_message || normalizeLabel(task.task_type)}</p>
            </div>
            <StatusBadge status={task.status} />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-text-muted">Source</p>
              <p className="mt-1 text-text-main">{task.source_system || 'Not set'}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-text-muted">Due</p>
              <p className="mt-1 text-text-main">{formatDate(task.due_at)}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-text-muted">Requested by</p>
              <p className="mt-1 text-text-main">{task.requested_by || 'System'}</p>
            </div>
          </div>
          {task.status === 'manual_evidence_required' ? (
            <button
              onClick={() => onManualAttestation(task)}
              className="mt-5 inline-flex items-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90"
            >
              <DocumentPlusIcon className="mr-2 h-4 w-4" />
              Add attestation
            </button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function ReviewQueue({
  items,
  isLoading,
  onOpenEvidence,
  onReview,
  isReviewing,
}: {
  items: ComplianceEvidenceItem[];
  isLoading: boolean;
  onOpenEvidence: (evidenceId: string) => void;
  onReview: (evidenceId: string, reviewStatus: 'accepted' | 'rejected' | 'needs_changes') => void;
  isReviewing: boolean;
}) {
  if (isLoading) {
    return <div className="rounded-lg border border-border-faint bg-surface-card p-8 text-sm text-text-muted">Loading review queue...</div>;
  }
  if (items.length === 0) {
    return <EmptyState title="Review queue clear" description="Pending, ready, and needs-changes evidence appears here." />;
  }
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.id} className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold text-text-main">{item.title}</p>
                <StatusBadge status={item.review_status} />
              </div>
              <p className="mt-2 text-sm text-text-muted">{item.summary}</p>
              <p className="mt-2 text-xs text-text-muted">
                {firstControlLabel(item)} - collected {formatDate(item.collected_at)} - valid until {formatDate(item.valid_until)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => onOpenEvidence(item.id)}
                className="rounded-lg border border-border-faint px-3 py-2 text-sm font-medium text-text-main hover:bg-surface-hover"
              >
                Details
              </button>
              <button
                onClick={() => onReview(item.id, 'needs_changes')}
                disabled={isReviewing}
                className="rounded-lg border border-orange-200 px-3 py-2 text-sm font-medium text-orange-700 hover:bg-orange-50 disabled:opacity-50"
              >
                Needs changes
              </button>
              <button
                onClick={() => onReview(item.id, 'accepted')}
                disabled={isReviewing}
                className="inline-flex items-center rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                <CheckCircleIcon className="mr-2 h-4 w-4" />
                Accept
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function EvidencePackagesPanel({
  packages,
  isLoading,
  packageForm,
  selectedEvidenceItems,
  fallbackEvidenceCount,
  onPackageFormChange,
  onSubmit,
  isCreatingPackage,
  onExport,
  isExporting,
}: {
  packages: ComplianceEvidencePackage[];
  isLoading: boolean;
  packageForm: PackageForm;
  selectedEvidenceItems: ComplianceEvidenceItem[];
  fallbackEvidenceCount: number;
  onPackageFormChange: (form: PackageForm) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  isCreatingPackage: boolean;
  onExport: (packageId: string, format: 'zip' | 'pdf' | 'csv') => void;
  isExporting: boolean;
}) {
  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-semibold text-text-main">Evidence packages</h2>
            <p className="mt-1 text-sm text-text-muted">Packages preserve selected evidence for audit and customer exports.</p>
          </div>
          <FolderOpenIcon className="h-7 w-7 text-text-muted" />
        </div>
        {isLoading ? (
          <p className="text-sm text-text-muted">Loading packages...</p>
        ) : packages.length === 0 ? (
          <EmptyState title="No packages yet" description="Create a package from selected or accepted evidence." />
        ) : (
          <div className="space-y-3">
            {packages.map((item) => (
              <div key={item.id} className="rounded-lg border border-border-faint px-4 py-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="font-semibold text-text-main">{item.package_name}</p>
                      <StatusBadge status={item.status} />
                      {item.review_status ? <StatusBadge status={item.review_status} /> : null}
                    </div>
                    <p className="mt-2 text-sm text-text-muted">
                      {item.framework_id || 'Any framework'} - {formatDate(item.report_period_start)} to {formatDate(item.report_period_end)}
                    </p>
                    <p className="mt-1 text-xs text-text-muted">{item.evidence_item_count || 0} evidence items</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onExport(item.id, 'zip')}
                      disabled={isExporting}
                      className="inline-flex items-center rounded-lg border border-border-faint px-3 py-2 text-sm font-medium text-text-main hover:bg-surface-hover disabled:opacity-50"
                    >
                      <ArchiveBoxIcon className="mr-2 h-4 w-4" />
                      ZIP
                    </button>
                    <button
                      onClick={() => onExport(item.id, 'csv')}
                      disabled={isExporting}
                      className="inline-flex items-center rounded-lg border border-border-faint px-3 py-2 text-sm font-medium text-text-main hover:bg-surface-hover disabled:opacity-50"
                    >
                      CSV
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
        <h2 className="text-lg font-semibold text-text-main">Create package</h2>
        <p className="mt-1 text-sm text-text-muted">
          {selectedEvidenceItems.length > 0
            ? `${selectedEvidenceItems.length} selected evidence items`
            : `${fallbackEvidenceCount} accepted evidence items`}
        </p>
        <div className="mt-4 space-y-4">
          <div>
            <label htmlFor="package-name" className="mb-1 block text-sm font-medium text-text-main">
              Name
            </label>
            <input
              id="package-name"
              value={packageForm.packageName}
              onChange={(event) => onPackageFormChange({ ...packageForm, packageName: event.target.value })}
              className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div>
            <label htmlFor="package-framework" className="mb-1 block text-sm font-medium text-text-main">
              Framework
            </label>
            <input
              id="package-framework"
              value={packageForm.frameworkId}
              onChange={(event) => onPackageFormChange({ ...packageForm, frameworkId: event.target.value })}
              className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="grid grid-cols-1 gap-3">
            <div>
              <label htmlFor="package-start" className="mb-1 block text-sm font-medium text-text-main">
                Period start
              </label>
              <input
                id="package-start"
                type="date"
                value={packageForm.reportPeriodStart}
                onChange={(event) => onPackageFormChange({ ...packageForm, reportPeriodStart: event.target.value })}
                className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label htmlFor="package-end" className="mb-1 block text-sm font-medium text-text-main">
                Period end
              </label>
              <input
                id="package-end"
                type="date"
                value={packageForm.reportPeriodEnd}
                onChange={(event) => onPackageFormChange({ ...packageForm, reportPeriodEnd: event.target.value })}
                className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={isCreatingPackage || fallbackEvidenceCount === 0}
            className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
          >
            <ArchiveBoxIcon className="mr-2 h-5 w-5" />
            {isCreatingPackage ? 'Creating...' : 'Create package'}
          </button>
        </div>
      </form>
    </div>
  );
}

function EvidenceDetailPanel({
  evidence,
  packageDetail,
  isLoading,
  open,
  onClose,
  onReview,
  isReviewing,
}: {
  evidence?: ComplianceEvidenceItem;
  packageDetail?: ComplianceEvidencePackage;
  isLoading: boolean;
  open: boolean;
  onClose: () => void;
  onReview: (evidenceId: string, reviewStatus: 'accepted' | 'rejected' | 'needs_changes') => void;
  isReviewing: boolean;
}) {
  return (
    <SlideOverPanel
      open={open}
      onClose={onClose}
      title={evidence?.title || 'Evidence detail'}
      subtitle={evidence ? `${firstControlLabel(evidence)} - ${normalizeLabel(evidence.review_status)}` : undefined}
      width="xl"
    >
      {isLoading || !evidence ? (
        <p className="text-sm text-text-muted">Loading evidence detail...</p>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={evidence.review_status} />
            <StatusBadge status={evidence.sensitivity} />
            {isExpired(evidence) ? <StatusBadge status="expired" /> : null}
          </div>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Summary</h3>
            <p className="text-sm text-text-main">{evidence.summary || evidence.description || 'No summary provided.'}</p>
          </section>

          <section className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <DetailField label="Source system" value={evidence.source_system} />
            <DetailField label="Collection method" value={evidence.collection_method} />
            <DetailField label="Collected" value={formatDateTime(evidence.collected_at)} />
            <DetailField label="Valid until" value={formatDateTime(evidence.valid_until)} />
            <DetailField label="Storage URI" value={evidence.storage_uri} />
            <DetailField label="SHA-256" value={evidence.hash_sha256} />
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Linked controls</h3>
            {(evidence.control_links || []).length > 0 ? (
              <div className="space-y-2">
                {evidence.control_links?.map((link) => (
                  <div key={link.id || `${link.framework_id}:${link.control_id}`} className="rounded-lg border border-border-faint px-3 py-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium text-text-main">{link.control_ref || link.control_id}</span>
                      {link.framework_code || link.framework_id ? (
                        <span className="rounded-full border border-border-faint bg-surface-hover px-2 py-0.5 text-xs text-text-muted">
                          {link.framework_code || link.framework_id}
                        </span>
                      ) : null}
                      <StatusBadge status={link.status || link.link_type} />
                    </div>
                    {link.rationale ? <p className="mt-1 text-xs text-text-muted">{link.rationale}</p> : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-muted">No control links recorded.</p>
            )}
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Review history</h3>
            {(evidence.reviews || []).length > 0 ? (
              <div className="space-y-2">
                {evidence.reviews?.map((review) => (
                  <div key={review.id} className="rounded-lg border border-border-faint px-3 py-2 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <StatusBadge status={review.review_status} />
                      <span className="text-xs text-text-muted">{formatDateTime(review.reviewed_at)}</span>
                    </div>
                    <p className="mt-1 text-text-main">{review.reviewer}</p>
                    {review.review_notes ? <p className="mt-1 text-text-muted">{review.review_notes}</p> : null}
                    {review.rejection_reason ? <p className="mt-1 text-rose-700">{review.rejection_reason}</p> : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-muted">No reviews recorded.</p>
            )}
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">Package and export state</h3>
            {packageDetail ? (
              <div className="rounded-lg border border-border-faint px-3 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium text-text-main">{packageDetail.package_name}</p>
                  <StatusBadge status={packageDetail.status} />
                </div>
                <p className="mt-1 text-sm text-text-muted">
                  {formatDate(packageDetail.report_period_start)} to {formatDate(packageDetail.report_period_end)}
                </p>
                {(packageDetail.exports || []).length > 0 ? (
                  <div className="mt-3 space-y-2">
                    {packageDetail.exports?.map((item) => (
                      <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-surface-hover px-3 py-2 text-sm">
                        <span className="text-text-main">{item.export_format.toUpperCase()}</span>
                        <StatusBadge status={item.status} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-text-muted">No exports requested for this package.</p>
                )}
              </div>
            ) : evidence.package_id ? (
              <p className="text-sm text-text-muted">Package detail is loading.</p>
            ) : (
              <p className="text-sm text-text-muted">This evidence is not attached to a package.</p>
            )}
          </section>

          <div className="flex flex-wrap gap-2 border-t border-border-faint pt-4">
            <button
              onClick={() => onReview(evidence.id, 'needs_changes')}
              disabled={isReviewing}
              className="rounded-lg border border-orange-200 px-3 py-2 text-sm font-medium text-orange-700 hover:bg-orange-50 disabled:opacity-50"
            >
              Needs changes
            </button>
            <button
              onClick={() => onReview(evidence.id, 'rejected')}
              disabled={isReviewing}
              className="rounded-lg border border-rose-200 px-3 py-2 text-sm font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            >
              Reject
            </button>
            <button
              onClick={() => onReview(evidence.id, 'accepted')}
              disabled={isReviewing}
              className="inline-flex items-center rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              <CheckCircleIcon className="mr-2 h-4 w-4" />
              Accept
            </button>
          </div>
        </div>
      )}
    </SlideOverPanel>
  );
}

function DetailField({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-lg border border-border-faint bg-surface-hover px-3 py-2">
      <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
      <p className="mt-1 break-words text-sm text-text-main">{value || 'Not set'}</p>
    </div>
  );
}
