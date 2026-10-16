'use client';

import React, { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getComplianceDashboard,
  getSoc2Coverage,
  listComplianceEvidencePackages,
  type ComplianceEvidencePackage,
  type ComplianceFrameworkCoverage,
} from '@/lib/api/compliance';
import {
  createScheduledReport,
  createShare,
  deleteShare,
  generateReport,
  getReportDownload,
  listScheduledReports,
  listReports,
  listShares,
  listTemplates,
  type Report,
  type ScheduleConfig,
  type ReportTemplate,
  type Share,
} from '@/lib/api/reports';
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  CalendarIcon,
  DocumentTextIcon,
  LinkIcon,
  PlusCircleIcon,
  TrashIcon,
} from '@heroicons/react/24/outline';
import { PlanGate } from '@/components/PlanGate';
import { useAuth } from '@/lib/providers/AuthProvider';
import {
  TRUST_ARTIFACTS,
  isTrustArtifactTemplateKey,
  slugifyTemplateName,
  type TrustArtifactDefinition,
} from '@/lib/trustArtifacts';
import { getComplianceRuntimeLabels } from '@/lib/compliance/features';
import { toast } from 'react-hot-toast';

const QuestionnaireAssistPanel = dynamic(
  () => import('@/components/compliance/QuestionnaireAssistPanel').then((mod) => mod.QuestionnaireAssistPanel),
  {
    loading: () => (
      <div className="rounded-xl border border-border-faint bg-surface-card p-4 text-sm text-text-muted">
        Loading questionnaire assist…
      </div>
    ),
  }
);

const SecurityReviewResponseTemplatesPanel = dynamic(
  () =>
    import('@/components/compliance/SecurityReviewResponseTemplatesPanel').then(
      (mod) => mod.SecurityReviewResponseTemplatesPanel
    ),
  {
    loading: () => (
      <div className="rounded-xl border border-border-faint bg-surface-card p-4 text-sm text-text-muted">
        Loading response templates…
      </div>
    ),
  }
);

const TrustArtifactCatalog = dynamic(
  () => import('@/components/TrustArtifactCatalog').then((mod) => mod.TrustArtifactCatalog),
  {
    loading: () => (
      <div className="rounded-xl border border-border-faint bg-surface-card p-4 text-sm text-text-muted">
        Loading trust artifacts…
      </div>
    ),
  }
);

function statusClasses(status: string) {
  switch (status) {
    case 'compliant':
      return 'bg-emerald-50 border-emerald-200 text-emerald-700';
    case 'partial':
      return 'bg-amber-50 border-amber-200 text-amber-700';
    case 'non_compliant':
      return 'bg-rose-50 border-rose-200 text-rose-700';
    default:
      return 'border-border-faint bg-surface-hover text-text-muted';
  }
}

function createDefaultRange() {
  const end = new Date();
  const start = new Date();
  start.setDate(end.getDate() - 90);

  const toDateInput = (value: Date) => value.toISOString().slice(0, 10);

  return {
    start: toDateInput(start),
    end: toDateInput(end),
  };
}

function normalizeStatus(status?: string) {
  const value = (status || '').toLowerCase();
  return value === 'completed' ? 'ready' : value || 'unknown';
}

function triggerDownload(url: string, filename?: string) {
  const anchor = document.createElement('a');
  anchor.href = url;
  if (filename) {
    anchor.download = filename;
  }
  anchor.target = '_blank';
  anchor.rel = 'noopener noreferrer';
  anchor.click();
}

function getTemplateKeyFromReport(report: Report) {
  const metadataTemplateKey =
    typeof report.metadata?.template_key === 'string' ? report.metadata.template_key : undefined;
  if (metadataTemplateKey) {
    return metadataTemplateKey;
  }

  const metadataTemplateName =
    typeof report.metadata?.template_name === 'string' ? report.metadata.template_name : undefined;
  if (metadataTemplateName) {
    return slugifyTemplateName(metadataTemplateName);
  }

  return undefined;
}

function formatShareDate(value?: string | null) {
  return value ? new Date(value).toLocaleDateString() : 'No expiration set';
}

function normalizeRole(value: string) {
  return value.trim().toLowerCase().replace(/[-\s]+/g, '_');
}

function canUseTemplate(template: ReportTemplate | undefined, userRoles: string[]) {
  const requiredRoles = (template?.required_roles || []).map(normalizeRole).filter(Boolean);
  if (!template || requiredRoles.length === 0) {
    return true;
  }

  const normalizedUserRoles = userRoles.map(normalizeRole);
  const bypassRoles = ['admin', 'superadmin', 'super_admin', 'tenant_admin'];
  return requiredRoles.some((role) => normalizedUserRoles.includes(role)) ||
    bypassRoles.some((role) => normalizedUserRoles.includes(role));
}

function requiredRoleLabel(template: ReportTemplate | undefined) {
  return (template?.required_roles || []).join(', ');
}

function asStringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

function getReportInputs(report?: Report | null) {
  const metadata = report?.metadata || {};
  const reportInputs = metadata.report_inputs && typeof metadata.report_inputs === 'object'
    ? metadata.report_inputs as Record<string, unknown>
    : {};
  return {
    frameworkIds: asStringArray(reportInputs.framework_ids),
    controlIds: asStringArray(reportInputs.control_ids),
    evidencePackageIds: asStringArray(reportInputs.evidence_package_ids),
    includeGaps: reportInputs.include_gaps !== false,
    includeExpiredEvidence: reportInputs.include_expired_evidence === true,
    dateRange: reportInputs.date_range && typeof reportInputs.date_range === 'object'
      ? reportInputs.date_range as Record<string, unknown>
      : {},
  };
}

function getReportSnapshot(report?: Report | null) {
  const snapshot = report?.metadata?.compliance_snapshot;
  return snapshot && typeof snapshot === 'object' ? snapshot as Record<string, any> : null;
}

