'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { MatchedResponsePack } from '@/lib/playbooks/responsePacks';

interface ResponsePackPanelProps {
  title?: string;
  description?: string;
  packs: MatchedResponsePack[];
  emptyState?: string;
  onRunPlaybook?: (playbookId: string, pack: MatchedResponsePack) => void;
  runningPlaybookId?: string | null;
  maxItems?: number;
}

const domainTone: Record<string, string> = {
  identity: 'border-sky-500/30 bg-sky-500/10 text-sky-200',
  endpoint: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  cloud: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-200',
  application: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  ai: 'border-fuchsia-500/30 bg-fuchsia-500/10 text-fuchsia-200',
  security: 'border-slate-500/30 bg-slate-500/10 text-slate-200',
};

function formatDomainLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export default function ResponsePackPanel({
  title = 'Saved response packs',
  description = 'Curated SMB response packs that bundle the right playbooks, ownership expectations, and first moves for common attack patterns.',
  packs,
  emptyState = 'No saved response pack matches this story yet. The operator can still use the full playbook library.',
  onRunPlaybook,
  runningPlaybookId,
  maxItems = 2,
}: ResponsePackPanelProps) {
  const items = packs.slice(0, maxItems);

  return (
    <div className="rounded-xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-main">{title}</h2>
          <p className="mt-1 max-w-3xl text-sm text-text-muted">{description}</p>
        </div>
        <Link
          href="/dashboard/playbooks"
          className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
        >
          Open playbook library
        </Link>
      </div>

      {items.length === 0 ? (
        <div className="mt-5 rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5 text-sm text-text-muted">
          {emptyState}
        </div>
      ) : (
        <div className="mt-5 space-y-4">
          {items.map((match) => {
            const { pack, playbooks, primaryPlaybook } = match;
            return (
              <div
                key={pack.id}
                className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-5"
              >
                <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
                        Response pack
                      </span>
                      {pack.storyDomains.map((domain) => (
                        <span
                          key={`${pack.id}-${domain}`}
                          className={clsx(
                            'rounded-full border px-2.5 py-1 text-[11px]',
                            domainTone[domain] || domainTone.security
                          )}
                        >
                          {formatDomainLabel(domain)}
                        </span>
                      ))}
                    </div>

                    <h3 className="mt-3 text-lg font-semibold text-text-main">{pack.label}</h3>
                    <p className="mt-2 text-sm text-text-main">{pack.summary}</p>
                    <p className="mt-2 text-sm text-text-muted">{pack.operatorGoal}</p>

                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                        Owner: {pack.recommendedOwner}
                      </span>
                      <span className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted">
                        SLA: {pack.recommendedSla}
                      </span>
                      {match.reasons.map((reason) => (
                        <span
                          key={`${pack.id}-${reason}`}
                          className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-200"
                        >
                          Matched: {reason}
                        </span>
                      ))}
                    </div>

                    <div className="mt-4 grid gap-4 lg:grid-cols-2">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">First moves</p>
                        <ul className="mt-2 space-y-2 text-sm text-text-main">
                          {pack.firstMoves.map((step) => (
                            <li key={step} className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-2">
                              {step}
                            </li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Success checks</p>
                        <ul className="mt-2 space-y-2 text-sm text-text-main">
                          {pack.successChecks.map((step) => (
                            <li key={step} className="rounded-lg border border-[rgba(148,163,184,0.12)] px-3 py-2">
                              {step}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    <div className="mt-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Included playbooks</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {playbooks.length > 0 ? (
                          playbooks.map((playbook) => (
                            <Link
                              key={playbook.id}
                              href={`/dashboard/playbooks/${playbook.id}/edit`}
                              className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-main hover:border-primary/40"
                            >
                              {playbook.name}
                            </Link>
                          ))
                        ) : (
                          pack.playbookKeys.map((token) => (
                            <span
                              key={token}
                              className="rounded-full border border-[rgba(148,163,184,0.18)] px-2.5 py-1 text-[11px] text-text-muted"
                            >
                              {token}
                            </span>
                          ))
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col gap-2 xl:min-w-[220px]">
                    {primaryPlaybook && onRunPlaybook && (
                      <button
                        type="button"
                        onClick={() => onRunPlaybook(primaryPlaybook.id, match)}
                        disabled={runningPlaybookId === primaryPlaybook.id}
                        className="inline-flex min-h-[42px] items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-slate-950 hover:brightness-110 disabled:opacity-60"
                      >
                        {runningPlaybookId === primaryPlaybook.id ? 'Running playbook...' : 'Run primary playbook'}
                      </button>
                    )}
                    <Link
                      href={`/dashboard/playbooks?pack=${encodeURIComponent(pack.id)}`}
                      className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                    >
                      View pack playbooks
                    </Link>
                    <Link
                      href={pack.operatorRoute}
                      className="inline-flex min-h-[42px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                    >
                      {pack.operatorRouteLabel}
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
