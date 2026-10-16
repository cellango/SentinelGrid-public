export type CanonicalStoryDomain =
  | 'identity'
  | 'endpoint'
  | 'cloud'
  | 'application'
  | 'ai'
  | 'security';

export interface CanonicalEntityRef {
  type: 'identity' | 'device' | 'resource' | 'ai_app';
  id: string;
  label: string;
  domain: CanonicalStoryDomain;
  role?: string;
  provider?: string;
  href?: string;
  metadata?: Record<string, unknown>;
}

export interface CanonicalEvidenceRef {
  type: 'alert' | 'incident' | 'ticket' | 'detection_rule' | 'playbook' | 'attachment' | 'cve' | 'finding';
  id: string;
  title: string;
  domain?: CanonicalStoryDomain;
  severity?: string;
  status?: string;
  source?: string;
  href?: string | null;
  metadata?: Record<string, unknown>;
}

export interface CanonicalStorySummary {
  headline: string;
  detail: string;
  domains: CanonicalStoryDomain[];
  primary_entity?: CanonicalEntityRef;
  entity_labels: string[];
  entity_count: number;
  evidence_count: number;
  evidence_types: Array<{
    type: CanonicalEvidenceRef['type'] | string;
    count: number;
  }>;
}

interface NormalizeStoryContextInput {
  rawPayload?: any;
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
  storyDomains?: string[];
  assetId?: string;
  userIdentifier?: string;
  detectionRuleId?: string;
  detectionRuleVersionId?: string;
  playbookId?: string;
  playbookVersionId?: string;
  relatedDetections?: Array<{ id: string; title?: string; severity?: string }>;
  ticketId?: string;
  externalTicketId?: string;
  externalTicketProvider?: string;
  cveIds?: string[];
}

const DOMAIN_LABELS: Record<CanonicalStoryDomain, string> = {
  identity: 'Identity',
  endpoint: 'Endpoint',
  cloud: 'Cloud',
  application: 'Application',
  ai: 'AI',
  security: 'Security',
};

const ENTITY_TYPE_LABELS: Record<CanonicalEntityRef['type'], string> = {
  identity: 'Identity',
  device: 'Device',
  resource: 'Resource',
  ai_app: 'AI App',
};

const EVIDENCE_TYPE_LABELS: Record<CanonicalEvidenceRef['type'], string> = {
  alert: 'Alert',
  incident: 'Incident',
  ticket: 'Ticket',
  detection_rule: 'Detection Rule',
  playbook: 'Playbook',
  attachment: 'Attachment',
  cve: 'CVE',
  finding: 'Finding',
};

function cleanString(value: unknown): string | undefined {
  if (value == null) return undefined;
  const text = String(value).trim();
  return text || undefined;
}

