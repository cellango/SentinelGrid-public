'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { clsx } from 'clsx';
import { accessRequestsApi, type AccessRequest } from '@/lib/api/accessRequests';
import { certificateApi, type Certificate } from '@/lib/api/certificates';
import { getDetectionRule } from '@/lib/api/detection-rules';
import { campaignsApi, type Campaign } from '@/lib/api/governance';
import { getApp, type App } from '@/lib/api/iam-portal';
import { getIncident, type Incident } from '@/lib/api/incidents';
import { getPhishingReport, type PhishingReport } from '@/lib/api/phishing';
import { playbooksApi, type Playbook } from '@/lib/api/playbooks';
import { getScan, type ScanDetail } from '@/lib/api/scans';
import { getAlert, type Alert } from '@/lib/api/siem';
import { getTicket, type Ticket } from '@/lib/api/tickets';

interface BreadcrumbOverride {
  /** Path segment to match (e.g. 'iam') */
  segment: string;
  /** Display label */
  label: string;
}

interface BreadcrumbsProps {
  /** Optional overrides for path segment labels */
  overrides?: BreadcrumbOverride[];
  className?: string;
}

interface EntityBreadcrumbResolver {
  targetIndex: number;
  queryKey: readonly unknown[];
  queryFn: () => Promise<string | null>;
  disableLink?: boolean;
}

const defaultOverrides: BreadcrumbOverride[] = [
  { segment: 'dashboard', label: 'Now' },
  { segment: 'iam', label: 'Identity Operations' },
  { segment: 'siem', label: 'Detection Coverage' },
  { segment: 'alerts', label: 'Alerts' },
  { segment: 'incidents', label: 'Incidents' },
  { segment: 'compliance', label: 'Prove & Report' },
  { segment: 'playbooks', label: 'Response Playbooks' },
  { segment: 'scans', label: 'Scans' },
  { segment: 'tickets', label: 'Tickets' },
  { segment: 'people', label: 'People & Access' },
  { segment: 'privileged-access', label: 'Privileged Access' },
  { segment: 'access-reviews', label: 'Access Reviews' },
  { segment: 'security-events', label: 'Identity Events' },
  { segment: 'log-management', label: 'Telemetry Search' },
  { segment: 'detection-rules', label: 'Detection Coverage' },
  { segment: 'penetration-testing', label: 'Pen Tests' },
  { segment: 'reports', label: 'Reports' },
  { segment: 'settings', label: 'Settings' },
  { segment: 'welcome', label: 'Welcome' },
  { segment: 'posture', label: 'Cloud Posture' },
  { segment: 'ai-activity', label: 'AI Activity' },
  { segment: 'ai-security', label: 'AI Operations' },
  { segment: 'api-keys', label: 'API Keys' },
  { segment: 'certificates', label: 'Certificates' },
  { segment: 'secrets', label: 'Secrets' },
  { segment: 'devices', label: 'Devices' },
  { segment: 'policies', label: 'Policies' },
  { segment: 'my-account', label: 'My Account' },
  { segment: 'my-access', label: 'My Access' },
  { segment: 'apps', label: 'Apps & Profiles' },
  { segment: 'builder', label: 'Builder' },
  { segment: 'health', label: 'Health' },
  { segment: 'edit', label: 'Edit' },
  { segment: 'executions', label: 'Executions' },
  { segment: 'triggers', label: 'Triggers' },
  { segment: 'new', label: 'New' },
  { segment: 'operations', label: 'Platform Ops' },
  { segment: 'partner', label: 'Partner Console' },
  { segment: 'ai-governance', label: 'AI Governance' },
  { segment: 'analyst', label: 'Analyst' },
  { segment: 'executive', label: 'Executive' },
  { segment: 'coverage', label: 'Coverage' },
];