function evidenceBasisLabel(evidencePackageIds: string[]) {
  return evidencePackageIds.length > 0 ? 'Evidence-backed' : 'Readiness-only';
}

function frameworkLabel(frameworks: ComplianceFrameworkCoverage[], frameworkId: string) {
  const framework = frameworks.find((item) => item.framework_id === frameworkId);
  return framework?.framework_name || framework?.framework_code || frameworkId;
}

function packageLabel(packages: ComplianceEvidencePackage[], packageId: string) {
  const evidencePackage = packages.find((item) => item.id === packageId);
  return evidencePackage?.package_name || packageId;
}

function ReportSnapshotDetails({
  report,
  frameworks,
  packages,
}: {
  report: Report;
  frameworks: ComplianceFrameworkCoverage[];
  packages: ComplianceEvidencePackage[];
}) {
  const inputs = getReportInputs(report);
  const snapshot = getReportSnapshot(report);
  const evidenceSummary = snapshot?.evidence_summary || {};
  const snapshotHash =
    typeof report.metadata?.compliance_snapshot_hash_sha256 === 'string'
      ? report.metadata.compliance_snapshot_hash_sha256
      : typeof snapshot?.snapshot_hash_sha256 === 'string'
      ? snapshot.snapshot_hash_sha256
      : null;

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Report snapshot</p>
          <p className="mt-1 font-semibold">{report.metadata?.template_name || report.name}</p>
        </div>
        <span className="rounded-full border border-blue-200 bg-white px-3 py-1 text-xs font-semibold text-blue-700">
          {evidenceBasisLabel(inputs.evidencePackageIds)}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-blue-700">Frameworks</dt>
          <dd className="mt-1 text-blue-950">
            {inputs.frameworkIds.length > 0
              ? inputs.frameworkIds.map((id) => frameworkLabel(frameworks, id)).join(', ')
              : 'Not scoped'}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-blue-700">Evidence packages</dt>
          <dd className="mt-1 text-blue-950">
            {inputs.evidencePackageIds.length > 0
              ? inputs.evidencePackageIds.map((id) => packageLabel(packages, id)).join(', ')
              : 'No package selected'}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-blue-700">Snapshot state</dt>
          <dd className="mt-1 text-blue-950">
            {snapshotHash ? `Captured ${snapshotHash.slice(0, 10)}...` : snapshot?.status || 'Pending background generation'}
          </dd>
        </div>
      </dl>

      {evidenceSummary && Object.keys(evidenceSummary).length > 0 ? (
        <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-blue-900 sm:grid-cols-3">
          <span>{Number(evidenceSummary.evidence_package_count || 0)} packages</span>
          <span>{Number(evidenceSummary.evidence_item_count || 0)} evidence items</span>
          <span>{Number(evidenceSummary.accepted_evidence_item_count || 0)} accepted items</span>
        </div>
      ) : null}
    </div>
  );
}

