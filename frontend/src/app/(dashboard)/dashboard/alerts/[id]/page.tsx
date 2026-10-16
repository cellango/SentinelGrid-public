/**
 * Alert Detail Page
 * View detailed information about a specific security alert
 */

'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { getAlert, getAlertStreamUrl, updateAlertStatus, updateAlert, getEntityTimeline, type Alert, getSourceHealth, type SourceHealth } from '@/lib/api/siem';
import { describePlaybookExecution, playbooksApi } from '@/lib/api/playbooks';
import { getAlertAudit } from '@/lib/api/audit';
import { useState, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Breadcrumbs from '@/components/ui/Breadcrumbs';
import HealthBadge from '@/components/ui/HealthBadge';
import AITransparencyPanel from '@/components/ai/AITransparencyPanel';
import StoryContextPanel from '@/components/operator/StoryContextPanel';
import CrossDomainRelationshipView from '@/components/operator/CrossDomainRelationshipView';
import IssueOwnershipSlaPanel from '@/components/operator/IssueOwnershipSlaPanel';
import ResponsePackPanel from '@/components/operator/ResponsePackPanel';
import { matchResponsePacksForAlert } from '@/lib/playbooks/responsePacks';
import { buildAlertGraphHref } from '@/lib/security/graph-context';
import { useAuth } from '@/lib/providers/AuthProvider';
import { recordAIFeedback } from '@/lib/api/ai-feedback';
import { useEventSourceStream } from '@/lib/realtime/useEventSourceStream';

export default function AlertDetailPage() {
  const params = useParams();
  const alertId = params.id as string;
  const { tenantId, user } = useAuth();
  const [showPlaybookConfirm, setShowPlaybookConfirm] = useState(false);
  const queryClient = useQueryClient();

  const alertStream = useEventSourceStream<Alert>({
    url: alertId ? getAlertStreamUrl(alertId) : null,
    enabled: !!alertId,
    onSnapshot: (payload) => {
      queryClient.setQueryData(['alert', alertId], payload);
      queryClient.invalidateQueries({ queryKey: ['alert-timeline', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alert-audit', alertId] });
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const { data: sourceHealth } = useQuery<SourceHealth>({
    queryKey: ['source-health'],
    queryFn: getSourceHealth,
    retry: 1,
    staleTime: 30000,
  });

  const { data: alert, isLoading, error } = useQuery({
    queryKey: ['alert', alertId],
    queryFn: () => getAlert(alertId),
    enabled: !!alertId,
    refetchInterval:
      alertStream.status === 'error' || alertStream.status === 'unsupported'
        ? 60 * 1000
        : false,
  });
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [playbookStatus, setPlaybookStatus] = useState<string | null>(null);

  const related = useMemo(() => {
    if (!alert) {
      return { incidents: [], detections: [], evidence: [] as any[], comments: [] as any[] };
    }
    const rp = (alert as any).raw_payload || {};
    const incidents = (alert.evidence || []).filter((item) => item.type === 'incident');
    const detections = (alert.evidence || []).filter((item) => item.type === 'alert');
    const evidence = (alert.evidence || []).filter((item) => item.type !== 'incident' && item.type !== 'alert');
    const comments = rp.comments || [];
    return { incidents, detections, evidence, comments };
  }, [alert]);

  const alternatePlaybooks = useMemo(() => {
    if (!alert) return [];
    const rp = (alert as any).raw_payload || {};
    const alts = rp.alternate_playbooks || rp.recommended_playbooks || [];
    if (!Array.isArray(alts)) return [];
    return alts.map((p: any) => ({
      id: p?.id || p,
      name: p?.name || p?.key || String(p),
      rationale: p?.rationale,
    }));
  }, [alert]);

  const aiAnalyses = useMemo(() => {
    const analyses = (alert as any)?.ai_analyses;
    return Array.isArray(analyses) ? analyses : [];
  }, [alert]);

  const latestAiAnalysis = aiAnalyses.length > 0 ? aiAnalyses[aiAnalyses.length - 1] : null;

  const recommendationWhy = useMemo(() => {
    const reasons: string[] = [];
    const recommendationRationale = (alert as any)?.playbook_rationale;
    if (typeof recommendationRationale === 'string' && recommendationRationale.trim()) {
      reasons.push(recommendationRationale.trim());
    }
    if (
      latestAiAnalysis?.rationale &&
      typeof latestAiAnalysis.rationale === 'string' &&
      latestAiAnalysis.rationale.trim() &&
      !reasons.includes(latestAiAnalysis.rationale.trim())
    ) {
      reasons.push(latestAiAnalysis.rationale.trim());
    }
    return reasons;
  }, [alert, latestAiAnalysis]);

  const entityContext = useMemo(() => {
    if (!alert) return null;
    const canonicalEntity = (alert.entities || []).find((entity) => entity.type === 'identity' || entity.type === 'device');
    if (canonicalEntity?.type === 'identity') {
      return { type: 'user' as const, id: canonicalEntity.id };
    }
    if (canonicalEntity?.type === 'device') {
      return { type: 'host' as const, id: canonicalEntity.id };
    }
    const rp = (alert as any).raw_payload || {};
    const userId =
      alert.user_identifier ||
      (alert as any).user_id ||
      rp.user_identifier ||
      rp.user_id ||
      rp.user?.id ||
      rp.user?.email;
    const assetId =
      alert.asset_id ||
      rp.asset_id ||
      rp.host?.id ||
      rp.host?.hostname ||
      rp.host?.name;
    if (userId) {
      return { type: 'user' as const, id: userId };
    }
    if (assetId) {
      return { type: 'host' as const, id: assetId };
    }
    return null;
  }, [alert]);

  const { data: timeline } = useQuery({
    queryKey: ['alert-timeline', alertId, entityContext?.id],
    queryFn: () =>
      entityContext
        ? getEntityTimeline({
            entity_type: entityContext.type,
            entity_id: entityContext.id,
            limit: 200,
          })
        : Promise.resolve(null),
    enabled: !!entityContext?.id,
  });

  const { data: auditEvents } = useQuery({
    queryKey: ['alert-audit', alertId],
    queryFn: () => getAlertAudit(alertId),
  });

  const auditEntries = useMemo(() => {
    const entries: Array<{ ts?: string; text: string; kind: 'comment' | 'event' }> = [];
    related.comments.forEach((c: any) => {
      entries.push({
        ts: c.at || c.timestamp,
        text: c.text || c.comment || 'Comment added',
        kind: 'comment',
      });
    });
    (auditEvents || []).forEach((e: any) => {
      entries.push({ ts: e.ts, text: e.text, kind: 'event' });
    });
    if (timeline?.events) {
      timeline.events.slice(0, 20).forEach((evt: any) => {
        entries.push({
          ts: evt.timestamp,
          text: `${evt.event_type || 'event'}${evt.action ? ` • ${evt.action}` : ''}${evt.source?.ip ? ` • ${evt.source.ip}` : ''}`,
          kind: 'event',
        });
      });
    }
    return entries.sort((a, b) => (a.ts || '').localeCompare(b.ts || ''));
  }, [related.comments, timeline, auditEvents]);

  const statusMutation = useMutation({
    mutationFn: (status: Alert['status']) => updateAlertStatus(alertId, status),
    onSuccess: (data) => {
      queryClient.setQueryData(['alert', alertId], data);
      setActionMessage(`Status updated to ${data.status}`);
    },
  });

  const assignMutation = useMutation({
    mutationFn: (assigned_to: string) => updateAlert(alertId, { assigned_to }),
    onSuccess: (data) => {
      queryClient.setQueryData(['alert', alertId], data);
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const handleAssignmentUpdate = async (assignedTo: string) => {
    await assignMutation.mutateAsync(assignedTo);
    setActionMessage(`Assigned alert to ${assignedTo}`);
  };

  const dueDateMutation = useMutation({
    mutationFn: (due_date: string | null) => updateAlert(alertId, { due_date: due_date || undefined }),
    onSuccess: (data) => {
      queryClient.setQueryData(['alert', alertId], data);
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  const handleDueDateUpdate = async (dueDate: string | null) => {
    await dueDateMutation.mutateAsync(dueDate);
    setActionMessage(`Alert SLA target ${dueDate ? 'updated' : 'cleared'}.`);
  };

  const { data: playbooks } = useQuery({
    queryKey: ['playbooks-all'],
    queryFn: () => playbooksApi.list(),
  });

  const detectionVersion = () =>
    (alert as any)?.detection_rule_version_id ||
    (alert as any)?.raw_payload?.detection_rule_version_id ||
    (alert as any)?.raw_payload?.sg?.detection_rule_version_id;

  const playbookVersion = () =>
    (alert as any)?.playbook_version_id ||
    (alert as any)?.raw_payload?.playbook_version_id ||
    (alert as any)?.raw_payload?.sg?.playbook_version_id;

  const playbookId = () =>
    (alert as any)?.recommended_playbook_id ||
    (alert as any)?.recommended_playbook ||
    (alert as any)?.raw_payload?.playbook_id;

  const matchedPlaybookId = useMemo(() => {
    if (!alert || !playbooks) return null;
    const token =
      alert.recommended_playbook_id ||
      alert.recommended_playbook ||
      alert.recommended_playbook_key;
    if (!token) return null;
    const lower = token.toLowerCase();
    // Direct ID match
    const byId = playbooks.find((p) => p.id === token);
    if (byId) return byId.id;
    // Match by key or name
    const byKey = playbooks.find(
      (p) =>
        (p as any).key?.toLowerCase?.() === lower ||
        p.name.toLowerCase() === lower
    );
    return byKey?.id || null;
  }, [alert, playbooks]);

  const matchedResponsePacks = useMemo(() => {
    if (!alert) return [];
    return matchResponsePacksForAlert(alert, playbooks || []);
  }, [alert, playbooks]);

  const runPlaybookMutation = useMutation({
    mutationFn: async (playbookId: string) => {
      if (!alert) {
        throw new Error('Alert not loaded');
      }
      setPlaybookStatus('Recording execution request...');
      const resp = await playbooksApi.execute(playbookId, 'alert', alert.id, { alert_id: alert.id });
      if (resp.execution_id && resp.workflow_exec_id) {
        // Optimistic polling for status
        setTimeout(async () => {
          const status = await playbooksApi.getExecution(resp.execution_id);
          if (status?.status) {
            setPlaybookStatus(`Execution ${status.status}`);
          }
        }, 2000);
      }
      return resp;
    },
    onSuccess: (resp) => {
      setActionMessage(`${describePlaybookExecution(resp)} Execution ${resp.execution_id || 'pending'}.`);
      setPlaybookStatus(resp.status ? `Execution ${resp.status}` : 'Execution request recorded');
    },
    onError: (err: any) => {
      setActionMessage(err?.message || 'Failed to record playbook execution request');
      setPlaybookStatus(null);
    },
    onSettled: () => {
      setShowPlaybookConfirm(false);
    }
  });

  const handleRunPlaybook = (playbookId: string, messagePrefix = 'Playbook') => {
    runPlaybookMutation.mutate(playbookId, {
      onSuccess: (resp) => {
        setActionMessage(`${messagePrefix}: ${describePlaybookExecution(resp)}`);
      },
    });
  };

  const submitAlertAIFeedback = async (
    action: 'ai_classification_disagreed' | 'ai_recommendation_disagreed',
    metadata: Record<string, unknown>
  ) => {
    if (!alert || !tenantId) {
      throw new Error('Alert context is unavailable for AI feedback.');
    }

    await recordAIFeedback({
      tenantId,
      actorUserId: user?.id,
      actorEmail: user?.email,
      actorRoles: user?.roles,
      action,
      resourceType: 'alert',
      resourceId: alert.id,
      resourceName: alert.title,
      metadata: {
        alert_status: alert.status,
        alert_severity: alert.severity,
        detection_rule_id: alert.detection_rule_id || null,
        recommended_playbook:
          alert.recommended_playbook_id ||
          alert.recommended_playbook ||
          alert.recommended_playbook_key ||
          null,
        ...metadata,
      },
    });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-bg-alt rounded w-1/3 mb-4"></div>
          <div className="h-24 bg-bg-alt rounded mb-4"></div>
          <div className="h-64 bg-bg-alt rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !alert) {
    return (
      <div className="p-6">
        <div className="bg-red-900/20 border border-red-900 rounded-lg p-4">
          <p className="text-red-400">Failed to load alert details</p>
        </div>
      </div>
    );
  }

  const severity = (alert.raw_severity || (alert as any).severity || 'low') as string;
  const detectionTime = alert.detection_time || (alert as any).timestamp || alert.created_at;
  const mitreTactic =
    alert.mitre_tactic ||
    (Array.isArray(alert.mitre_tactics) && alert.mitre_tactics[0]?.name) ||
    (typeof alert.mitre_tactics === 'string' ? alert.mitre_tactics : undefined);
  const mitreTechnique =
    alert.mitre_technique ||
    (Array.isArray(alert.mitre_techniques) && alert.mitre_techniques[0]?.name) ||
    (typeof alert.mitre_techniques === 'string' ? alert.mitre_techniques : undefined);

  const controlStatusLabel = alert.control_gap === 'gap' ? 'Gap' : alert.control_gap === 'partial' ? 'Partial' : 'Covered';
  const controlStatusColor =
    alert.control_gap === 'gap'
      ? 'bg-red-500/15 text-red-300 border border-red-500/30'
      : alert.control_gap === 'partial'
      ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
      : 'bg-green-500/15 text-green-300 border border-green-500/30';
  const alertGraphHref = buildAlertGraphHref(alert.id);

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <Breadcrumbs />
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-text-main">{alert.title}</h1>
          <span
            className={`px-3 py-1 text-xs font-semibold rounded ${
              severity === 'critical'
                ? 'bg-red-500/20 text-red-500'
                : severity === 'high'
                ? 'bg-orange-500/20 text-orange-500'
                : severity === 'medium'
                ? 'bg-yellow-500/20 text-yellow-500'
                : 'bg-blue-500/20 text-blue-500'
            }`}
          >
            {severity?.toUpperCase()}
          </span>
          <span className="px-3 py-1 text-xs font-semibold rounded bg-primary/20 text-primary">
            {alert.status}
          </span>
        </div>
        <p className="text-text-muted">
          Detected {detectionTime ? new Date(detectionTime).toLocaleString() : '—'} • Source: {alert.source}
        </p>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-text-muted">
          <span className="uppercase tracking-wide">Pipeline health</span>
          <HealthBadge label="Ingestion" status={sourceHealth?.ingestion_service} />
          <HealthBadge label="SIEM agent" status={sourceHealth?.siem_agent} />
          <HealthBadge label="OpenSearch" status={sourceHealth?.opensearch} />
          {detectionVersion() && (
            <span className="px-2 py-1 rounded-full text-[11px] border border-blue-500/40 text-blue-200">
              Det vID: {detectionVersion()}
            </span>
          )}
          {playbookId() && (
            <span className="px-2 py-1 rounded-full text-[11px] border border-primary/40 text-primary">
              PB: {playbookId()}
            </span>
          )}
          {playbookVersion() && (
            <span className="px-2 py-1 rounded-full text-[11px] border border-emerald-500/40 text-emerald-200">
              PB vID: {playbookVersion()}
            </span>
          )}
        </div>
        <div className="mt-3">
          <Link
            href={alertGraphHref}
            className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-primary/30 px-4 py-2 text-sm font-medium text-text-main hover:border-primary/50"
          >
            Open security graph
          </Link>
        </div>
      </div>
      {actionMessage && (
        <div className="mb-4 bg-green-500/10 border border-green-500/30 text-green-200 text-sm px-3 py-2 rounded">
          {actionMessage}
        </div>
      )}

      {/* Alert Details */}
      <div className="grid gap-6 mb-6">
        {/* Overview + Classification */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <h2 className="text-lg font-semibold text-text-main mb-4">Overview</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="text-sm text-text-muted mb-1">Description</div>
              <div className="text-text-main">{alert.description || 'No description available'}</div>
            </div>
            {alert.external_id && (
              <div>
                <div className="text-sm text-text-muted mb-1">External ID</div>
                <div className="text-text-main font-mono text-sm">{alert.external_id}</div>
              </div>
            )}
            {alert.asset_id && (
              <div>
                <div className="text-sm text-text-muted mb-1">Affected Asset</div>
                <div className="text-text-main">{alert.asset_id}</div>
              </div>
            )}
            {alert.user_identifier && (
              <div>
                <div className="text-sm text-text-muted mb-1">Affected User</div>
                <div className="text-text-main">{alert.user_identifier}</div>
              </div>
            )}
            <div>
              <div className="text-sm text-text-muted mb-1">Category</div>
              <div className="text-text-main font-semibold capitalize">
                {alert.category || 'Uncategorized'}
              </div>
            </div>
            {(alert as any).detection_rule_id && (
              <div>
                <div className="text-sm text-text-muted mb-1">Detection Rule</div>
                <a
                  href={`/dashboard/siem/detection-rules/${(alert as any).detection_rule_id}`}
                  className="text-primary hover:text-primary/80 font-mono text-sm"
                >
                  {(alert as any).detection_rule_id}
                </a>
                {(alert as any).detection_rule_version_id && (
                  <div className="text-xs text-text-muted">
                    Version ID: {(alert as any).detection_rule_version_id}
                  </div>
                )}
              </div>
            )}
            {(alert as any).playbook_version_id && (
              <div>
                <div className="text-sm text-text-muted mb-1">Playbook Version</div>
                <div className="text-text-main font-mono text-sm">
                  {(alert as any).playbook_version_id}
                </div>
              </div>
            )}
            <div>
              <div className="text-sm text-text-muted mb-1">MITRE</div>
              <div className="text-text-main text-sm">
                {mitreTactic || mitreTechnique ? (
                  <>
                    {mitreTactic && <span>{mitreTactic}</span>}
                    {mitreTactic && mitreTechnique && <span className="mx-1 text-text-muted">/</span>}
                    {mitreTechnique && <span className="text-text-muted">{mitreTechnique}</span>}
                  </>
                ) : (
                  <span className="text-text-muted">Not tagged</span>
                )}
              </div>
            </div>
          </div>
        </div>

        <StoryContextPanel
          title="Cross-domain story"
          description="Canonical entities and supporting evidence linked to this alert."
          domains={alert.story_domains}
          entities={alert.entities}
          evidence={alert.evidence}
          emptyEntityText="No linked entities have been normalized for this alert yet."
          emptyEvidenceText="No supporting evidence has been linked yet."
          graphHref={alertGraphHref}
          getEntityGraphHref={(entity) =>
            buildAlertGraphHref(alert.id, {
              focusEntityId: entity.id,
              sourceLabel: 'Back to alert',
              sourceHref: `/dashboard/alerts/${alert.id}`,
            })
          }
          getEvidenceGraphHref={(item) =>
            buildAlertGraphHref(alert.id, {
              focusEvidenceId: item.id,
              sourceLabel: 'Back to alert',
              sourceHref: `/dashboard/alerts/${alert.id}`,
            })
          }
        />

        <CrossDomainRelationshipView
          title="Cross-domain relationships"
          description="Follow how this alert moves across identity, endpoint, cloud, application, and AI lanes so the operator can pivot into the next system with context."
          domains={alert.story_domains}
          entities={alert.entities}
          evidence={alert.evidence}
        />

        <ResponsePackPanel
          title="Saved response packs"
          description="Use a saved SMB attack-pattern pack to move from this alert into the right owner, SLA, and playbook path without rebuilding the response each time."
          packs={matchedResponsePacks}
          runningPlaybookId={(runPlaybookMutation.variables as string | undefined) || null}
          onRunPlaybook={(playbookId, pack) => {
            handleRunPlaybook(playbookId, `${pack.pack.label} playbook`);
          }}
          emptyState="No saved response pack matched this alert yet. Use the detection-specific recommendation or the broader playbook library."
        />

        {/* Control coverage */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-text-main">Control coverage</h2>
            <span className={`px-2 py-1 rounded text-xs font-semibold ${controlStatusColor}`}>
              {controlStatusLabel}
            </span>
          </div>
          <div className="flex flex-wrap gap-2 mb-3">
            {(alert.control_tags || []).length > 0 ? (
              alert.control_tags!.map((ct) => (
                <span
                  key={ct}
                  className="px-2 py-1 rounded bg-[rgba(34,197,94,0.15)] text-[11px] text-green-300 border border-green-500/20"
                >
                  {ct}
                </span>
              ))
            ) : (
              <span className="text-text-muted text-sm">No control mapping provided.</span>
            )}
          </div>
          {alert.control_gap && alert.control_gap !== 'covered' && (
            <div className="text-sm text-amber-200 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3">
              {alert.raw_payload?.control_gap_note ||
                alert.raw_payload?.gap_note ||
                'Coverage gap detected. Add or tune the relevant control for this detection.'}
            </div>
          )}
        </div>

        {/* Raw Payload */}
        {alert.raw_payload && (
          <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">Raw Data</h2>
            <pre className="bg-[rgba(2,6,23,0.9)] p-4 rounded-lg overflow-x-auto text-xs text-text-muted">
              {JSON.stringify(alert.raw_payload, null, 2)}
            </pre>
          </div>
        )}

        {/* AI Analysis */}
        {aiAnalyses.length > 0 && (
          <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
            <h2 className="text-lg font-semibold text-text-main mb-4">AI Analysis</h2>
            <div className="space-y-4">
              {aiAnalyses.map((analysis: any, index: number) => (
                (() => {
                  const analysisSteps = Array.isArray(analysis.recommended_actions)
                    ? analysis.recommended_actions
                    : Array.isArray(analysis.recommended_actions?.steps_preview)
                      ? analysis.recommended_actions.steps_preview
                      : [];

                  return (
                    <AITransparencyPanel
                      key={`${analysis.id || analysis.model_name || 'analysis'}-${index}`}
                      embedded
                      title={`AI classified this alert as ${analysis.ai_severity || 'unknown'} severity${analysis.ai_category ? ` in ${analysis.ai_category}` : ''}.`}
                      summary="Use the reasoning chain before escalating or dismissing the alert."
                      why={analysis.rationale}
                      confidence={analysis.ai_confidence}
                      modelName={analysis.model_name}
                      modelVersion={analysis.model_version}
                      provider={analysis.provider}
                      sourceLabel={analysis.inference_source}
                      processingHint={analysis.inference_source}
                      disagreeLabel="Disagree with classification"
                      onDisagree={async () => {
                        await submitAlertAIFeedback('ai_classification_disagreed', {
                          feedback_scope: 'classification',
                          analysis_id: analysis.id || null,
                          analysis_index: index,
                          ai_category: analysis.ai_category || null,
                          ai_severity: analysis.ai_severity || null,
                          ai_confidence: analysis.ai_confidence ?? null,
                          model_name: analysis.model_name || null,
                          model_version: analysis.model_version || null,
                          provider: analysis.provider || null,
                          inference_source: analysis.inference_source || null,
                        });
                        setActionMessage('AI classification feedback captured for analyst review.');
                      }}
                    >
                      {(analysisSteps.length > 0 || analysis.recommended_actions?.playbook_key) && (
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                            Suggested next steps
                          </p>
                          {analysis.recommended_actions?.playbook_key && (
                            <p className="mt-2 text-sm text-text-muted">
                              Playbook key: {analysis.recommended_actions.playbook_key}
                            </p>
                          )}
                          {analysisSteps.length > 0 && (
                            <ul className="mt-2 space-y-2">
                              {analysisSteps.map((step: string) => (
                                <li
                                  key={step}
                                  className="rounded-lg border border-border-faint px-3 py-2 text-sm text-text-main"
                                >
                                  {step}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </AITransparencyPanel>
                  );
                })()
              ))}
            </div>
          </div>
        )}

        {/* Related items */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-text-main">Related items</h2>
            <span className="text-xs text-text-muted">
              Incidents: {related.incidents.length} • Detections: {related.detections.length} • Evidence: {related.evidence.length}
            </span>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-text-muted mb-1">Incidents</div>
              {related.incidents.length ? (
                <div className="space-y-1">
                  {related.incidents.map((inc: any) => (
                    <a
                      key={inc.id}
                      href={inc.href || `/dashboard/incidents/${inc.id}`}
                      className="block text-sm text-primary hover:text-primary/80"
                    >
                      {inc.title} ({inc.id})
                    </a>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-text-muted">None linked</div>
              )}
            </div>
            <div>
              <div className="text-sm text-text-muted mb-1">Detections</div>
              {related.detections.length ? (
                <div className="space-y-1">
                  {related.detections.map((det: any) => (
                    <a
                      key={det.id}
                      href={det.href || `/dashboard/alerts/${det.id}`}
                      className="block text-sm text-primary hover:text-primary/80"
                    >
                      {det.title} ({det.id})
                    </a>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-text-muted">None linked</div>
              )}
            </div>
            <div>
              <div className="text-sm text-text-muted mb-1">Evidence</div>
              {related.evidence.length ? (
                <ul className="space-y-1 text-sm text-text-main">
                  {related.evidence.map((ev: any, idx: number) => (
                    <li key={idx}>
                      {ev.title || ev.name || ev.filename || 'Evidence'}
                      {ev.href ? (
                        <a href={ev.href} className="text-primary ml-1" target="_blank" rel="noreferrer">
                          open
                        </a>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-sm text-text-muted">No evidence attached</div>
              )}
            </div>
          </div>
        </div>

        {/* Recommended response */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-text-main">Recommended response</h2>
            {alert.recommended_playbook ? (
              <span className="px-2 py-1 text-[11px] rounded bg-primary/15 text-primary border border-primary/30">
                {alert.recommended_playbook}
              </span>
            ) : (
              <span className="text-text-muted text-xs">No recommendation</span>
            )}
          </div>
          {recommendationWhy.length > 0 && (
            <div className="mb-4">
              <AITransparencyPanel
                embedded
                title={
                  alert.recommended_playbook
                    ? `${alert.recommended_playbook} is the recommended response path.`
                    : 'SentinelGrid generated a recommended next step.'
                }
                summary="Review the explanation before launching automation or choosing an alternate playbook."
                why={recommendationWhy}
                confidence={latestAiAnalysis?.ai_confidence}
                modelName={latestAiAnalysis?.model_name}
                modelVersion={latestAiAnalysis?.model_version}
                provider={latestAiAnalysis?.provider}
                sourceLabel={latestAiAnalysis?.inference_source}
                processingHint={latestAiAnalysis?.inference_source}
                disagreeLabel="Disagree with recommendation"
                onDisagree={async () => {
                  await submitAlertAIFeedback('ai_recommendation_disagreed', {
                    feedback_scope: 'recommendation',
                    ai_confidence: latestAiAnalysis?.ai_confidence ?? null,
                    model_name: latestAiAnalysis?.model_name || null,
                    model_version: latestAiAnalysis?.model_version || null,
                    provider: latestAiAnalysis?.provider || null,
                    inference_source: latestAiAnalysis?.inference_source || null,
                    alternate_playbooks: alternatePlaybooks.map((playbook) => playbook.id),
                    recommendation_why: recommendationWhy,
                  });
                  setActionMessage('Recommendation feedback captured for analyst review.');
                }}
              >
                {alternatePlaybooks.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                      Alternate playbooks considered
                    </p>
                    <div className="mt-2 space-y-2">
                      {alternatePlaybooks.map((p) => (
                        <div key={p.id} className="rounded-lg border border-border-faint px-3 py-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full border border-primary/20 bg-primary/10 px-2 py-1 text-[11px] text-primary">
                              {p.name}
                            </span>
                          </div>
                          {p.rationale && (
                            <p className="mt-2 text-sm text-text-muted">{p.rationale}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </AITransparencyPanel>
            </div>
          )}
          {playbookStatus && (
            <div className="text-sm text-primary mb-3">{playbookStatus}</div>
          )}
          {alternatePlaybooks.length > 0 && recommendationWhy.length === 0 && (
            <div className="mb-4 space-y-1">
              <div className="text-xs text-text-muted">Alternates:</div>
              {alternatePlaybooks.map((p) => (
                <div key={p.id} className="text-sm text-text-main flex items-center gap-2">
                  <span className="px-2 py-1 text-[11px] rounded bg-primary/10 text-primary border border-primary/20">
                    {p.name}
                  </span>
                  {p.rationale && <span className="text-[11px] text-text-muted">{p.rationale}</span>}
                </div>
              ))}
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <button
              className="px-4 py-2 bg-primary text-slate-950 rounded-lg hover:brightness-110 font-medium"
              disabled={!matchedPlaybookId && !alert.recommended_playbook}
              onClick={() => setShowPlaybookConfirm(true)}
            >
              Run recommended playbook
            </button>
            {matchedPlaybookId ? (
              <Link
                href={`/dashboard/playbooks/${matchedPlaybookId}`}
                className="inline-flex items-center px-4 py-2 bg-surface-card border border-primary/30 text-primary rounded-lg hover:bg-primary/10"
              >
                Open playbook details
              </Link>
            ) : (
              <button
                type="button"
                disabled
                className="px-4 py-2 bg-surface-card border border-primary/20 text-primary/60 rounded-lg cursor-not-allowed"
              >
                Playbook details unavailable
              </button>
            )}
          </div>
        </div>

        {/* Status & actions */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <h2 className="text-lg font-semibold text-text-main mb-3">Status &amp; actions</h2>
          <div className="flex flex-wrap gap-3">
            <button
              className="px-4 py-2 bg-surface-card border border-primary/30 text-primary rounded-lg hover:bg-primary/10 text-sm"
              onClick={() => statusMutation.mutate('acknowledged')}
              disabled={statusMutation.isPending}
            >
              Mark In Progress
            </button>
            <button
              className="px-4 py-2 bg-surface-card border border-green-500/30 text-green-300 rounded-lg hover:bg-green-500/10 text-sm"
              onClick={() => statusMutation.mutate('resolved')}
              disabled={statusMutation.isPending}
            >
              Mark Resolved
            </button>
            <button
              className="px-4 py-2 bg-surface-card border border-amber-500/30 text-amber-300 rounded-lg hover:bg-amber-500/10 text-sm"
              onClick={() => statusMutation.mutate('false_positive' as Alert['status'])}
              disabled={statusMutation.isPending}
            >
              Mark False Positive
            </button>
          </div>
          <div className="mt-5">
            <IssueOwnershipSlaPanel
              issueLabel="Alert"
              currentOwner={(alert as any).assigned_to || alert.raw_payload?.assigned_to}
              currentDueDate={alert.due_date || alert.raw_payload?.due_date || alert.raw_payload?.sla_due_at}
              onOwnerSave={handleAssignmentUpdate}
              onDueDateSave={handleDueDateUpdate}
              ownerSaving={assignMutation.isPending}
              dueDateSaving={dueDateMutation.isPending}
              assignmentTitle="Alert ownership"
              assignmentDescription="Search the configured downstream directory, then save the assignee identifier on this alert."
              assignmentSaveLabel="Assign alert"
            />
          </div>
        </div>

        {/* Audit trail */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-text-main">Audit &amp; actions</h2>
            <span className="text-xs text-text-muted">
              {auditEntries.length > 0 ? `${auditEntries.length} entries` : 'No history yet'}
            </span>
          </div>
          {auditEntries.length > 0 ? (
            <div className="space-y-2">
              {auditEntries.map((entry, idx) => (
                <div key={`${entry.ts || idx}-${idx}`} className="flex items-start gap-3">
                  <div className="text-[11px] text-text-muted w-36">
                    {entry.ts ? new Date(entry.ts).toLocaleString() : '—'}
                  </div>
                  <div className="flex-1 text-sm text-text-main">
                    {entry.text}
                    <span className="text-[11px] text-text-muted ml-2">{entry.kind === 'comment' ? 'comment' : 'event'}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No audit history yet. Actions and timeline events will appear here.</p>
          )}
        </div>

        {/* Timeline / Evidence placeholders */}
        <div className="bg-surface-card rounded-xl border border-surface-card-border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-main">Timeline &amp; Evidence</h2>
            {entityContext ? (
              <span className="text-xs text-text-muted">
                Entity: {entityContext.type} • {entityContext.id}
              </span>
            ) : (
              <span className="text-xs text-text-muted">No entity context</span>
            )}
          </div>
          {timeline && timeline.events && timeline.events.length > 0 ? (
            <div className="space-y-3">
              {timeline.events.slice(0, 10).map((evt) => (
                <div key={evt.id} className="flex gap-3 items-start border border-[rgba(255,255,255,0.05)] rounded-lg px-3 py-2">
                  <div className="text-[11px] text-text-muted w-40">
                    {evt.timestamp ? new Date(evt.timestamp).toLocaleString() : '—'}
                  </div>
                  <div className="flex-1">
                    <div className="text-sm text-text-main font-medium">
                      {evt.event_type || 'event'} {evt.action ? `• ${evt.action}` : ''}
                    </div>
                    {evt.source?.ip && (
                      <div className="text-[11px] text-text-muted">Src IP: {evt.source.ip}</div>
                    )}
                    {evt.user?.email && (
                      <div className="text-[11px] text-text-muted">User: {evt.user.email}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">
              {entityContext ? 'No recent events for this entity.' : 'Add an entity (user or asset) to view timeline.'}
            </p>
          )}
        </div>
      </div>

      {showPlaybookConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-semibold text-text-main mb-2">Run recommended playbook?</h3>
            <p className="text-sm text-text-muted mb-4">
              This will execute the recommended response for this detection. Confirm to proceed.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowPlaybookConfirm(false)}
                className="px-4 py-2 rounded border border-border text-text-main hover:bg-[rgba(255,255,255,0.05)]"
              >
                Keep current plan
              </button>
              <button
                disabled={runPlaybookMutation.isPending}
                onClick={() => {
                  const recommendedPlaybookId = matchedPlaybookId || alert.recommended_playbook;
                  if (!recommendedPlaybookId) {
                    setActionMessage('No recommended playbook available');
                    return;
                  }
                  runPlaybookMutation.mutate(recommendedPlaybookId);
                }}
                className="px-4 py-2 rounded bg-primary text-slate-950 hover:brightness-110"
              >
                {runPlaybookMutation.isPending ? 'Launching...' : 'Launch recommended playbook'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