function getLabel(segment: string, overrides: BreadcrumbOverride[]): string {
  const override = overrides.find((o) => o.segment === segment);
  if (override) return override.label;
  // Default: capitalize and replace dashes
  return segment
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

/** Returns true if segment looks like a UUID or dynamic ID */
function isDynamicSegment(segment: string): boolean {
  return /^[0-9a-f-]{8,}$/i.test(segment) || /^\d+$/.test(segment);
}

function humanizeToken(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function truncateLabel(value: string, maxLength: number = 72): string {
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function joinTitleParts(...parts: Array<string | undefined | null>): string | null {
  const filtered = parts
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part));
  if (filtered.length === 0) return null;
  return truncateLabel(filtered.join(': '));
}

function formatAlertLabel(alert: Alert): string {
  return joinTitleParts(alert.external_id, alert.title, alert.id) || 'Alert details';
}

function formatIncidentLabel(incident: Incident): string {
  return joinTitleParts(incident.external_id, incident.title, incident.id) || 'Incident details';
}

function formatTicketLabel(ticket: Ticket): string {
  return joinTitleParts(ticket.external_id, ticket.title, ticket.id) || 'Ticket details';
}

function formatRequestLabel(request: AccessRequest): string {
  const action = humanizeToken(request.action || 'access');
  const resourceType = humanizeToken(request.resource_type || 'resource');
  const target = request.resource_id || request.id;
  return truncateLabel(`${action} ${resourceType} · ${target}`);
}

function formatScanLabel(scan: ScanDetail): string {
  const scanType = humanizeToken(scan.scan_type || scan.summary?.type || 'scan');
  const target = scan.target_ref || scan.summary?.target_url || scan.summary?.repo || scan.id;
  return truncateLabel(`${scanType} · ${target}`);
}

function formatCampaignLabel(campaign: Campaign): string {
  return truncateLabel(campaign.name || campaign.id);
}

function formatPhishingLabel(report: PhishingReport): string {
  return truncateLabel(report.subject || report.from_address || report.id);
}

function formatPlaybookLabel(playbook: Playbook): string {
  return truncateLabel(playbook.name || playbook.id);
}

function formatDetectionRuleLabel(rule: { id: string; rule_key?: string; name?: string }): string {
  return (
    joinTitleParts(rule.rule_key, rule.name, rule.id) ||
    truncateLabel(rule.name || rule.id || 'Detection rule')
  );
}

function formatAppLabel(app: App): string {
  return truncateLabel(app.display_name || app.name || app.id);
}

function formatCertificateLabel(certificate: Certificate): string {
  return truncateLabel(certificate.common_name || certificate.id);
}

function getEntityResolver(
  segments: string[],
  tenantId: string | null
): EntityBreadcrumbResolver | null {
  if (segments[0] !== 'dashboard') {
    return null;
  }

  if (segments[1] === 'alerts' && segments[2]) {
    const alertId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['alert', alertId],
      queryFn: async () => formatAlertLabel(await getAlert(alertId)),
    };
  }

  if (segments[1] === 'incidents' && segments[2]) {
    const incidentId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['incident', incidentId],
      queryFn: async () => formatIncidentLabel(await getIncident(incidentId)),
    };
  }

  if (segments[1] === 'tickets' && segments[2] && tenantId) {
    const ticketId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['ticket', ticketId, tenantId],
      queryFn: async () => formatTicketLabel(await getTicket(ticketId, tenantId)),
    };
  }

  if (segments[1] === 'requests' && segments[2]) {
    const requestId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['access-requests', 'detail', requestId],
      queryFn: async () => formatRequestLabel(await accessRequestsApi.get(requestId)),
    };
  }

  if (segments[1] === 'scans' && segments[2]) {
    const scanId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['scan', scanId],
      queryFn: async () => formatScanLabel(await getScan(scanId)),
    };
  }

  if (segments[1] === 'campaigns' && segments[2]) {
    const campaignId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['campaigns', 'detail', campaignId],
      queryFn: async () => formatCampaignLabel(await campaignsApi.get(campaignId)),
    };
  }

  if (segments[1] === 'phishing' && segments[2] && tenantId) {
    const reportId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['phishingReport', reportId, tenantId],
      queryFn: async () => formatPhishingLabel(await getPhishingReport(reportId, tenantId)),
    };
  }

  if (segments[1] === 'playbooks' && segments[2]) {
    const playbookId = segments[2];
    return {
      targetIndex: 2,
      queryKey: ['playbook', playbookId],
      queryFn: async () => formatPlaybookLabel(await playbooksApi.get(playbookId)),
      disableLink: true,
    };
  }

  if (segments[1] === 'iam' && segments[2] === 'apps' && segments[3]) {
    const appId = segments[3];
    return {
      targetIndex: 3,
      queryKey: ['iam-app', appId],
      queryFn: async () => formatAppLabel(await getApp(appId)),
      disableLink: true,
    };
  }

  if (segments[1] === 'iam' && segments[2] === 'certificates' && segments[3]) {
    const certificateId = segments[3];
    return {
      targetIndex: 3,
      queryKey: ['certificate', certificateId],
      queryFn: async () => {
        const response = await certificateApi.getCertificate(certificateId);
        return formatCertificateLabel(response.data);
      },
    };
  }

  if (segments[1] === 'siem' && segments[2] === 'detection-rules' && segments[3]) {
    const ruleId = segments[3];
    return {
      targetIndex: 3,
      queryKey: ['detection-rule', ruleId],
      queryFn: async () => formatDetectionRuleLabel(await getDetectionRule(ruleId)),
    };
  }

  return null;
}

