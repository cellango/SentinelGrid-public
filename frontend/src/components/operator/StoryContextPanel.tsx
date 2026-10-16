'use client';

import Link from 'next/link';
import {
  type CanonicalEntityRef,
  type CanonicalEvidenceRef,
  formatStoryDomainLabel,
  formatStoryEntityTypeLabel,
  formatStoryEvidenceTypeLabel,
} from '@/lib/security/story';

interface StoryContextPanelProps {
  title?: string;
  description?: string;
  domains?: string[];
  entities?: CanonicalEntityRef[];
  evidence?: CanonicalEvidenceRef[];
  emptyEntityText?: string;
  emptyEvidenceText?: string;
  graphHref?: string | null;
  getEntityGraphHref?: (entity: CanonicalEntityRef) => string | null;
  getEvidenceGraphHref?: (evidence: CanonicalEvidenceRef) => string | null;
}

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

export default function StoryContextPanel({
  title = 'Story context',
  description = 'Canonical entities and evidence linked to this security story.',
  domains = [],
  entities = [],
  evidence = [],
  emptyEntityText = 'No linked entities yet.',
  emptyEvidenceText = 'No linked evidence yet.',
  graphHref = null,
  getEntityGraphHref,
  getEvidenceGraphHref,
}: StoryContextPanelProps) {
  return (
    <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-text-main">{title}</h2>
          <p className="mt-1 text-sm text-text-muted">{description}</p>
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {graphHref && (
            <Link
              href={graphHref}
              className="inline-flex min-h-[36px] items-center justify-center rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-primary hover:border-primary/50"
            >
              Open story graph
            </Link>
          )}
          {domains.length > 0 &&
            domains.map((domain) => (
              <span
                key={domain}
                className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-primary"
              >
                {formatStoryDomainLabel(domain)}
              </span>
            ))}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-main">Entities</h3>
            <span className="text-xs text-text-muted">{entities.length}</span>
          </div>
          {entities.length > 0 ? (
            <div className="space-y-3">
              {entities.map((entity) => (
                <div key={`${entity.type}-${entity.id}`} className="rounded-lg border border-[rgba(148,163,184,0.1)] px-3 py-2">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.12em] text-text-muted">
                        {formatStoryEntityTypeLabel(entity.type)}
                      </div>
                      <StoryLink
                        href={entity.href}
                        label={entity.label}
                        className="mt-1 block text-sm font-medium text-text-main hover:text-primary"
                      />
                      <div className="mt-1 text-[11px] text-text-muted">{entity.id}</div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {entity.role && (
                        <span className="rounded-full bg-[rgba(148,163,184,0.12)] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-text-muted">
                          {entity.role.replace(/_/g, ' ')}
                        </span>
                      )}
                      {getEntityGraphHref?.(entity) && (
                        <Link
                          href={getEntityGraphHref(entity)!}
                          className="rounded-full border border-primary/25 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-primary hover:border-primary/50"
                        >
                          Graph
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">{emptyEntityText}</p>
          )}
        </div>

        <div className="rounded-xl border border-[rgba(148,163,184,0.12)] bg-[rgba(15,23,42,0.45)] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-main">Evidence</h3>
            <span className="text-xs text-text-muted">{evidence.length}</span>
          </div>
          {evidence.length > 0 ? (
            <div className="space-y-3">
              {evidence.map((item) => (
                <div key={`${item.type}-${item.id}`} className="rounded-lg border border-[rgba(148,163,184,0.1)] px-3 py-2">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs uppercase tracking-[0.12em] text-text-muted">
                        {formatStoryEvidenceTypeLabel(item.type)}
                      </div>
                      <StoryLink
                        href={item.href}
                        label={item.title}
                        className="mt-1 block text-sm font-medium text-text-main hover:text-primary"
                      />
                      <div className="mt-1 text-[11px] text-text-muted">{item.id}</div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      {item.severity && (
                        <span className="rounded-full bg-red-500/15 px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-red-200">
                          {item.severity}
                        </span>
                      )}
                      {item.source && (
                        <span className="rounded-full bg-[rgba(148,163,184,0.12)] px-2 py-0.5 text-[10px] uppercase tracking-[0.12em] text-text-muted">
                          {item.source}
                        </span>
                      )}
                      {getEvidenceGraphHref?.(item) && (
                        <Link
                          href={getEvidenceGraphHref(item)!}
                          className="rounded-full border border-primary/25 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-primary hover:border-primary/50"
                        >
                          Graph
                        </Link>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">{emptyEvidenceText}</p>
          )}
        </div>
      </div>
    </div>
  );
}
