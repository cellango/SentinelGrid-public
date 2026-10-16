'use client';

import clsx from 'clsx';
import {
  type CanonicalStoryDomain,
  type CanonicalStorySummary,
  formatStoryDomainLabel,
} from '@/lib/security/story';

interface StorySummaryInlineProps {
  summary?: CanonicalStorySummary;
  domains?: CanonicalStoryDomain[];
  className?: string;
}

export default function StorySummaryInline({
  summary,
  domains = [],
  className,
}: StorySummaryInlineProps) {
  const visibleDomains = (summary?.domains || domains || []).slice(0, 3);

  if (!summary && visibleDomains.length === 0) {
    return null;
  }

  return (
    <div className={clsx('space-y-2', className)}>
      {visibleDomains.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {visibleDomains.map((domain) => (
            <span
              key={domain}
              className="rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em] text-primary"
            >
              {formatStoryDomainLabel(domain)}
            </span>
          ))}
        </div>
      )}
      {summary?.detail && (
        <p className="text-xs text-text-muted">
          {summary.detail}
        </p>
      )}
    </div>
  );
}
