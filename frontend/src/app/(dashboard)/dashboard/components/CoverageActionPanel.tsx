'use client';

import Link from 'next/link';
import clsx from 'clsx';
import type { PostureScore } from '@/lib/api/dashboard';
import type { SourceHealth } from '@/lib/api/siem';

interface CoverageActionPanelProps {
  postureScore?: PostureScore;
  sourceHealth?: SourceHealth;
}

type CoverageActionItem = {
  id: string;
  title: string;
  description: string;
  actionLabel: string;
  href: string;
  statusLabel: string;
  tone: 'critical' | 'warning' | 'healthy';
  score: number;
};

const DOMAIN_CONFIG: Record<
  string,
  { label: string; href: string; connectLabel: string; expandLabel: string }
> = {
  identity: {
    label: 'Identity coverage',
    href: '/dashboard/iam/identity-providers',
    connectLabel: 'Connect identity data',
    expandLabel: 'Review identity gaps',
  },
  cloud: {
    label: 'Cloud coverage',
    href: '/dashboard/posture',
    connectLabel: 'Connect cloud accounts',
    expandLabel: 'Review cloud posture',
  },
  endpoint: {
    label: 'Endpoint coverage',
    href: '/dashboard/endpoint-protection',
    connectLabel: 'Roll out endpoint telemetry',
    expandLabel: 'Finish endpoint rollout',
  },
  app: {
    label: 'Application and AI coverage',
    href: '/dashboard/compliance/ai-activity',
    connectLabel: 'Connect app and AI telemetry',
    expandLabel: 'Review app and AI exposure',
  },
};

const HEALTH_CONFIG: Record<
  string,
  { label: string; href: string; actionLabel: string }
> = {
  ingestion_service: {
    label: 'Ingestion pipeline',
    href: '/dashboard/siem',
    actionLabel: 'Check ingestion',
  },
  siem_agent: {
    label: 'SIEM agent',
    href: '/dashboard/siem',
    actionLabel: 'Review SIEM agent',
  },
  opensearch: {
    label: 'Search backend',
    href: '/dashboard/siem',
    actionLabel: 'Inspect search health',
  },
  wazuh: {
    label: 'Baseline sensor',
    href: '/dashboard/endpoint-protection',
    actionLabel: 'Review baseline sensor',
  },
  openedr: {
    label: 'Behavioral telemetry',
    href: '/dashboard/endpoint-protection',
    actionLabel: 'Review behavioral telemetry',
  },
  velociraptor: {
    label: 'Hunt and collection sensor',
    href: '/dashboard/endpoint-protection',
    actionLabel: 'Review hunt coverage',
  },
};

function toneClasses(tone: CoverageActionItem['tone']) {
  switch (tone) {
    case 'critical':
      return 'border-rose-500/40 bg-rose-500/15 text-rose-200';
    case 'warning':
      return 'border-amber-500/40 bg-amber-500/15 text-amber-200';
    default:
      return 'border-emerald-500/40 bg-emerald-500/15 text-emerald-200';
  }
}

function normalizeHealthTone(status?: string | null): CoverageActionItem['tone'] {
  const value = (status || '').toLowerCase();
  if (!value || value === 'healthy' || value === 'ok' || value === 'online' || value === 'up' || value === 'connected') {
    return 'healthy';
  }
  if (
    value.includes('critical') ||
    value.includes('down') ||
    value.includes('error') ||
    value.includes('offline') ||
    value.includes('disconnected')
  ) {
    return 'critical';
  }
  return 'warning';
}

