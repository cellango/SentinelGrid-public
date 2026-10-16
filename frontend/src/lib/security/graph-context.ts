import type { AttackPath, AttackPathEntity, AttackPathLink } from '@/components/security-graph';
import type { NowQueueItem } from '@/lib/api/dashboard';
import type {
  CanonicalEntityRef,
  CanonicalEvidenceRef,
  CanonicalStoryDomain,
} from '@/lib/security/story';

type GraphSeverity = AttackPath['severity'];

type BuildStoryGraphInput = {
  title: string;
  severity?: string | null;
  summary?: string | null;
  domains?: Array<CanonicalStoryDomain | string>;
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
};

type BuildEntityGraphInput = {
  entityType: CanonicalEntityRef['type'];
  entityId: string;
  entityLabel: string;
  entityDomain?: CanonicalStoryDomain | string;
  title?: string;
  severity?: string | null;
  summary?: string | null;
  entitlementsCount?: number;
};

type GraphHrefFocusOptions = {
  focusEntityId?: string | null;
  focusEvidenceId?: string | null;
  sourceLabel?: string | null;
  sourceHref?: string | null;
};

const DOMAIN_ORDER: CanonicalStoryDomain[] = [
  'identity',
  'endpoint',
  'cloud',
  'application',
  'ai',
  'security',
];

const VULNERABILITY_TYPES = new Set<CanonicalEvidenceRef['type']>([
  'alert',
  'incident',
  'finding',
  'cve',
  'attachment',
]);

const CONTROL_TYPES = new Set<CanonicalEvidenceRef['type']>([
  'ticket',
  'detection_rule',
  'playbook',
]);

function normalizeSeverity(value?: string | null): GraphSeverity {
  const text = (value || '').toLowerCase();
  if (text === 'critical' || text === 'high' || text === 'medium' || text === 'low') {
    return text;
  }
  return 'medium';
}

function normalizeDomain(value?: CanonicalStoryDomain | string | null): CanonicalStoryDomain {
  const text = (value || '').toLowerCase();
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
  return 'security';
}

function safeText(value: unknown, fallback: string) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text || fallback;
}

function domainRank(value?: CanonicalStoryDomain | string | null) {
  const domain = normalizeDomain(value);
  const index = DOMAIN_ORDER.indexOf(domain);
  return index === -1 ? DOMAIN_ORDER.length : index;
}

function dedupeEntities(entities: AttackPathEntity[]) {
  const seen = new Set<string>();
  return entities.filter((entity) => {
    if (seen.has(entity.id)) {
      return false;
    }
    seen.add(entity.id);
    return true;
  });
}

function buildHref(params: Record<string, string | null | undefined>) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });

  const query = searchParams.toString();
  return query ? `/dashboard/security-graph?${query}` : '/dashboard/security-graph';
}

function toEntityNode(entity: CanonicalEntityRef): AttackPathEntity {
  const role = (entity.role || '').toLowerCase();
  const type: AttackPathEntity['type'] =
    entity.type === 'identity' && /threat|attacker|suspect|actor|compromised/.test(role)
      ? 'threat_actor'
      : 'asset';

  return {
    id: `entity:${entity.type}:${entity.id}`,
    type,
    label: safeText(entity.label, entity.id),
    domain: normalizeDomain(entity.domain),
    status: entity.role,
    metadata: {
      graph_kind: 'entity',
      canonical_id: entity.id,
      canonical_type: entity.type,
      href: entity.href,
      provider: entity.provider,
      role: entity.role,
    },
  };
}

function toEvidenceNode(item: CanonicalEvidenceRef): AttackPathEntity {
  const type: AttackPathEntity['type'] = VULNERABILITY_TYPES.has(item.type)
    ? 'vulnerability'
    : CONTROL_TYPES.has(item.type)
      ? 'control'
      : 'asset';

  return {
    id: `evidence:${item.type}:${item.id}`,
    type,
    label: safeText(item.title, item.id),
    domain: normalizeDomain(item.domain),
    severity: normalizeSeverity(item.severity),
    status: item.status,
    metadata: {
      graph_kind: 'evidence',
      canonical_id: item.id,
      canonical_type: item.type,
      href: item.href,
      source: item.source,
    },
  };
}

function createImpactNode(
  title: string,
  severity: GraphSeverity,
  summary?: string | null,
  domain?: CanonicalStoryDomain | string | null
): AttackPathEntity {
  return {
    id: `impact:${title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'story'}`,
    type: 'impact',
    label: `${safeText(title, 'Story')} blast radius`,
    severity,
    domain: normalizeDomain(domain),
    metadata: {
      graph_kind: 'impact',
      summary: summary || null,
    },
  };
}