export default function Breadcrumbs({ overrides = [], className }: BreadcrumbsProps) {
  const pathname = usePathname();
  const [tenantId, setTenantId] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setTenantId(localStorage.getItem('tenant_id'));
    }
  }, []);

  const allOverrides = [...overrides, ...defaultOverrides];
  const safePathname = pathname ?? '';
  const segments = useMemo(() => safePathname.split('/').filter(Boolean), [safePathname]);
  const entityResolver = useMemo(
    () => getEntityResolver(segments, tenantId),
    [segments, tenantId]
  );
  const { data: entityLabel } = useQuery({
    queryKey: entityResolver?.queryKey ?? ['breadcrumbs', safePathname],
    queryFn: entityResolver?.queryFn ?? (async () => null),
    enabled: Boolean(entityResolver),
    staleTime: 60_000,
    retry: 1,
  });

  if (!pathname) return null;

  // Don't show breadcrumbs for root dashboard
  if (segments.length <= 1) return null;

  const crumbs = segments.map((segment, index) => {
    const href = '/' + segments.slice(0, index + 1).join('/');
    const isLast = index === segments.length - 1;
    const isResolvedEntity = index === entityResolver?.targetIndex;
    const isDynamic = isDynamicSegment(segment);
    const label = isResolvedEntity
      ? entityLabel || 'Details'
      : isDynamic
        ? 'Details'
        : getLabel(segment, allOverrides);

    return {
      href,
      isLast,
      isLinkable: !isLast && !(isResolvedEntity && entityResolver?.disableLink),
      label,
    };
  });

  return (
    <nav aria-label="Breadcrumb" className={clsx('mb-4', className)}>
      <ol className="flex items-center gap-1.5 text-sm text-text-muted flex-wrap">
        {crumbs.map((crumb, i) => (
          <li key={crumb.href} className="flex items-center gap-1.5">
            {i > 0 && (
              <svg className="w-3.5 h-3.5 text-text-muted/50 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            )}
            {crumb.isLast ? (
              <span className="text-text-main font-medium" aria-current="page">
                {crumb.label}
              </span>
            ) : !crumb.isLinkable ? (
              <span className="text-text-muted">
                {crumb.label}
              </span>
            ) : (
              <Link
                href={crumb.href}
                className="hover:text-primary transition-colors"
              >
                {crumb.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}