function buildCoverageItems(
  postureScore?: PostureScore,
  sourceHealth?: SourceHealth
): CoverageActionItem[] {
  const items: CoverageActionItem[] = [];

  for (const [domain, config] of Object.entries(DOMAIN_CONFIG)) {
    const coverage = postureScore?.coverage_details?.[domain];
    const scanned = Number(coverage?.scanned ?? 0);
    const total = Number(coverage?.total ?? 0);
    const pct = total > 0 ? Math.round((scanned / total) * 100) : 0;

    if (total === 0) {
      items.push({
        id: `${domain}-connect`,
        title: `Connect ${config.label.toLowerCase()}`,
        description: `SentinelGrid is not receiving ${config.label.toLowerCase()} yet, so cross-domain prioritization for this area is still thin.`,
        actionLabel: config.connectLabel,
        href: config.href,
        statusLabel: 'Not connected',
        tone: 'critical',
        score: 100,
      });
      continue;
    }

    if (pct < 60) {
      items.push({
        id: `${domain}-expand`,
        title: `Expand ${config.label.toLowerCase()}`,
        description: `${scanned} of ${total} tracked items are currently covered. Raise this before relying on the queue to represent the full risk picture.`,
        actionLabel: config.expandLabel,
        href: config.href,
        statusLabel: `${pct}% covered`,
        tone: 'critical',
        score: 90 - pct,
      });
      continue;
    }

    if (pct < 85) {
      items.push({
        id: `${domain}-tighten`,
        title: `Tighten ${config.label.toLowerCase()}`,
        description: `${scanned} of ${total} tracked items are covered. There is still enough blind spot here to affect prioritization quality.`,
        actionLabel: config.expandLabel,
        href: config.href,
        statusLabel: `${pct}% covered`,
        tone: 'warning',
        score: 70 - pct,
      });
    }
  }

  for (const [key, config] of Object.entries(HEALTH_CONFIG)) {
    const status = sourceHealth?.[key as keyof SourceHealth];
    const tone = normalizeHealthTone(status);
    if (!status || tone === 'healthy') continue;
    items.push({
      id: `${key}-health`,
      title: `${config.label} needs attention`,
      description: `Current status is ${status}. Stabilize this path so findings and evidence stay fresh enough for operator decisions.`,
      actionLabel: config.actionLabel,
      href: config.href,
      statusLabel: status,
      tone,
      score: tone === 'critical' ? 95 : 65,
    });
  }

  return items.sort((left, right) => right.score - left.score).slice(0, 4);
}

export default function CoverageActionPanel({
  postureScore,
  sourceHealth,
}: CoverageActionPanelProps) {
  const items = buildCoverageItems(postureScore, sourceHealth);

  return (
    <div className="rounded-2xl border border-surface-card-border bg-surface-card p-6">
      <div className="flex flex-col gap-2">
        <p className="text-[11px] uppercase tracking-[0.2em] text-primary">Coverage</p>
        <h2 className="text-xl font-semibold text-text-main">Close the next blind spots</h2>
        <p className="text-sm text-text-muted">
          Fix the data and sensor gaps that most directly affect queue quality and operator confidence.
        </p>
      </div>

      <div className="mt-6 space-y-3">
        {items.length === 0 ? (
          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4">
            <p className="text-sm font-semibold text-emerald-100">Coverage looks healthy.</p>
            <p className="mt-1 text-sm text-emerald-50/80">
              Current telemetry and service health do not show a major blind spot on the active domains.
            </p>
            <Link
              href="/dashboard/posture"
              className="mt-4 inline-flex min-h-[40px] items-center justify-center rounded-lg border border-emerald-400/30 px-4 py-2 text-sm text-emerald-100 hover:border-emerald-300/50"
            >
              Review posture
            </Link>
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-[rgba(148,163,184,0.14)] bg-[rgba(15,23,42,0.45)] p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={clsx(
                        'rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]',
                        toneClasses(item.tone)
                      )}
                    >
                      {item.statusLabel}
                    </span>
                  </div>
                  <h3 className="mt-3 text-base font-semibold text-text-main">{item.title}</h3>
                  <p className="mt-2 text-sm text-text-muted">{item.description}</p>
                </div>
                <Link
                  href={item.href}
                  className="inline-flex min-h-[40px] items-center justify-center rounded-lg border border-[rgba(148,163,184,0.18)] px-4 py-2 text-sm text-text-main hover:border-primary/40"
                >
                  {item.actionLabel}
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