function buildChainLinks(chain: AttackPathEntity[], controls: AttackPathEntity[]): AttackPathLink[] {
  const links: AttackPathLink[] = [];

  for (let index = 0; index < chain.length - 1; index += 1) {
    const source = chain[index];
    const target = chain[index + 1];
    let type: AttackPathLink['type'] = 'lateral_move';
    let label = 'pivots';

    if (target.type === 'impact') {
      type = 'exposes';
      label = 'widens impact';
    } else if (source.type === 'threat_actor' || source.type === 'vulnerability') {
      type = 'exploits';
      label = 'leverages';
    } else if (source.domain !== target.domain) {
      type = 'lateral_move';
      label = 'crosses domains';
    } else {
      type = 'escalates';
      label = 'extends access';
    }

    links.push({
      source: source.id,
      target: target.id,
      type,
      label,
    });
  }

  const mitigationTarget =
    chain.find((node) => node.type === 'vulnerability') ||
    chain.find((node) => node.type !== 'impact');

  if (mitigationTarget) {
    controls.forEach((control) => {
      links.push({
        source: control.id,
        target: mitigationTarget.id,
        type: 'mitigates',
        label: 'constrains',
      });
    });
  }

  return links;
}

export function buildAttackPathsFromStory({
  title,
  severity,
  summary,
  domains = [],
  entities = [],
  evidence = [],
}: BuildStoryGraphInput): AttackPath[] {
  const normalizedSeverity = normalizeSeverity(severity);
  const orderedEntities = [...entities].sort((left, right) => {
    const leftRank = domainRank(left.domain);
    const rightRank = domainRank(right.domain);
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return safeText(left.label, left.id).localeCompare(safeText(right.label, right.id));
  });
  const orderedEvidence = [...evidence].sort((left, right) => {
    const leftRank = domainRank(left.domain);
    const rightRank = domainRank(right.domain);
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return safeText(left.title, left.id).localeCompare(safeText(right.title, right.id));
  });

  const threatActors = orderedEntities
    .map(toEntityNode)
    .filter((entity) => entity.type === 'threat_actor');
  const pivotEntities = orderedEntities
    .map(toEntityNode)
    .filter((entity) => entity.type !== 'threat_actor');
  const evidenceNodes = orderedEvidence.map(toEvidenceNode);
  const vulnerabilityNodes = evidenceNodes.filter((entity) => entity.type === 'vulnerability');
  const controlNodes = evidenceNodes.filter((entity) => entity.type === 'control').slice(0, 2);
  const storyDomain = domains[0] || orderedEntities[0]?.domain || orderedEvidence[0]?.domain || 'security';
  const impactNode = createImpactNode(title, normalizedSeverity, summary, storyDomain);
  const basePivotNodes =
    pivotEntities.length > 0
      ? pivotEntities
      : [
          {
            id: `entity:context:${safeText(title, 'story').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
            type: 'asset' as const,
            label: safeText(title, 'Story context'),
            domain: normalizeDomain(storyDomain),
            severity: normalizedSeverity,
            metadata: {
              graph_kind: 'context',
              summary: summary || null,
            },
          },
        ];

  if (vulnerabilityNodes.length === 0) {
    const chain = [...threatActors, ...basePivotNodes, impactNode];
    return [
      {
        id: 'path-story',
        title: safeText(title, 'Security story'),
        severity: normalizedSeverity,
        entities: dedupeEntities([...chain, ...controlNodes]),
        links: buildChainLinks(chain, controlNodes),
      },
    ];
  }

  return vulnerabilityNodes.slice(0, 3).map((vulnerability, index) => {
    const chain = [...threatActors, vulnerability, ...basePivotNodes, impactNode];
    return {
      id: `path-story-${index + 1}`,
      title: `${safeText(title, 'Security story')} · ${vulnerability.label}`,
      severity: (vulnerability.severity === 'info' ? 'low' : vulnerability.severity) || normalizedSeverity,
      entities: dedupeEntities([...chain, ...controlNodes]),
      links: buildChainLinks(chain, controlNodes),
    };
  });
}

export function buildEntityAttackPaths({
  entityType,
  entityId,
  entityLabel,
  entityDomain,
  title,
  severity,
  summary,
  entitlementsCount,
}: BuildEntityGraphInput): AttackPath[] {
  const primaryEntity = toEntityNode({
    type: entityType,
    id: entityId,
    label: entityLabel,
    domain: normalizeDomain(entityDomain),
    role: 'primary_pivot',
  });
  const graphSeverity = normalizeSeverity(severity);
  const supportEntities: AttackPathEntity[] = [];

  if (typeof entitlementsCount === 'number' && entitlementsCount > 0) {
    supportEntities.push({
      id: `evidence:entitlements:${entityId}`,
      type: 'vulnerability',
      label: `${entitlementsCount} assigned entitlement${entitlementsCount === 1 ? '' : 's'}`,
      severity: entitlementsCount >= 10 ? 'high' : entitlementsCount >= 5 ? 'medium' : 'low',
      domain: normalizeDomain(entityDomain),
      metadata: {
        graph_kind: 'derived',
        canonical_id: entityId,
        canonical_type: 'entitlements',
      },
    });
  }

  const impactNode = createImpactNode(
    title || `${entityLabel} access graph`,
    graphSeverity,
    summary,
    entityDomain
  );
  const chain = supportEntities.length > 0 ? [primaryEntity, ...supportEntities, impactNode] : [primaryEntity, impactNode];

  return [
    {
      id: `path-entity:${entityId}`,
      title: title || `${entityLabel} graph`,
      severity: graphSeverity,
      entities: dedupeEntities(chain),
      links: buildChainLinks(chain, []),
    },
  ];
}

export function buildAlertGraphHref(alertId: string, options: GraphHrefFocusOptions = {}) {
  return buildHref({
    alert_id: alertId,
    focus_entity_id: options.focusEntityId || undefined,
    focus_evidence_id: options.focusEvidenceId || undefined,
    source_label: options.sourceLabel || undefined,
    source_href: options.sourceHref || undefined,
  });
}

export function buildIncidentGraphHref(incidentId: string, options: GraphHrefFocusOptions = {}) {
  return buildHref({
    incident_id: incidentId,
    focus_entity_id: options.focusEntityId || undefined,
    focus_evidence_id: options.focusEvidenceId || undefined,
    source_label: options.sourceLabel || undefined,
    source_href: options.sourceHref || undefined,
  });
}

export function buildEntityGraphHref({
  entityType,
  entityId,
  entityLabel,
  entityDomain,
  title,
  severity,
  summary,
  entitlementsCount,
  sourceLabel,
  sourceHref,
}: BuildEntityGraphInput & {
  sourceLabel?: string | null;
  sourceHref?: string | null;
}) {
  return buildHref({
    entity_type: entityType,
    entity_id: entityId,
    entity_label: entityLabel,
    entity_domain: entityDomain ? normalizeDomain(entityDomain) : undefined,
    title: title || undefined,
    severity: severity || undefined,
    summary: summary || undefined,
    entitlements_count:
      typeof entitlementsCount === 'number' ? String(entitlementsCount) : undefined,
    source_label: sourceLabel || undefined,
    source_href: sourceHref || undefined,
  });
}

export function buildQueueItemGraphHref(item?: NowQueueItem | null) {
  if (!item) {
    return '/dashboard/security-graph';
  }

  if (item.item_type === 'alert') {
    return buildAlertGraphHref(item.id, {
      sourceLabel: 'Now queue',
      sourceHref: item.href,
    });
  }

  if (item.item_type === 'incident') {
    return buildIncidentGraphHref(item.id, {
      sourceLabel: 'Now queue',
      sourceHref: item.href,
    });
  }

  const primaryEntity = item.entities?.[0];
  if (primaryEntity) {
    return buildEntityGraphHref({
      entityType: primaryEntity.type,
      entityId: primaryEntity.id,
      entityLabel: primaryEntity.label,
      entityDomain: primaryEntity.domain,
      title: item.title,
      severity: item.priority,
      summary: item.summary,
      sourceLabel: 'Now queue',
      sourceHref: item.href,
    });
  }

  return '/dashboard/security-graph';
}

export function findAttackPathEntity(
  paths: AttackPath[],
  focus: { entityId?: string | null; evidenceId?: string | null }
) {
  const entityId = focus.entityId || null;
  const evidenceId = focus.evidenceId || null;

  for (const path of paths) {
    for (const entity of path.entities) {
      const canonicalId =
        typeof entity.metadata?.canonical_id === 'string' ? entity.metadata.canonical_id : null;
      const graphKind =
        typeof entity.metadata?.graph_kind === 'string' ? entity.metadata.graph_kind : null;

      if (entityId && graphKind === 'entity' && canonicalId === entityId) {
        return entity;
      }
      if (evidenceId && graphKind === 'evidence' && canonicalId === evidenceId) {
        return entity;
      }
    }
  }

  return null;
}

export function findAttackPathSelection(
  paths: AttackPath[],
  focus: { entityId?: string | null; evidenceId?: string | null }
) {
  const entityId = focus.entityId || null;
  const evidenceId = focus.evidenceId || null;

  for (const path of paths) {
    for (const entity of path.entities) {
      const canonicalId =
        typeof entity.metadata?.canonical_id === 'string' ? entity.metadata.canonical_id : null;
      const graphKind =
        typeof entity.metadata?.graph_kind === 'string' ? entity.metadata.graph_kind : null;

      if (entityId && graphKind === 'entity' && canonicalId === entityId) {
        return {
          pathId: path.id,
          entity,
        };
      }
      if (evidenceId && graphKind === 'evidence' && canonicalId === evidenceId) {
        return {
          pathId: path.id,
          entity,
        };
      }
    }
  }

  return null;
}