export default function ComplianceReportsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [selectedReportType, setSelectedReportType] = useState<'all' | 'compliance' | 'soc2'>('all');
  const [dateRange, setDateRange] = useState(createDefaultRange);
  const [selectedFrameworkIds, setSelectedFrameworkIds] = useState<string[]>([]);
  const [selectedEvidencePackageIds, setSelectedEvidencePackageIds] = useState<string[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [selectedFormat, setSelectedFormat] = useState<'pdf' | 'csv'>('pdf');
  const [includeGaps, setIncludeGaps] = useState(true);
  const [includeExpiredEvidence, setIncludeExpiredEvidence] = useState(false);
  const [lastGeneratedReport, setLastGeneratedReport] = useState<Report | null>(null);
  const [scheduleTemplateId, setScheduleTemplateId] = useState<string>('');
  const [scheduleFrequency, setScheduleFrequency] = useState<ScheduleConfig['frequency']>('monthly');
  const [scheduleDay, setScheduleDay] = useState('1');
  const [scheduleTime, setScheduleTime] = useState('09:00');
  const [scheduleRecipients, setScheduleRecipients] = useState('');
  const runtimeLabels = getComplianceRuntimeLabels();
  const userRoles = user?.roles || [];

  const { data: coverage, isLoading: coverageLoading } = useQuery({
    queryKey: ['soc2-coverage-reporting'],
    queryFn: getSoc2Coverage,
  });

  const { data: dashboard } = useQuery({
    queryKey: ['compliance-dashboard-reporting-scope'],
    queryFn: getComplianceDashboard,
  });

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['report-templates', 'compliance-exports'],
    queryFn: () => listTemplates(),
  });

  const selectedFrameworkFilter =
    selectedFrameworkIds.length === 1 ? selectedFrameworkIds[0] : undefined;

  const { data: evidencePackagesPayload, isLoading: evidencePackagesLoading } = useQuery({
    queryKey: ['compliance-evidence-packages-reporting', selectedFrameworkFilter || 'all'],
    queryFn: () =>
      listComplianceEvidencePackages({
        framework_id: selectedFrameworkFilter,
        limit: 50,
      }),
  });

  const { data: reports = [], isLoading: reportsLoading } = useQuery({
    queryKey: ['compliance-reports', selectedReportType],
    queryFn: () =>
      listReports({
        limit: 50,
        report_type: selectedReportType === 'all' ? undefined : selectedReportType,
      }),
  });

  const { data: scheduledReports = [] } = useQuery({
    queryKey: ['compliance-report-schedules'],
    queryFn: listScheduledReports,
  });

  const frameworkOptions = dashboard?.framework_coverage?.items || [];
  const evidencePackages = evidencePackagesPayload?.items || [];
  const supportedReportTemplates = useMemo(
    () =>
      templates.filter(
        (template) =>
          template.type === 'compliance' ||
          template.type === 'soc2' ||
          TRUST_ARTIFACTS.some((artifact) => artifact.templateName === template.name)
      ),
    [templates]
  );
  const selectedTemplate = supportedReportTemplates.find((template) => template.id === selectedTemplateId);
  const selectedTemplateAllowed = canUseTemplate(selectedTemplate, userRoles);
  const selectedEvidenceBasis = evidenceBasisLabel(selectedEvidencePackageIds);

  useEffect(() => {
    if (selectedFrameworkIds.length === 0 && frameworkOptions.length > 0) {
      setSelectedFrameworkIds([frameworkOptions[0].framework_id]);
    }
  }, [frameworkOptions, selectedFrameworkIds.length]);

  useEffect(() => {
    if (!selectedTemplateId && supportedReportTemplates.length > 0) {
      setSelectedTemplateId(supportedReportTemplates[0].id);
    }
  }, [selectedTemplateId, supportedReportTemplates]);

  useEffect(() => {
    if (!scheduleTemplateId && supportedReportTemplates.length > 0) {
      setScheduleTemplateId(supportedReportTemplates[0].id);
    }
  }, [scheduleTemplateId, supportedReportTemplates]);

  const trustArtifactEntries = useMemo(
    () =>
      TRUST_ARTIFACTS.map((artifact) => {
        const template = templates.find(
          (item) =>
            item.name === artifact.templateName || slugifyTemplateName(item.name) === artifact.templateKey
        );
        const latestReport = reports.find(
          (item) => getTemplateKeyFromReport(item) === artifact.templateKey
        );
        const latestReadyReport = reports.find(
          (item) =>
            getTemplateKeyFromReport(item) === artifact.templateKey &&
            normalizeStatus(item.status) === 'ready'
        );

        return {
          artifact,
          template,
          latestReport,
          latestReadyReport,
        };
      }),
    [reports, templates]
  );

  const trustArtifactEntryById = useMemo(
    () =>
      trustArtifactEntries.reduce<
        Record<
          string,
          {
            artifact: TrustArtifactDefinition;
            template?: ReportTemplate;
            latestReport?: Report;
            latestReadyReport?: Report;
          }
        >
      >((accumulator, entry) => {
        accumulator[entry.artifact.id] = entry;
        return accumulator;
      }, {}),
    [trustArtifactEntries]
  );

  const readyTrustArtifactEntries = useMemo(
    () => trustArtifactEntries.filter((entry) => entry.latestReadyReport),
    [trustArtifactEntries]
  );

  const templateById = useMemo(
    () =>
      templates.reduce<Record<string, ReportTemplate>>((accumulator, template) => {
        accumulator[template.id] = template;
        return accumulator;
      }, {}),
    [templates]
  );

  const canUseReport = (report?: Report | null) => {
    if (!report?.template_id) {
      return true;
    }
    const template = templateById[report.template_id];
    return template ? canUseTemplate(template, userRoles) : true;
  };

  const toggleFramework = (frameworkId: string) => {
    setSelectedFrameworkIds((current) =>
      current.includes(frameworkId)
        ? current.filter((item) => item !== frameworkId)
        : [...current, frameworkId]
    );
  };

  const toggleEvidencePackage = (packageId: string) => {
    setSelectedEvidencePackageIds((current) =>
      current.includes(packageId)
        ? current.filter((item) => item !== packageId)
        : [...current, packageId]
    );
  };

  const generateMutation = useMutation({
    mutationFn: ({ templateId, format }: { templateId: string; format: 'pdf' | 'csv' }) =>
      generateReport({
        template_id: templateId,
        format,
        date_range: dateRange.start && dateRange.end ? dateRange : undefined,
        framework_ids: selectedFrameworkIds,
        evidence_package_ids: selectedEvidencePackageIds,
        include_gaps: includeGaps,
        include_expired_evidence: includeExpiredEvidence,
        parameters: {
          evidence_basis: selectedEvidencePackageIds.length > 0 ? 'evidence_backed' : 'readiness_only',
        },
      }),
    onSuccess: (report) => {
      setLastGeneratedReport(report);
      toast.success('Export generation started. Refresh in a moment for the finished file.');
      queryClient.invalidateQueries({ queryKey: ['compliance-reports'] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to generate export');
    },
  });

  const createShareMutation = useMutation({
    mutationFn: ({ reportId, expiresInDays }: { reportId: string; expiresInDays: number }) =>
      createShare(reportId, { expires_in_days: expiresInDays }),
  });

  const deleteShareMutation = useMutation({
    mutationFn: ({ shareId }: { shareId: string }) => deleteShare(shareId),
  });

  const createScheduleMutation = useMutation({
    mutationFn: () => {
      const recipients = scheduleRecipients
        .split(',')
        .map((recipient) => recipient.trim())
        .filter(Boolean);
      return createScheduledReport(scheduleTemplateId, {
        frequency: scheduleFrequency,
        day: scheduleFrequency === 'daily' ? undefined : scheduleDay,
        time: scheduleTime,
        recipients,
        enabled: true,
      });
    },
    onSuccess: () => {
      toast.success('Report schedule created.');
      queryClient.invalidateQueries({ queryKey: ['compliance-report-schedules'] });
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to create report schedule');
    },
  });

  const shareQueries = useQueries({
    queries: readyTrustArtifactEntries.map((entry) => ({
      queryKey: ['report-shares', entry.latestReadyReport!.id],
      queryFn: () => listShares(entry.latestReadyReport!.id),
      enabled: Boolean(entry.latestReadyReport?.id),
    })),
  });

  const sharesByReportId = useMemo(() => {
    return readyTrustArtifactEntries.reduce<Record<string, Share[]>>((accumulator, entry, index) => {
      const reportId = entry.latestReadyReport?.id;
      if (reportId) {
        accumulator[reportId] = shareQueries[index]?.data || [];
      }
      return accumulator;
    }, {});
  }, [readyTrustArtifactEntries, shareQueries]);

  const handleGenerate = (templateId: string, format: 'pdf' | 'csv') => {
    if (selectedFrameworkIds.length === 0) {
      toast.error('Select at least one framework before generating a report.');
      return;
    }
    generateMutation.mutate({ templateId, format });
  };

  const handleGenerateSelectedTemplate = () => {
    if (!selectedTemplateId) {
      toast.error('Choose a report template.');
      return;
    }
    if (!selectedTemplateAllowed) {
      toast.error('Your role cannot generate this report template.');
      return;
    }
    handleGenerate(selectedTemplateId, selectedFormat);
  };

  const handleCreateSchedule = () => {
    const scheduleTemplate = supportedReportTemplates.find((template) => template.id === scheduleTemplateId);
    if (!scheduleTemplate) {
      toast.error('Choose a report template to schedule.');
      return;
    }
    if (!canUseTemplate(scheduleTemplate, userRoles)) {
      toast.error('Your role cannot schedule this report template.');
      return;
    }
    createScheduleMutation.mutate();
  };

  const handleCreateShare = async (reportId: string) => {
    try {
      const share = await createShareMutation.mutateAsync({ reportId, expiresInDays: 14 });
      await navigator.clipboard.writeText(share.share_url);
      queryClient.invalidateQueries({ queryKey: ['report-shares', reportId] });
      toast.success('14-day share link created and copied.');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to create share link');
    }
  };

  const handleCopyShare = async (shareUrl: string) => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      toast.success('Share link copied.');
    } catch {
      toast.error('Failed to copy share link');
    }
  };

  const handleDeleteShare = async (reportId: string, shareId: string) => {
    try {
      await deleteShareMutation.mutateAsync({ shareId });
      queryClient.invalidateQueries({ queryKey: ['report-shares', reportId] });
      toast.success('Share link revoked.');
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to revoke share link');
    }
  };

  const handleDownload = async (report: Report) => {
    if (!report.download_url) {
      toast.error('This export is not ready to download yet.');
      return;
    }

    const extension = report.format.toString().toLowerCase();
    const filename = `${(report.metadata?.template_key || report.name || 'sentinelgrid-export')
      .toString()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')}.${extension}`;
    try {
      const download = await getReportDownload(report.id);
      triggerDownload(download.download_url, filename);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Failed to prepare export download');
    }
  };

  const summary = coverage?.summary || {
    total_criteria: 0,
    open_criteria: 0,
    total_findings: 0,
    open_findings: 0,
    evidence_items: 0,
  };
  const reporting = coverage?.reporting_summary || {
    criteria_ready: 0,
    criteria_partial: 0,
    criteria_needing_attention: 0,
    key_detection_count: 0,
    control_check_count: 0,
    reportable_evidence_items: 0,
    top_detection_sources: [],
  };

  return (
    <PlanGate requiredTier="protect_defend_comply">
      <div className="p-6">
        <div className="flex justify-between items-center mb-6 gap-4 flex-wrap">
          <div>
            <h1 className="text-3xl font-bold text-text-main">{runtimeLabels.reportsTitle}</h1>
            <p className="mt-2 text-text-muted">
              {runtimeLabels.reportsDescription}
            </p>
          </div>
          <a
            href="#questionnaire-assist"
            className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-white hover:bg-primary/90"
          >
            Open questionnaire assist
          </a>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
            <p className="text-xs uppercase tracking-wide text-text-muted">Criteria ready</p>
            <p className="mt-2 text-3xl font-bold text-text-main">{reporting.criteria_ready}</p>
            <p className="text-xs text-text-muted">Directly usable in exports</p>
          </div>
          <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
            <p className="text-xs uppercase tracking-wide text-text-muted">Criteria with open work</p>
            <p className="mt-2 text-3xl font-bold text-text-main">{reporting.criteria_needing_attention}</p>
            <p className="text-xs text-text-muted">Need remediation context</p>
          </div>
          <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
            <p className="text-xs uppercase tracking-wide text-text-muted">Mapped detections</p>
            <p className="mt-2 text-3xl font-bold text-text-main">{reporting.key_detection_count}</p>
            <p className="text-xs text-text-muted">Signals supporting the control story</p>
          </div>
          <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
            <p className="text-xs uppercase tracking-wide text-text-muted">Control checks</p>
            <p className="mt-2 text-3xl font-bold text-text-main">{reporting.control_check_count}</p>
            <p className="text-xs text-text-muted">Identity and posture checks mapped</p>
          </div>
          <div className="rounded-lg border border-surface-card-border bg-surface-card p-5 shadow">
            <p className="text-xs uppercase tracking-wide text-text-muted">{runtimeLabels.evidenceMetricLabel}</p>
            <p className="mt-2 text-3xl font-bold text-text-main">{summary.evidence_items}</p>
            <p className="text-xs text-text-muted">{runtimeLabels.evidenceMetricDescription}</p>
          </div>
        </div>

        <div id="trust-center-kit" className="mb-6 rounded-lg border border-surface-card-border bg-surface-card p-6 shadow">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-xl font-semibold text-text-main">Trust Center Kit</h2>
              <p className="mt-1 text-sm text-text-muted">
                Generate customer-review artifacts, download the latest packet, and create expiring share links for prospects or customers.
              </p>
            </div>
            <Link
              href="/dashboard/compliance/reports/schedule"
              className="inline-flex items-center rounded-lg border border-border-faint bg-surface-hover px-4 py-2 text-text-main hover:bg-surface-input"
            >
              <CalendarIcon className="h-5 w-5 mr-2" />
              Schedule exports
            </Link>
          </div>

          <div className="mt-5 grid grid-cols-1 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.7fr)] gap-5">
            <div className="rounded-lg border border-border-faint bg-surface-hover p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-text-main">Generate report</h3>
                  <p className="mt-1 text-sm text-text-muted">
                    Select the framework scope and evidence package basis before generating an export.
                  </p>
                </div>
                <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  selectedEvidencePackageIds.length > 0
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    : 'border-amber-200 bg-amber-50 text-amber-700'
                }`}>
                  {selectedEvidenceBasis}
                </span>
              </div>

              <div className="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="report-template-select" className="mb-2 block text-sm font-medium text-text-main">
                    Template
                  </label>
                  <select
                    id="report-template-select"
                    value={selectedTemplateId}
                    onChange={(event) => setSelectedTemplateId(event.target.value)}
                    className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={templatesLoading}
                  >
                    <option value="">Select a report template</option>
                    {supportedReportTemplates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                  {!selectedTemplateAllowed && selectedTemplate ? (
                    <p className="mt-2 text-xs text-rose-600">
                      Requires role: {requiredRoleLabel(selectedTemplate)}
                    </p>
                  ) : null}
                </div>
                <div>
                  <label htmlFor="report-format-select" className="mb-2 block text-sm font-medium text-text-main">
                    Format
                  </label>
                  <select
                    id="report-format-select"
                    value={selectedFormat}
                    onChange={(event) => setSelectedFormat(event.target.value as 'pdf' | 'csv')}
                    className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="pdf">PDF</option>
                    <option value="csv">CSV</option>
                  </select>
                </div>
                <div>
                  <label htmlFor="export-start-date" className="mb-2 block text-sm font-medium text-text-main">
                    Start date
                  </label>
                  <input
                    id="export-start-date"
                    type="date"
                    value={dateRange.start}
                    onChange={(event) => setDateRange((current) => ({ ...current, start: event.target.value }))}
                    className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
                <div>
                  <label htmlFor="export-end-date" className="mb-2 block text-sm font-medium text-text-main">
                    End date
                  </label>
                  <input
                    id="export-end-date"
                    type="date"
                    value={dateRange.end}
                    onChange={(event) => setDateRange((current) => ({ ...current, end: event.target.value }))}
                    className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                  />
                </div>
              </div>

              <div className="mt-5">
                <p className="text-sm font-medium text-text-main">Frameworks</p>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                  {frameworkOptions.length > 0 ? (
                    frameworkOptions.map((framework) => (
                      <label
                        key={framework.framework_id}
                        className="flex items-start gap-3 rounded-lg border border-border-faint bg-surface-card px-3 py-3 text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={selectedFrameworkIds.includes(framework.framework_id)}
                          onChange={() => toggleFramework(framework.framework_id)}
                          className="mt-1 h-4 w-4 rounded border-border-faint text-primary focus:ring-primary"
                        />
                        <span>
                          <span className="block font-medium text-text-main">{framework.framework_name}</span>
                          <span className="block text-xs text-text-muted">
                            {framework.framework_code || framework.framework_id} - {framework.status.replace(/_/g, ' ')}
                          </span>
                        </span>
                      </label>
                    ))
                  ) : (
                    <p className="text-sm text-text-muted">Selected frameworks will appear after dashboard coverage loads.</p>
                  )}
                </div>
              </div>

              <div className="mt-5">
                <p className="text-sm font-medium text-text-main">Evidence packages</p>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2">
                  {evidencePackagesLoading ? (
                    <p className="text-sm text-text-muted">Loading evidence packages...</p>
                  ) : evidencePackages.length > 0 ? (
                    evidencePackages.slice(0, 6).map((evidencePackage) => (
                      <label
                        key={evidencePackage.id}
                        className="flex items-start gap-3 rounded-lg border border-border-faint bg-surface-card px-3 py-3 text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={selectedEvidencePackageIds.includes(evidencePackage.id)}
                          onChange={() => toggleEvidencePackage(evidencePackage.id)}
                          className="mt-1 h-4 w-4 rounded border-border-faint text-primary focus:ring-primary"
                        />
                        <span>
                          <span className="block font-medium text-text-main">{evidencePackage.package_name}</span>
                          <span className="block text-xs text-text-muted">
                            {evidencePackage.framework_id || 'all frameworks'} - {evidencePackage.review_status || evidencePackage.status || 'draft'}
                          </span>
                        </span>
                      </label>
                    ))
                  ) : (
                    <p className="text-sm text-text-muted">
                      No evidence packages found for the selected scope. Reports will be readiness-only until a package is selected.
                    </p>
                  )}
                </div>
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-4 text-sm text-text-muted">
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={includeGaps}
                      onChange={(event) => setIncludeGaps(event.target.checked)}
                      className="h-4 w-4 rounded border-border-faint text-primary focus:ring-primary"
                    />
                    Include control gaps
                  </label>
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={includeExpiredEvidence}
                      onChange={(event) => setIncludeExpiredEvidence(event.target.checked)}
                      className="h-4 w-4 rounded border-border-faint text-primary focus:ring-primary"
                    />
                    Include expired evidence
                  </label>
                </div>
                <button
                  type="button"
                  onClick={handleGenerateSelectedTemplate}
                  disabled={
                    generateMutation.isPending ||
                    !selectedTemplateId ||
                    !selectedTemplateAllowed ||
                    selectedFrameworkIds.length === 0
                  }
                  className="inline-flex items-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                >
                  {generateMutation.isPending ? (
                    <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <DocumentTextIcon className="mr-2 h-4 w-4" />
                  )}
                  Generate selected report
                </button>
              </div>

              {lastGeneratedReport ? (
                <div className="mt-5">
                  <ReportSnapshotDetails
                    report={lastGeneratedReport}
                    frameworks={frameworkOptions}
                    packages={evidencePackages}
                  />
                </div>
              ) : null}
            </div>

            <div className="rounded-lg border border-border-faint bg-surface-hover p-5">
              <div className="flex items-start gap-3">
                <CalendarIcon className="mt-0.5 h-6 w-6 text-primary" />
                <div>
                  <h3 className="text-lg font-semibold text-text-main">Schedule report</h3>
                  <p className="mt-1 text-sm text-text-muted">
                    Create a recurring job for supported compliance templates.
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-4">
                <div>
                  <label htmlFor="schedule-template-select" className="mb-2 block text-sm font-medium text-text-main">
                    Template
                  </label>
                  <select
                    id="schedule-template-select"
                    value={scheduleTemplateId}
                    onChange={(event) => setScheduleTemplateId(event.target.value)}
                    className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={templatesLoading}
                  >
                    <option value="">Select a report template</option>
                    {supportedReportTemplates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="schedule-frequency-select" className="mb-2 block text-sm font-medium text-text-main">
                      Frequency
                    </label>
                    <select
                      id="schedule-frequency-select"
                      value={scheduleFrequency}
                      onChange={(event) => setScheduleFrequency(event.target.value as ScheduleConfig['frequency'])}
                      className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="weekly">Weekly</option>
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="schedule-time-input" className="mb-2 block text-sm font-medium text-text-main">
                      Time UTC
                    </label>
                    <input
                      id="schedule-time-input"
                      type="time"
                      value={scheduleTime}
                      onChange={(event) => setScheduleTime(event.target.value)}
                      className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                </div>
                {scheduleFrequency !== 'daily' ? (
                  <div>
                    <label htmlFor="schedule-day-input" className="mb-2 block text-sm font-medium text-text-main">
                      {scheduleFrequency === 'weekly' ? 'Day of week' : 'Day of month'}
                    </label>
                    <input
                      id="schedule-day-input"
                      type="text"
                      value={scheduleDay}
                      onChange={(event) => setScheduleDay(event.target.value)}
                      className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                      placeholder={scheduleFrequency === 'weekly' ? 'monday' : '1'}
                    />
                  </div>
                ) : null}
                <div>
                  <label htmlFor="schedule-recipients-input" className="mb-2 block text-sm font-medium text-text-main">
                    Recipients
                  </label>
                  <input
                    id="schedule-recipients-input"
                    type="text"
                    value={scheduleRecipients}
                    onChange={(event) => setScheduleRecipients(event.target.value)}
                    className="w-full rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
                    placeholder="security@example.com, compliance@example.com"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleCreateSchedule}
                  disabled={createScheduleMutation.isPending || !scheduleTemplateId}
                  className="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                >
                  {createScheduleMutation.isPending ? (
                    <ArrowPathIcon className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <PlusCircleIcon className="mr-2 h-4 w-4" />
                  )}
                  Create schedule
                </button>
                <p className="text-xs text-text-muted">
                  {scheduledReports.length} active scheduled {scheduledReports.length === 1 ? 'report' : 'reports'}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6">
            {templatesLoading ? (
              <div className="rounded-lg border border-dashed border-border-faint p-6 text-sm text-text-muted">
                Loading trust artifacts...
              </div>
            ) : trustArtifactEntries.every((entry) => !entry.template) ? (
              <div className="rounded-lg border border-dashed border-border-faint p-6 text-sm text-text-muted">
                No trust-center artifacts are available yet.
              </div>
            ) : (
              <TrustArtifactCatalog
                artifacts={TRUST_ARTIFACTS}
                variant="light"
                actionRenderer={(artifact) => {
                  const entry = trustArtifactEntryById[artifact.id];
                  const template = entry?.template;
                  const latestReadyReport = entry?.latestReadyReport;
                  const latestReport = entry?.latestReport;
                  const activeShares = latestReadyReport ? sharesByReportId[latestReadyReport.id] || [] : [];
                  const templateAllowed = canUseTemplate(template, userRoles);
                  const latestReadyReportAllowed = canUseReport(latestReadyReport);

                  if (!template) {
                    return (
                      <div className="rounded-2xl border border-dashed border-border-faint p-4 text-sm text-text-muted">
                        This trust artifact template is not seeded yet.
                      </div>
                    );
                  }

                  return (
                    <div className="rounded-2xl border border-border-faint bg-surface-hover p-4">
                      <p className="text-xs uppercase tracking-wide text-text-muted">In-product actions</p>
                      <div className="mt-3 grid grid-cols-2 gap-2">
                        <button
                          onClick={() => handleGenerate(template.id, 'pdf')}
                          disabled={generateMutation.isPending || !templateAllowed || selectedFrameworkIds.length === 0}
                          className="inline-flex items-center justify-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                        >
                          <DocumentTextIcon className="mr-2 h-4 w-4" />
                          Generate PDF
                        </button>
                        <button
                          onClick={() => handleGenerate(template.id, 'csv')}
                          disabled={generateMutation.isPending || !templateAllowed || selectedFrameworkIds.length === 0}
                          className="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          <ArrowDownTrayIcon className="mr-2 h-4 w-4" />
                          Generate CSV
                        </button>
                      </div>
                      {!templateAllowed ? (
                        <p className="mt-2 text-xs text-rose-600">
                          Requires role: {requiredRoleLabel(template)}
                        </p>
                      ) : (
                        <p className="mt-2 text-xs text-text-muted">
                          Uses selected frameworks and {selectedEvidenceBasis.toLowerCase()} inputs.
                        </p>
                      )}

                      <div className="mt-4 rounded-xl border border-border-faint bg-surface-card p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs uppercase tracking-wide text-text-muted">Latest artifact</p>
                            <p className="mt-1 text-sm font-medium text-text-main">
                              {latestReadyReport
                                ? latestReadyReport.metadata?.template_name || latestReadyReport.name
                                : latestReport
                                ? `${latestReport.metadata?.template_name || latestReport.name} (${normalizeStatus(latestReport.status)})`
                                : 'No generated artifact yet'}
                            </p>
                          </div>
                          {latestReadyReport ? (
                            <button
                              onClick={() => handleDownload(latestReadyReport)}
                              disabled={!latestReadyReportAllowed}
                              className="inline-flex items-center rounded-lg border border-border-faint px-3 py-2 text-sm font-medium text-text-main hover:bg-surface-hover disabled:opacity-50"
                            >
                              <ArrowDownTrayIcon className="mr-2 h-4 w-4" />
                              Download artifact
                            </button>
                          ) : null}
                        </div>
                        <p className="mt-2 text-xs text-text-muted">
                          {latestReadyReport?.generated_at
                            ? `Last generated ${new Date(latestReadyReport.generated_at).toLocaleString()}`
                            : latestReport?.created_at
                            ? `Most recent run ${new Date(latestReport.created_at).toLocaleString()}`
                            : 'Generate an artifact to make it available for sharing.'}
                        </p>

                        {latestReadyReport ? (
                          <div className="mt-4">
                            <div className="flex items-center justify-between gap-3">
                              <div>
                                <p className="text-xs uppercase tracking-wide text-text-muted">Shareable links</p>
                                <p className="mt-1 text-xs text-text-muted">
                                  Create a 14-day trust-review link for this artifact.
                                </p>
                              </div>
                              <button
                                onClick={() => handleCreateShare(latestReadyReport.id)}
                                disabled={createShareMutation.isPending || !latestReadyReportAllowed}
                                className="inline-flex items-center rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-primary/90 disabled:opacity-50"
                              >
                                <LinkIcon className="mr-2 h-4 w-4" />
                                Create link
                              </button>
                            </div>

                            <div className="mt-3 space-y-2">
                              {activeShares.length > 0 ? (
                                activeShares.slice(0, 3).map((share) => (
                                  <div
                                    key={share.id}
                                    className="rounded-xl border border-border-faint bg-surface-hover px-3 py-3"
                                  >
                                    <div className="flex flex-wrap items-center justify-between gap-2">
                                      <div>
                                        <p className="text-sm font-medium text-text-main">
                                          Expires {formatShareDate(share.expires_at)}
                                        </p>
                                        <p className="text-xs text-text-muted">
                                          {share.access_count} accesses
                                          {share.password_protected ? ' • password protected' : ''}
                                        </p>
                                      </div>
                                      <div className="flex gap-2">
                                        <button
                                          onClick={() => handleCopyShare(share.share_url)}
                                          className="rounded-lg border border-border-faint px-3 py-1.5 text-xs font-medium text-text-main hover:bg-surface-card"
                                        >
                                          Copy link
                                        </button>
                                        <button
                                          onClick={() => handleDeleteShare(latestReadyReport.id, share.id)}
                                          disabled={deleteShareMutation.isPending}
                                          className="inline-flex items-center rounded-lg border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                                        >
                                          <TrashIcon className="mr-1 h-3.5 w-3.5" />
                                          Revoke
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <p className="text-xs text-text-muted">
                                  No active share links yet. Create one when a prospect or customer needs a packet.
                                </p>
                              )}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  );
                }}
              />
            )}
          </div>
        </div>

        <div className="mb-6 rounded-lg border border-surface-card-border bg-surface-card p-6 shadow">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <h2 className="text-xl font-semibold text-text-main">Report-ready coverage preview</h2>
              <p className="mt-1 text-sm text-text-muted">
                Use the same mapped detections and control checks that feed the audit export packs.
              </p>
            </div>
            <Link
              href="/dashboard/compliance"
              className="inline-flex items-center rounded-lg border border-border-faint bg-surface-hover px-4 py-2 text-text-main hover:bg-surface-input"
            >
              Open dashboard
            </Link>
          </div>

          {coverageLoading ? (
            <p className="mt-4 text-sm text-text-muted">Loading report-ready coverage…</p>
          ) : (
            <div className="mt-5 grid grid-cols-1 xl:grid-cols-2 gap-6">
              <div>
                <p className="text-xs uppercase tracking-wide text-text-muted">Priority criteria</p>
                <div className="mt-3 space-y-3">
                  {(coverage?.controls || []).slice(0, 4).map((control) => (
                    <div key={control.id} className="rounded-lg border border-border-faint px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-text-main">{control.id}</span>
                            <span className={`rounded-full border px-2 py-0.5 text-xs ${statusClasses(control.status)}`}>
                              {control.status.replace(/_/g, ' ')}
                            </span>
                          </div>
                          <p className="mt-2 text-sm text-text-main">{control.title}</p>
                        </div>
                        <div className="text-right text-xs text-text-muted">
                          <div>{control.open_findings} open findings</div>
                          <div>{control.evidence_items} evidence items</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs uppercase tracking-wide text-text-muted">Top detection sources</p>
                <div className="mt-3 space-y-3">
                  {(coverage?.reporting_summary.top_detection_sources || []).length > 0 ? (
                    coverage?.reporting_summary.top_detection_sources.map((item) => (
                      <div
                        key={item.source}
                        className="flex items-center justify-between rounded-lg border border-border-faint px-4 py-3"
                      >
                        <span className="text-sm text-text-main">{item.source}</span>
                        <span className="text-sm font-semibold text-text-main">{item.count}</span>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-text-muted">
                      Detection-source coverage will appear here once SOC 2 criteria have mapped active signals.
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        <QuestionnaireAssistPanel />
        <SecurityReviewResponseTemplatesPanel />

        <div className="rounded-lg border border-surface-card-border bg-surface-card p-6 shadow">
          <div className="flex items-center justify-between gap-4 flex-wrap mb-5">
            <div>
              <h2 className="text-xl font-semibold text-text-main">Generated exports</h2>
              <p className="mt-1 text-sm text-text-muted">
                Completed exports appear here with their generated format and reporting window.
              </p>
            </div>
            <select
              className="rounded-lg border border-border-faint bg-surface-input px-3 py-2 text-sm text-text-main focus:outline-none focus:ring-2 focus:ring-primary"
              value={selectedReportType}
              onChange={(event) =>
                setSelectedReportType(event.target.value as 'all' | 'compliance' | 'soc2')
              }
            >
              <option value="all">All report families</option>
              <option value="compliance">Compliance exports</option>
              <option value="soc2">SOC 2 exports</option>
            </select>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
            {reportsLoading ? (
              <div className="xl:col-span-3 py-12 text-center text-sm text-text-muted">
                Loading reports...
              </div>
            ) : reports.length === 0 ? (
              <div className="xl:col-span-3 text-center py-12">
                <DocumentTextIcon className="mx-auto mb-4 h-16 w-16 text-text-muted" />
                <p className="text-text-main">No exports generated yet</p>
                <p className="mt-2 text-sm text-text-muted">Start with one of the trust-center artifacts above.</p>
              </div>
            ) : (
              reports.map((report: Report) => {
                const title = report.metadata?.template_name || report.name || 'Compliance report';
                const normalizedStatus = normalizeStatus(report.status);
                const periodStart = report.date_range_start;
                const periodEnd = report.date_range_end;
                const formatLabel = report.format.toString().toUpperCase();
                const templateKey = getTemplateKeyFromReport(report);
                const isTrustArtifact = isTrustArtifactTemplateKey(templateKey);
                const reportInputs = getReportInputs(report);
                const reportSnapshot = getReportSnapshot(report);
                const reportActionAllowed = canUseReport(report);

                return (
                  <div
                    key={report.id}
                    className="rounded-lg border border-surface-card-border bg-surface-hover p-6 shadow transition-[border-color,box-shadow] hover:border-primary/30 hover:shadow-lg"
                  >
                    <div className="flex items-start justify-between mb-3 gap-3">
                      <DocumentTextIcon className="h-8 w-8 text-primary" />
                      <div className="flex items-center gap-2">
                        <span className="rounded-full border border-border-faint bg-surface-card px-2 py-1 text-xs text-text-muted">
                          {formatLabel}
                        </span>
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            normalizedStatus === 'ready'
                              ? 'bg-green-100 text-green-800'
                              : normalizedStatus === 'generating' || normalizedStatus === 'pending'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {normalizedStatus}
                        </span>
                      </div>
                    </div>

                    <h3 className="mb-2 text-lg font-semibold text-text-main">{title}</h3>
                    {report.metadata?.template_key && (
                      <div className="mb-3 flex flex-wrap items-center gap-2">
                        <p className="text-xs uppercase tracking-wide text-text-muted">
                          {report.metadata.template_key.replace(/_/g, ' ')}
                        </p>
                        {isTrustArtifact ? (
                          <span className="rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                            trust artifact
                          </span>
                        ) : null}
                        <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                          reportInputs.evidencePackageIds.length > 0
                            ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                            : 'border-amber-200 bg-amber-50 text-amber-700'
                        }`}>
                          {evidenceBasisLabel(reportInputs.evidencePackageIds)}
                        </span>
                      </div>
                    )}

                    <div className="mb-4 space-y-2 text-sm text-text-muted">
                      <p>
                        <span className="font-medium">Period:</span>{' '}
                        {periodStart ? new Date(periodStart).toLocaleDateString() : '—'} to{' '}
                        {periodEnd ? new Date(periodEnd).toLocaleDateString() : '—'}
                      </p>
                      <p>
                        <span className="font-medium">Generated:</span>{' '}
                        {report.generated_at ? new Date(report.generated_at).toLocaleString() : '—'}
                      </p>
                      {report.generated_by && report.generated_by !== 'system' && (
                        <p>
                          <span className="font-medium">By:</span> {report.generated_by}
                        </p>
                      )}
                      <p>
                        <span className="font-medium">Frameworks:</span>{' '}
                        {reportInputs.frameworkIds.length > 0
                          ? reportInputs.frameworkIds.map((id) => frameworkLabel(frameworkOptions, id)).join(', ')
                          : 'Not scoped'}
                      </p>
                      <p>
                        <span className="font-medium">Evidence packages:</span>{' '}
                        {reportInputs.evidencePackageIds.length > 0
                          ? reportInputs.evidencePackageIds.map((id) => packageLabel(evidencePackages, id)).join(', ')
                          : 'None'}
                      </p>
                      {reportSnapshot ? (
                        <p>
                          <span className="font-medium">Snapshot:</span>{' '}
                          {reportSnapshot.snapshot_hash_sha256
                            ? String(reportSnapshot.snapshot_hash_sha256).slice(0, 10)
                            : reportSnapshot.status || 'attached'}
                        </p>
                      ) : null}
                    </div>

                    {!reportActionAllowed ? (
                      <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-center text-sm text-rose-700">
                        Your role cannot export this report template.
                      </div>
                    ) : normalizedStatus === 'ready' && report.download_url ? (
                      <button
                        onClick={() => handleDownload(report)}
                        className="flex w-full items-center justify-center rounded-lg bg-primary px-3 py-2 text-sm text-white hover:bg-primary/90"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                        Download {formatLabel} export
                      </button>
                    ) : (
                      <div className="rounded-lg border border-dashed border-border-faint px-3 py-2 text-center text-sm text-text-muted">
                        {normalizedStatus === 'ready'
                          ? 'Download link unavailable'
                          : 'Export is still processing'}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </PlanGate>
  );
}
