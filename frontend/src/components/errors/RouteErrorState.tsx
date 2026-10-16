'use client';

import { useEffect } from 'react';
import Link from 'next/link';

interface RouteErrorStateProps {
  title: string;
  description: string;
  reset: () => void;
  backHref: string;
  backLabel: string;
}

export default function RouteErrorState({
  title,
  description,
  reset,
  backHref,
  backLabel,
}: RouteErrorStateProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-10">
      <div className="w-full max-w-xl rounded-2xl border border-rose-500/20 bg-surface-card p-8 shadow-xl">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-rose-300">
          Route error
        </p>
        <h1 className="mt-3 text-2xl font-semibold text-text-main">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-text-muted">{description}</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={reset}
            className="inline-flex min-h-[44px] items-center rounded-xl bg-primary px-4 py-2 text-sm font-medium text-slate-950 transition-all hover:brightness-110"
          >
            Retry
          </button>
          <Link
            href={backHref}
            className="inline-flex min-h-[44px] items-center rounded-xl border border-border-strong px-4 py-2 text-sm text-text-main transition-colors hover:border-primary"
          >
            {backLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}
