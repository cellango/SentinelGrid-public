/**
 * Security Graph Page
 * Visual attack path analysis with contextual pivots from alerts, incidents, and entity views.
 */

'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import EmptyState from '@/components/ui/EmptyState';
import type { AttackPath, AttackPathEntity } from '@/components/security-graph';
import { getIncident } from '@/lib/api/incidents';
import { getAlert } from '@/lib/api/siem';
import {
  buildAttackPathsFromStory,
  buildEntityAttackPaths,
  findAttackPathSelection,
} from '@/lib/security/graph-context';

const SecurityGraph = dynamic(() => import('@/components/security-graph/SecurityGraph'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[600px] bg-surface-card rounded-lg border border-border-faint">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" role="status">
          <span className="sr-only">Loading graph...</span>
        </div>
        <p className="text-sm text-text-muted">Loading Security Graph...</p>
      </div>
    </div>
  ),
});

function coerceEntityType(value: string | null) {
  if (value === 'identity' || value === 'device' || value === 'resource' || value === 'ai_app') {
    return value;
  }
  return null;
}

export default function SecurityGraphPage() {
  const searchParams = useSearchParams();
  const alertId = searchParams.get('alert_id');
  const incidentId = searchParams.get('incident_id');
  const entityType = coerceEntityType(searchParams.get('entity_type'));
  const entityId = searchParams.get('entity_id');
  const entityLabel = searchParams.get('entity_label');
  const entityDomain = searchParams.get('entity_domain');
  const entityTitle = searchParams.get('title');
  const entitySummary = searchParams.get('summary');
  const severity = searchParams.get('severity');
  const entitlementsCount = searchParams.get('entitlements_count');
  const focusEntityId = searchParams.get('focus_entity_id');
  const focusEvidenceId = searchParams.get('focus_evidence_id');
  const sourceHrefParam = searchParams.get('source_href');
  const sourceLabelParam = searchParams.get('source_label');

  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [selectedEntity, setSelectedEntity] = useState<AttackPathEntity | null>(null);

  const {
    data: alert,
    isLoading: alertLoading,
    error: alertError,
  } = useQuery({
    queryKey: ['alert', alertId],
    queryFn: () => getAlert(alertId!),
    enabled: !!alertId,
    retry: 1,
  });

  const {
    data: incident,
    isLoading: incidentLoading,
    error: incidentError,
  } = useQuery({
    queryKey: ['incident', incidentId],
    queryFn: () => getIncident(incidentId!),
    enabled: !alertId && !!incidentId,
    retry: 1,
  });

  const graphContext = useMemo(() => {
    if (alert) {
      const paths = buildAttackPathsFromStory({
        title: alert.title,
        severity: alert.severity,
        summary: alert.description,
        domains: alert.story_domains,
        entities: alert.entities,
        evidence: alert.evidence,
      });
      return {
        title: 'Security Graph',
        subtitle: `Graph view for alert ${alert.id} and its linked story context.`,
        badge: `${paths.length} contextual path${paths.length === 1 ? '' : 's'}`,
        paths,
        sourceHref: `/dashboard/alerts/${alert.id}`,
        sourceLabel: sourceLabelParam || 'Back to alert',
      };
    }

    if (incident) {
      const paths = buildAttackPathsFromStory({
        title: incident.title,
        severity: incident.severity,
        summary: incident.description,
        domains: incident.story_domains,
        entities: incident.entities,
        evidence: incident.evidence,
      });
      return {
        title: 'Security Graph',
        subtitle: `Graph view for incident ${incident.id} and the cross-domain story tied to it.`,
        badge: `${paths.length} contextual path${paths.length === 1 ? '' : 's'}`,
        paths,
        sourceHref: `/dashboard/incidents/${incident.id}`,
        sourceLabel: sourceLabelParam || 'Back to incident',
      };
    }

    if (entityType && entityId && entityLabel) {
      const paths = buildEntityAttackPaths({
        entityType,
        entityId,
        entityLabel,
        entityDomain: entityDomain || undefined,
        title: entityTitle || `${entityLabel} graph`,
        severity,
        summary: entitySummary,
        entitlementsCount: entitlementsCount ? Number(entitlementsCount) : undefined,
      });
      return {
        title: 'Security Graph',
        subtitle: `Graph view for ${entityLabel}. Open it from an alert, incident, or IAM surface to keep the original story context.`,
        badge: paths.length > 0 ? 'Focused entity path' : 'Context required',
        paths,
        sourceHref: sourceHrefParam,
        sourceLabel: sourceLabelParam || 'Back to source',
      };
    }

    return {
      title: 'Security Graph',
      subtitle: 'Launch Security Graph from an alert, incident, or normalized entity to render real story context.',
      badge: 'Context required',
      paths: [] as AttackPath[],
      sourceHref: null,
      sourceLabel: null,
    };
  }, [
    alert,
    entitlementsCount,
    entityDomain,
    entityId,
    entityLabel,
    entitySummary,
    entityTitle,
    entityType,
    incident,
    severity,
    sourceHrefParam,
    sourceLabelParam,
  ]);

  useEffect(() => {
    setSelectedPathId(graphContext.paths[0]?.id || null);
  }, [graphContext.paths]);

  useEffect(() => {
    const selection = findAttackPathSelection(graphContext.paths, {
      entityId: focusEntityId || entityId,
      evidenceId: focusEvidenceId,
    });
    if (selection?.pathId) {
      setSelectedPathId(selection.pathId);
    }
    setSelectedEntity(selection?.entity || null);
  }, [entityId, focusEntityId, focusEvidenceId, graphContext.paths]);

  const loading = alertLoading || incidentLoading;
  const errorMessage =
    (alertError as Error | null)?.message || (incidentError as Error | null)?.message || null;
  const hasGraphContext = graphContext.paths.length > 0;
  const isStoryLaunch = Boolean(alert || incident || (entityType && entityId && entityLabel));
  const emptyStateTitle = isStoryLaunch
    ? 'No contextual graph is ready yet'
    : 'Open a story to build the graph';
  const emptyStateDescription = isStoryLaunch
    ? 'This story does not have enough normalized entities or linked evidence yet to render a cross-domain graph.'
    : 'Security Graph no longer ships seeded demo paths. Open it from an alert, incident, or entity pivot once real story context exists.';

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      <div className="px-6 py-4 border-b border-border-faint">
        <Breadcrumbs />
        <div className="mt-2 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-xl font-bold text-text-main">{graphContext.title}</h1>
            <p className="text-sm text-text-muted mt-0.5">{graphContext.subtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-text-muted bg-surface-card border border-border-faint rounded-lg px-3 py-1.5">
              {graphContext.badge}
            </span>
            {graphContext.sourceHref && (
              <Link
                href={graphContext.sourceHref}
                className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-primary/30 px-3 py-2 text-sm text-text-main hover:border-primary/50"
              >
                {graphContext.sourceLabel}
              </Link>
            )}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex-1 p-6">
          <div className="flex h-full items-center justify-center rounded-lg border border-border-faint bg-surface-card">
            <div className="flex flex-col items-center gap-3">
              <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <p className="text-sm text-text-muted">Building graph context...</p>
            </div>
          </div>
        </div>
      ) : errorMessage ? (
        <div className="flex-1 p-6">
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
            Failed to load contextual graph data. {errorMessage}
          </div>
        </div>
      ) : hasGraphContext ? (
        <div className="flex-1 overflow-hidden">
          <SecurityGraph
            paths={graphContext.paths}
            selectedPathId={selectedPathId}
            onSelectPath={setSelectedPathId}
            onNodeClick={setSelectedEntity}
          />
        </div>
      ) : (
        <div className="flex-1 p-6">
          <div className="flex h-full items-center justify-center rounded-lg border border-border-faint bg-surface-card">
            <div className="w-full max-w-2xl p-6">
              <EmptyState
                variant="no-data"
                title={emptyStateTitle}
                description={emptyStateDescription}
              />
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                {graphContext.sourceHref ? (
                  <Link
                    href={graphContext.sourceHref}
                    className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-950 transition hover:brightness-110"
                  >
                    {graphContext.sourceLabel || 'Back to source'}
                  </Link>
                ) : (
                  <>
                    <Link
                      href="/dashboard/alerts"
                      className="inline-flex min-h-[44px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-slate-950 transition hover:brightness-110"
                    >
                      Open alert queue
                    </Link>
                    <Link
                      href="/dashboard/incidents"
                      className="inline-flex min-h-[44px] items-center justify-center rounded-lg border border-border-faint px-4 py-2 text-sm font-medium text-text-main transition hover:border-primary/40"
                    >
                      Open incident queue
                    </Link>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {selectedEntity && hasGraphContext && (
        <div className="absolute right-0 top-0 bottom-0 w-80 bg-surface-card border-l border-border-faint p-4 overflow-y-auto z-20 shadow-2xl">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-main text-sm">Entity Details</h3>
            <button
              onClick={() => setSelectedEntity(null)}
              className="p-1.5 rounded-lg hover:bg-surface-hover text-text-muted min-h-[44px] min-w-[44px] flex items-center justify-center"
              aria-label="Close details"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-text-muted text-xs">Type</dt>
              <dd className="text-text-main font-medium capitalize">{selectedEntity.type.replace('_', ' ')}</dd>
            </div>
            <div>
              <dt className="text-text-muted text-xs">Name</dt>
              <dd className="text-text-main font-medium">{selectedEntity.label}</dd>
            </div>
            {selectedEntity.severity && (
              <div>
                <dt className="text-text-muted text-xs">Severity</dt>
                <dd className="text-text-main font-medium capitalize">{selectedEntity.severity}</dd>
              </div>
            )}
            {selectedEntity.domain && (
              <div>
                <dt className="text-text-muted text-xs">Domain</dt>
                <dd className="text-text-main font-medium capitalize">{selectedEntity.domain}</dd>
              </div>
            )}
            {selectedEntity.status && (
              <div>
                <dt className="text-text-muted text-xs">Status</dt>
                <dd className="text-text-main font-medium capitalize">{selectedEntity.status}</dd>
              </div>
            )}
            {selectedEntity.metadata && Object.keys(selectedEntity.metadata).length > 0 && (
              <div>
                <dt className="text-text-muted text-xs">Metadata</dt>
                <dd className="mt-1 rounded-lg bg-surface-hover p-3 text-xs text-text-main">
                  <pre className="whitespace-pre-wrap break-words">
                    {JSON.stringify(selectedEntity.metadata, null, 2)}
                  </pre>
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}