function uniqueRefs<T extends { type: string; id: string }>(items: T[]): T[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.type}:${item.id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function toDomain(value: unknown): CanonicalStoryDomain | undefined {
  const text = cleanString(value)?.toLowerCase();
  if (
    text === 'identity' ||
    text === 'endpoint' ||
    text === 'cloud' ||
    text === 'application' ||
    text === 'ai' ||
    text === 'security'
  ) {
    return text;
  }
  return undefined;
}

function inferDomainFromPayload(rawPayload: any): CanonicalStoryDomain {
  const category =
    cleanString(rawPayload?.sg?.category) ||
    cleanString(rawPayload?.category) ||
    cleanString(rawPayload?.finding?.type);

  if (rawPayload?.ai) return 'ai';
  if (rawPayload?.repo) return 'application';
  if (rawPayload?.cloud) return 'cloud';
  if (rawPayload?.host) return 'endpoint';
  if (rawPayload?.user || rawPayload?.identity) return 'identity';

  switch (category?.toLowerCase()) {
    case 'identity':
    case 'iam':
    case 'access':
    case 'authentication':
      return 'identity';
    case 'endpoint':
    case 'host':
    case 'process':
      return 'endpoint';
    case 'cloud':
    case 'network':
    case 'data':
    case 'storage':
      return 'cloud';
    case 'app':
    case 'application':
    case 'git':
    case 'repo':
    case 'secret':
      return 'application';
    case 'ai':
    case 'llm':
    case 'guardrail':
      return 'ai';
    default:
      return 'security';
  }
}

function evidenceHref(type: CanonicalEvidenceRef['type'], id: string): string | null {
  switch (type) {
    case 'alert':
      return `/dashboard/alerts/${encodeURIComponent(id)}`;
    case 'incident':
      return `/dashboard/incidents/${encodeURIComponent(id)}`;
    case 'ticket':
      return `/dashboard/tickets/${encodeURIComponent(id)}`;
    case 'detection_rule':
      return `/dashboard/siem/detection-rules/${encodeURIComponent(id)}`;
    case 'playbook':
      return `/dashboard/playbooks?playbook_id=${encodeURIComponent(id)}`;
    default:
      return null;
  }
}

export function normalizeStoryContext(input: NormalizeStoryContextInput): {
  entities: CanonicalEntityRef[];
  evidence: CanonicalEvidenceRef[];
  story_domains: CanonicalStoryDomain[];
} {
  const rawPayload = input.rawPayload ?? {};
  const defaultDomain = inferDomainFromPayload(rawPayload);
  const entities: CanonicalEntityRef[] = [];
  const evidence: CanonicalEvidenceRef[] = [];

  for (const entity of input.entities ?? rawPayload.entities ?? []) {
    const id = cleanString(entity?.id);
    const type = cleanString(entity?.type) as CanonicalEntityRef['type'] | undefined;
    if (!id || !type) continue;
    entities.push({
      type,
      id,
      label: cleanString(entity?.label) ?? id,
      domain: toDomain(entity?.domain) ?? defaultDomain,
      role: cleanString(entity?.role),
      provider: cleanString(entity?.provider),
      href: cleanString(entity?.href),
      metadata: entity?.metadata,
    });
  }

  for (const item of input.evidence ?? rawPayload.evidence ?? []) {
    const id = cleanString(item?.id);
    const type = cleanString(item?.type) as CanonicalEvidenceRef['type'] | undefined;
    if (!id || !type) continue;
    evidence.push({
      type,
      id,
      title: cleanString(item?.title) ?? id,
      domain: toDomain(item?.domain),
      severity: cleanString(item?.severity),
      status: cleanString(item?.status),
      source: cleanString(item?.source),
      href: cleanString(item?.href) ?? evidenceHref(type, id),
      metadata: item?.metadata,
    });
  }

  const user = rawPayload.user ?? {};
  const host = rawPayload.host ?? {};
  const repo = rawPayload.repo ?? {};
  const ai = rawPayload.ai ?? {};
  const cloud = rawPayload.cloud ?? {};

  const identityId =
    cleanString(input.userIdentifier) ||
    cleanString(user.email) ||
    cleanString(user.id) ||
    cleanString(user.name) ||
    cleanString(ai.user_id);
  if (identityId) {
    entities.push({
      type: 'identity',
      id: identityId,
      label: cleanString(user.email) || cleanString(user.name) || identityId,
      domain: 'identity',
      role: 'affected_identity',
      href: `/dashboard/iam/people?user_id=${encodeURIComponent(identityId)}`,
    });
  }

  const hostId = cleanString(host.hostname) || cleanString(host.id);
  const assetId = cleanString(input.assetId);
  if (hostId || assetId) {
    const entityId = hostId || assetId!;
    entities.push({
      type: rawPayload.cloud || rawPayload.repo || rawPayload.ai ? 'resource' : 'device',
      id: entityId,
      label: cleanString(host.hostname) || assetId || entityId,
      domain: hostId ? 'endpoint' : defaultDomain,
      role: 'affected_asset',
      href: `/dashboard/endpoint-protection?asset_id=${encodeURIComponent(entityId)}`,
    });
  }

  const cloudAccountId = cleanString(cloud?.account?.id);
  const cloudProvider = cleanString(cloud?.provider);
  if (cloudAccountId) {
    entities.push({
      type: 'resource',
      id: `${cloudProvider || 'cloud'}:${cloudAccountId}`,
      label: `${(cloudProvider || 'cloud').toUpperCase()} account ${cloudAccountId}`,
      domain: 'cloud',
      role: 'cloud_account',
      provider: cloudProvider,
      href: '/dashboard/compliance',
    });
  }

  const repoId = cleanString(repo.id) || cleanString(repo.name);
  if (repoId) {
    entities.push({
      type: 'resource',
      id: `repo:${repoId}`,
      label: cleanString(repo.name) || repoId,
      domain: 'application',
      role: 'repository',
      provider: 'git',
      href: '/dashboard/posture',
    });
  }

  const aiAppId = cleanString(ai.app_id) || cleanString(ai.application);
  if (aiAppId) {
    entities.push({
      type: 'ai_app',
      id: aiAppId,
      label: aiAppId,
      domain: 'ai',
      role: 'ai_application',
      provider: cleanString(ai.provider),
      href: '/dashboard/compliance/ai-activity',
    });
  }

  for (const incidentId of rawPayload.incident_ids ?? []) {
    const id = cleanString(incidentId);
    if (!id) continue;
    evidence.push({
      type: 'incident',
      id,
      title: 'Related incident',
      domain: defaultDomain,
      href: evidenceHref('incident', id),
    });
  }

  for (const detection of input.relatedDetections ?? []) {
    const id = cleanString(detection.id);
    if (!id) continue;
    evidence.push({
      type: 'alert',
      id,
      title: cleanString(detection.title) ?? 'Linked alert',
      domain: defaultDomain,
      severity: cleanString(detection.severity),
      href: evidenceHref('alert', id),
    });
  }

  for (const alertId of rawPayload.related_alert_ids ?? []) {
    const id = cleanString(alertId);
    if (!id) continue;
    evidence.push({
      type: 'alert',
      id,
      title: 'Linked alert',
      domain: defaultDomain,
      href: evidenceHref('alert', id),
    });
  }

  if (input.detectionRuleId) {
    evidence.push({
      type: 'detection_rule',
      id: input.detectionRuleId,
      title: input.detectionRuleId,
      domain: defaultDomain,
      href: evidenceHref('detection_rule', input.detectionRuleId),
      metadata: input.detectionRuleVersionId ? { version_id: input.detectionRuleVersionId } : undefined,
    });
  }

  if (input.playbookId) {
    evidence.push({
      type: 'playbook',
      id: input.playbookId,
      title: input.playbookId,
      domain: defaultDomain,
      href: evidenceHref('playbook', input.playbookId),
      metadata: input.playbookVersionId ? { version_id: input.playbookVersionId } : undefined,
    });
  }

  if (input.ticketId) {
    evidence.push({
      type: 'ticket',
      id: input.ticketId,
      title: `Local ticket ${input.ticketId}`,
      domain: defaultDomain,
      href: evidenceHref('ticket', input.ticketId),
    });
  } else if (input.externalTicketId) {
    evidence.push({
      type: 'ticket',
      id: input.externalTicketId,
      title: `${input.externalTicketProvider || 'ticket'}:${input.externalTicketId}`,
      domain: defaultDomain,
      source: input.externalTicketProvider,
      href: null,
    });
  }

  for (const cveId of input.cveIds ?? []) {
    const id = cleanString(cveId);
    if (!id) continue;
    evidence.push({
      type: 'cve',
      id,
      title: id,
      domain: defaultDomain,
      href: null,
    });
  }

  for (const attachment of rawPayload.evidence ?? rawPayload.attachments ?? []) {
    if (typeof attachment === 'string') {
      evidence.push({
        type: 'attachment',
        id: attachment,
        title: 'Attachment',
        href: null,
      });
      continue;
    }
    const attachmentId =
      cleanString(attachment?.id) ||
      cleanString(attachment?.url) ||
      cleanString(attachment?.filename) ||
      cleanString(attachment?.name);
    if (!attachmentId) continue;
    evidence.push({
      type: 'attachment',
      id: attachmentId,
      title: cleanString(attachment?.name) || cleanString(attachment?.filename) || 'Attachment',
      href: cleanString(attachment?.url) || null,
      metadata: attachment,
    });
  }

  const uniqueEntities = uniqueRefs(entities);
  const uniqueEvidence = uniqueRefs(evidence);
  const storyDomains = Array.from(
    new Set(
      [
        ...(input.storyDomains ?? []),
        ...uniqueEntities.map((item) => item.domain),
        ...uniqueEvidence.map((item) => item.domain).filter(Boolean),
      ].map((domain) => toDomain(domain) ?? defaultDomain)
    )
  ) as CanonicalStoryDomain[];

  return {
    entities: uniqueEntities,
    evidence: uniqueEvidence,
    story_domains: storyDomains.length > 0 ? storyDomains : [defaultDomain],
  };
}

export function summarizeStoryContext(input: {
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
  story_domains?: CanonicalStoryDomain[];
}): CanonicalStorySummary {
  const entities = input.entities ?? [];
  const evidence = input.evidence ?? [];
  const domains =
    input.story_domains && input.story_domains.length > 0
      ? input.story_domains
      : (Array.from(
          new Set([
            ...entities.map((item) => item.domain),
            ...evidence.map((item) => item.domain).filter(Boolean),
          ])
        ) as CanonicalStoryDomain[]);

  const storyDomains = (domains.length > 0 ? domains : ['security']) as CanonicalStoryDomain[];
  const primaryEntity = entities[0];
  const entityLabels = Array.from(
    new Set(
      entities
        .map((entity) => cleanString(entity.label) ?? cleanString(entity.id))
        .filter((label): label is string => Boolean(label))
    )
  ).slice(0, 3);

  const evidenceTypeCounts = evidence.reduce<Record<string, number>>((counts, item) => {
    const key = item.type || 'attachment';
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});

  const headline =
    storyDomains.length === 1
      ? `${formatStoryDomainLabel(storyDomains[0])} story`
      : storyDomains.length <= 3
        ? `${storyDomains.map((domain) => formatStoryDomainLabel(domain)).join(' + ')} story`
        : `${formatStoryDomainLabel(storyDomains[0])} + ${storyDomains.length - 1} more domains`;

  const detailParts: string[] = [];
  if (primaryEntity) {
    detailParts.push(primaryEntity.label);
  } else if (entityLabels.length > 0) {
    detailParts.push(`${entityLabels.length} linked ${entityLabels.length === 1 ? 'entity' : 'entities'}`);
  }
  if (evidence.length > 0) {
    detailParts.push(`${evidence.length} evidence item${evidence.length === 1 ? '' : 's'}`);
  }

  return {
    headline,
    detail: detailParts.join(' · ') || 'No linked story context yet',
    domains: storyDomains,
    primary_entity: primaryEntity,
    entity_labels: entityLabels,
    entity_count: entities.length,
    evidence_count: evidence.length,
    evidence_types: Object.entries(evidenceTypeCounts)
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .map(([type, count]) => ({ type, count })),
  };
}

export function formatStoryDomainLabel(domain: string): string {
  return DOMAIN_LABELS[(toDomain(domain) || 'security') as CanonicalStoryDomain];
}

export function formatStoryEntityTypeLabel(type: string): string {
  return ENTITY_TYPE_LABELS[(cleanString(type) as CanonicalEntityRef['type']) || 'resource'];
}

export function formatStoryEvidenceTypeLabel(type: string): string {
  return EVIDENCE_TYPE_LABELS[(cleanString(type) as CanonicalEvidenceRef['type']) || 'attachment'];
}
