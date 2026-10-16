'use client';

import { useEffect, useState } from 'react';
import {
  type OnboardingMetrics,
  readOnboardingMetrics,
} from '@/lib/onboarding/metrics';

function formatDuration(start?: string, end?: string) {
  if (!start || !end) return null;

  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (Number.isNaN(ms) || ms < 0) return null;

  const totalMinutes = Math.round(ms / 60000);
  if (totalMinutes < 60) {
    return `${totalMinutes}m`;
  }

  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
}

function formatTimestamp(value?: string) {
  if (!value) return 'Pending';
  return new Date(value).toLocaleString();
}

export default function ActivationMetricsPanel() {
  const [metrics, setMetrics] = useState<OnboardingMetrics | null>(null);

  useEffect(() => {
    const sync = () => setMetrics(readOnboardingMetrics());
    sync();

    window.addEventListener('sentinelgrid:onboarding-metrics-updated', sync as EventListener);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('sentinelgrid:onboarding-metrics-updated', sync as EventListener);
      window.removeEventListener('storage', sync);
    };
  }, []);

  const baseline =
    metrics?.signupStartedAt ||
    metrics?.paymentSucceededAt ||
    metrics?.onboardingStartedAt;

  const metricCards = [
    {
      label: 'Setup started',
      value: formatTimestamp(baseline),
      detail: metrics?.planTier ? `Plan: ${metrics.planTier}` : 'Awaiting first checkpoint',
    },
    {
      label: 'First connector',
      value: metrics?.firstConnectorConnectedAt
        ? formatDuration(baseline, metrics.firstConnectorConnectedAt) || 'Ready'
        : 'Pending',
      detail: metrics?.firstConnectorConnectedAt
        ? formatTimestamp(metrics.firstConnectorConnectedAt)
        : 'Happens after identity or cloud is connected',
    },
    {
      label: 'Core connectors',
      value: metrics?.coreConnectorsReadyAt
        ? formatDuration(baseline, metrics.coreConnectorsReadyAt) || 'Ready'
        : 'Pending',
      detail: metrics?.coreConnectorsReadyAt
        ? formatTimestamp(metrics.coreConnectorsReadyAt)
        : 'Primary identity + AWS',
    },
    {
      label: 'First value',
      value: metrics?.firstValueReadyAt
        ? formatDuration(baseline, metrics.firstValueReadyAt) || 'Ready'
        : 'Pending',
      detail: metrics?.firstValueReadyAt
        ? formatTimestamp(metrics.firstValueReadyAt)
        : 'First findings or quick wins not recorded yet',
    },
  ];

  return (
    <section className="mb-8 rounded-2xl border border-primary/20 bg-[rgba(15,23,42,0.9)] p-6 backdrop-blur-md">
      <div className="mb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">
          Activation metrics
        </p>
        <h2 className="mt-2 text-2xl font-semibold text-text-main">
          Time-to-value checkpoints
        </h2>
        <p className="mt-2 text-sm text-text-muted">
          These milestones make onboarding measurable: from signup, to first connector, to core coverage, to visible findings.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" aria-live="polite" aria-atomic="true">
        {metricCards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-primary/10 bg-slate-950/50 p-4"
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-primary">
              {card.label}
            </p>
            <p className="mt-3 text-2xl font-semibold text-text-main">{card.value}</p>
            <p className="mt-2 text-sm leading-6 text-text-muted">{card.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
