'use client';

import Link from 'next/link';
import clsx from 'clsx';
import {
  type CanonicalEntityRef,
  type CanonicalEvidenceRef,
  formatStoryDomainLabel,
  formatStoryEntityTypeLabel,
  formatStoryEvidenceTypeLabel,
} from '@/lib/security/story';

interface CrossDomainRelationshipViewProps {
  title?: string;
  description?: string;
  domains?: string[];
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
}

type DomainBucket = {
  domain: string;
  entities: CanonicalEntityRef[];
  evidence: CanonicalEvidenceRef[];
};

function StoryLink({
  href,
  label,
  className,
}: {
  href?: string | null;
  label: string;
  className?: string;
}) {
  if (!href) {
    return <span className={className}>{label}</span>;
  }
  if (href.startsWith('http')) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={className}>
        {label}
      </a>
    );
  }
  return (
    <Link href={href} className={className}>
      {label}
    </Link>
  );
}

function uniqueDomains(domains: string[], entities: CanonicalEntityRef[], evidence: CanonicalEvidenceRef[]) {
  const ordered = [...domains];
  for (const entity of entities) {
    if (entity.domain && !ordered.includes(entity.domain)) {
      ordered.push(entity.domain);
    }
  }
  for (const item of evidence) {
    if (item.domain && !ordered.includes(item.domain)) {
      ordered.push(item.domain);
    }
  }
  return ordered.length > 0 ? ordered : ['security'];
}

function buildBuckets(
  domains: string[],
  entities: CanonicalEntityRef[],
  evidence: CanonicalEvidenceRef[]
): DomainBucket[] {
  return domains.map((domain) => ({
    domain,
    entities: entities.filter((entity) => entity.domain === domain),
    evidence: evidence.filter((item) => (item.domain || 'security') === domain),
  }));
}

function domainTone(domain: string) {
  switch (domain) {
    case 'identity':
      return 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200';
    case 'cloud':
      return 'border-amber-500/30 bg-amber-500/10 text-amber-200';
    case 'endpoint':
      return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200';
    case 'application':
      return 'border-violet-500/30 bg-violet-500/10 text-violet-200';
    case 'ai':
      return 'border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-200';
    default:
      return 'border-slate-500/30 bg-slate-500/10 text-slate-200';
  }
}

function buildPathSummary(primaryLabel: string, primaryDomain: string, otherDomain: string, evidenceCount: number) {
  if (primaryDomain === otherDomain) {
    return `${primaryLabel} is anchored in the ${formatStoryDomainLabel(primaryDomain).toLowerCase()} lane.`;
  }
  return `${primaryLabel} intersects with ${formatStoryDomainLabel(otherDomain).toLowerCase()} context through ${evidenceCount} linked evidence item${evidenceCount === 1 ? '' : 's'}.`;
}

export default function CrossDomainRelationshipView({
  title = 'Relationship view',
  description = 'See how this story connects identities, assets, cloud resources, AI apps, and evidence across domains.',
  domains = [],
  entities = [],
  evidence = [],
}: CrossDomainRelationshipViewProps) {
  const orderedDomains = uniqueDomains(domains, entities, evidence);
  const buckets = buildBuckets(orderedDomains, entities, evidence);
  const primaryEntity = entities[0];
  const bridgeDomains = orderedDomains.filter((domain) => domain !== (primaryEntity?.domain || orderedDomains[0]));

  return (
    <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-main">{title}</h2>
          <p className="mt-1 max-w-3xl text-sm text-text-muted">{description}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
            {orderedDomains.length} domain{orderedDomains.length === 1 ? '' : 's'}
          </span>
          <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
            {entities.length} entit{entities.length === 1 ? 'y' : 'ies'}
          </span>
          <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-text-muted">
            {evidence.length} evidence
          </span>
        </div>
      </div>

      {(primaryEntity || bridgeDomains.length > 0) && (
        <div className="mt-5 rounded-xl border border-primary/15 bg-primary/5 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
            Cross-domain paths
          </p>
          {primaryEntity ? (
            <p className="mt-2 text-sm text-text-main">
              <span className="font-medium">{primaryEntity.label}</span> is the main pivot for this story.
            </p>
          ) : (
            <p className="mt-2 text-sm text-text-main">
              This story spans multiple domains even though no primary entity has been normalized yet.
            </p>
          )}
          {bridgeDomains.length > 0 && (
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {bridgeDomains.map((domain) => {
                const bucket = buckets.find((item) => item.domain === domain);
                return (
                  <div
                    key={domain}
                    className="rounded-lg border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-3"
                  >
                    <p className="text-sm text-text-main">
                      {buildPathSummary(
                        primaryEntity?.label || formatStoryDomainLabel(orderedDomains[0]),
                        primaryEntity?.domain || orderedDomains[0],
                        domain,
                        bucket?.evidence.length || 0
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        {buckets.map((bucket) => (
          <div
            key={bucket.domain}
            className="rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(15,23,42,0.45)] p-4"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <span
                  className={clsx(
                    'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                    domainTone(bucket.domain)
                  )}
                >
                  {formatStoryDomainLabel(bucket.domain)}
                </span>
                <p className="mt-3 text-sm text-text-muted">
                  {bucket.entities.length} entit{bucket.entities.length === 1 ? 'y' : 'ies'} and{' '}
                  {bucket.evidence.length} evidence item{bucket.evidence.length === 1 ? '' : 's'}
                </p>
              </div>
            </div>

            <div className="mt-4 space-y-4">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Entity pivots
                </h3>
                {bucket.entities.length > 0 ? (
                  <div className="mt-2 space-y-2">
                    {bucket.entities.map((entity) => (
                      <div
                        key={`${bucket.domain}-entity-${entity.type}-${entity.id}`}
                        className="rounded-lg border border-[rgba(148,163,184,0.1)] px-3 py-2"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="text-[11px] uppercase tracking-[0.12em] text-text-muted">
                              {formatStoryEntityTypeLabel(entity.type)}
                            </div>
                            <StoryLink
                              href={entity.href}
                              label={entity.label}
                              className="mt-1 block truncate text-sm font-medium text-text-main hover:text-primary"
                            />
                            <div className="mt-1 text-[11px] text-text-muted">{entity.id}</div>
                          </div>
                          {entity.role && (
                            <span className="rounded-full bg-[rgba(148,163,184,0.12)] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-text-muted">
                              {entity.role.replace(/_/g, ' ')}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-text-muted">No normalized entity pivots in this lane yet.</p>
                )}
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
                  Evidence and workflows
                </h3>
                {bucket.evidence.length > 0 ? (
                  <div className="mt-2 space-y-2">
                    {bucket.evidence.map((item) => (
                      <div
                        key={`${bucket.domain}-evidence-${item.type}-${item.id}`}
                        className="rounded-lg border border-[rgba(148,163,184,0.1)] px-3 py-2"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="text-[11px] uppercase tracking-[0.12em] text-text-muted">
                              {formatStoryEvidenceTypeLabel(item.type)}
                            </div>
                            <StoryLink
                              href={item.href}
                              label={item.title}
                              className="mt-1 block truncate text-sm font-medium text-text-main hover:text-primary"
                            />
                            <div className="mt-1 text-[11px] text-text-muted">{item.id}</div>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            {item.severity && (
                              <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-red-200">
                                {item.severity}
                              </span>
                            )}
                            {item.status && (
                              <span className="rounded-full bg-[rgba(148,163,184,0.12)] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-text-muted">
                                {item.status.replace(/_/g, ' ')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-text-muted">No linked evidence in this lane yet.</p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
