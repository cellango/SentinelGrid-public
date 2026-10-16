'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { Playbook } from '@/lib/api/playbooks';
import { RESPONSE_PACKS, getResponsePackPlaybooks } from '@/lib/playbooks/responsePacks';

interface ResponsePackLibrarySectionProps {
  playbooks?: Playbook[];
  selectedPackId?: string | null;
  onSelectPack: (packId: string | null) => void;
}

export default function ResponsePackLibrarySection({
  playbooks = [],
  selectedPackId = null,
  onSelectPack,
}: ResponsePackLibrarySectionProps) {
  return (
    <div className="rounded-xl border border-surface-card-border bg-surface-card p-6 dark:border-surface-card-border dark:bg-surface-card">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Saved response packs</p>
          <h2 className="mt-1 text-xl font-semibold text-text-main">Common SMB attack patterns</h2>
          <p className="mt-2 max-w-3xl text-sm text-text-muted dark:text-text-muted">
            Curated pack definitions group the built-in playbooks that operators need most often, along with the owner and timing expectations for the response.
          </p>
        </div>
        {selectedPackId && (
          <button
            type="button"
            onClick={() => onSelectPack(null)}
            className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:bg-surface-hover dark:border-border dark:text-text-main dark:hover:bg-surface-hover"
          >
            Clear pack filter
          </button>
        )}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {RESPONSE_PACKS.map((pack) => {
          const matchedPlaybooks = getResponsePackPlaybooks(pack.id, playbooks);
          const active = selectedPackId === pack.id;

          return (
            <div
              key={pack.id}
              className={clsx(
                'rounded-xl border p-5 transition-colors',
                active
                  ? 'border-primary bg-primary/10'
                  : 'border-surface-card-border bg-[rgba(15,23,42,0.03)] dark:border-surface-card-border dark:bg-[rgba(15,23,42,0.45)]'
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-text-main">{pack.label}</h3>
                  <p className="mt-2 text-sm text-text-muted dark:text-text-muted">{pack.summary}</p>
                </div>
                {matchedPlaybooks.length > 0 && (
                  <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-[11px] text-primary">
                    {matchedPlaybooks.length} playbook{matchedPlaybooks.length === 1 ? '' : 's'}
                  </span>
                )}
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-text-muted dark:border-border dark:text-text-muted">
                  Owner: {pack.recommendedOwner}
                </span>
                <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-text-muted dark:border-border dark:text-text-muted">
                  SLA: {pack.recommendedSla}
                </span>
              </div>

              <p className="mt-3 text-sm text-text-muted dark:text-text-muted">{pack.operatorGoal}</p>

              <div className="mt-4">
                <p className="text-xs uppercase tracking-[0.14em] text-text-muted dark:text-text-muted">Playbook coverage</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {(matchedPlaybooks.length > 0 ? matchedPlaybooks.map((playbook) => playbook.name) : pack.playbookKeys).slice(0, 4).map((label) => (
                    <span
                      key={`${pack.id}-${label}`}
                      className="rounded-full border border-border px-2.5 py-1 text-[11px] text-text-muted dark:border-border dark:text-text-muted"
                    >
                      {label}
                    </span>
                  ))}
                  {(matchedPlaybooks.length > 4 || pack.playbookKeys.length > 4) && (
                    <span className="rounded-full border border-border px-2.5 py-1 text-[11px] text-text-muted dark:border-border dark:text-text-muted">
                      + more
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => onSelectPack(active ? null : pack.id)}
                  className={clsx(
                    'inline-flex min-h-[40px] items-center justify-center rounded-lg px-4 py-2 text-sm font-medium',
                    active
                      ? 'bg-primary text-slate-950'
                      : 'border border-border text-text-muted hover:bg-surface-hover dark:border-border dark:text-text-main dark:hover:bg-surface-hover'
                  )}
                >
                  {active ? 'Pack filter active' : 'Filter playbooks'}
                </button>
                <Link
                  href={pack.operatorRoute}
                  className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-border px-4 py-2 text-sm text-text-muted hover:bg-surface-hover dark:border-border dark:text-text-main dark:hover:bg-surface-hover"
                >
                  {pack.operatorRouteLabel}
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
