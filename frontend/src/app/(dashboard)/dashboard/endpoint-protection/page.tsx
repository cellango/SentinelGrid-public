'use client';

import Link from 'next/link';
import {
  ArrowDownTrayIcon,
  BoltIcon,
  ComputerDesktopIcon,
  RocketLaunchIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

const coveragePillars = [
  {
    title: 'Collect',
    description: 'Deploy hardened images or install SentinelGuard on new and existing workloads.',
    icon: ArrowDownTrayIcon,
  },
  {
    title: 'Detect',
    description: 'Stream endpoint telemetry into detections, posture scoring, and incident timelines.',
    icon: ComputerDesktopIcon,
  },
  {
    title: 'Respond',
    description: 'Turn endpoint findings into guided playbooks and fast analyst actions.',
    icon: BoltIcon,
  },
];

const installPaths = [
  'Use hardened images when you are spinning up net-new cloud workloads.',
  'Use the SentinelGuard installer when you need to retrofit existing servers or workstations.',
  'Route endpoint telemetry into detections and incidents so the SOC view stays consistent.',
];

export default function EndpointProtectionPage() {
  return (
    <div className="p-6 space-y-6 text-text-main">
      <section className="rounded-2xl border border-border-muted bg-surface-card p-6 lg:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-primary">
              <ShieldCheckIcon className="h-4 w-4" />
              Endpoint Coverage
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">Endpoint protection without a dead-end workflow</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
                SentinelGrid uses SentinelGuard for endpoint collection and ties that telemetry into detections,
                posture, and guided response. This page is the landing point for hardened images, install steps,
                and the analyst workflows they feed.
              </p>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Link
              href="#install"
              className="inline-flex items-center justify-center rounded-xl border border-primary/40 bg-primary/15 px-4 py-3 text-sm font-medium text-primary transition-colors hover:bg-primary/20"
            >
              Install SentinelGuard
            </Link>
            <Link
              href="#images"
              className="inline-flex items-center justify-center rounded-xl border border-border-muted px-4 py-3 text-sm font-medium text-text-main transition-colors hover:border-primary/40"
            >
              Browse Hardened Images
            </Link>
            <Link
              href="/dashboard/siem/detection-rules"
              className="inline-flex items-center justify-center rounded-xl border border-border-muted px-4 py-3 text-sm font-medium text-text-main transition-colors hover:border-primary/40"
            >
              View Detection Rules
            </Link>
            <Link
              href="/edr"
              className="inline-flex items-center justify-center rounded-xl border border-border-muted px-4 py-3 text-sm font-medium text-text-main transition-colors hover:border-primary/40"
            >
              Product Overview
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {coveragePillars.map((pillar) => {
          const Icon = pillar.icon;

          return (
            <div key={pillar.title} className="rounded-2xl border border-border-muted bg-surface-card p-5">
              <div className="mb-4 inline-flex rounded-xl border border-primary/30 bg-primary/10 p-3 text-primary">
                <Icon className="h-6 w-6" />
              </div>
              <h2 className="text-lg font-semibold">{pillar.title}</h2>
              <p className="mt-2 text-sm leading-6 text-text-muted">{pillar.description}</p>
            </div>
          );
        })}
      </section>

      <section id="images" className="rounded-2xl border border-border-muted bg-surface-card p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-xl font-semibold">Hardened images</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
              Use pre-hardened images for AWS, Azure, and GCP when you want fast rollout and a consistent baseline.
              Keep this workflow focused on small and mid-sized teams that need speed more than endless tuning.
            </p>
          </div>
          <div className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            <RocketLaunchIcon className="h-5 w-5" />
            Recommended for net-new workloads
          </div>
        </div>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-border-muted bg-bg-alt/60 p-4">
            <h3 className="text-sm font-semibold text-text-main">AWS</h3>
            <p className="mt-2 text-sm text-text-muted">Golden AMIs with the agent preinstalled and baseline hardening applied.</p>
          </div>
          <div className="rounded-xl border border-border-muted bg-bg-alt/60 p-4">
            <h3 className="text-sm font-semibold text-text-main">Azure</h3>
            <p className="mt-2 text-sm text-text-muted">Managed image path for standard VM builds and faster environment rollout.</p>
          </div>
          <div className="rounded-xl border border-border-muted bg-bg-alt/60 p-4">
            <h3 className="text-sm font-semibold text-text-main">GCP</h3>
            <p className="mt-2 text-sm text-text-muted">Image-based deployment for teams standardizing on instance templates.</p>
          </div>
        </div>
      </section>

      <section id="install" className="rounded-2xl border border-border-muted bg-surface-card p-6">
        <h2 className="text-xl font-semibold">Install paths</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
          Endpoint coverage should feel operational, not aspirational. Start with one of the supported rollout paths
          below and bring telemetry into the main dashboard immediately.
        </p>
        <div className="mt-5 grid gap-3">
          {installPaths.map((step, index) => (
            <div key={step} className="flex gap-3 rounded-xl border border-border-muted bg-bg-alt/60 p-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-sm font-semibold text-primary">
                {index + 1}
              </div>
              <p className="text-sm leading-6 text-text-main">{step}</p>
            </div>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link
            href="/dashboard/scans"
            className="inline-flex items-center justify-center rounded-xl border border-border-muted px-4 py-3 text-sm font-medium text-text-main transition-colors hover:border-primary/40"
          >
            Open Scans
          </Link>
          <Link
            href="/dashboard/incidents"
            className="inline-flex items-center justify-center rounded-xl border border-border-muted px-4 py-3 text-sm font-medium text-text-main transition-colors hover:border-primary/40"
          >
            Open Incidents
          </Link>
          <Link
            href="/dashboard/siem"
            className="inline-flex items-center justify-center rounded-xl border border-primary/40 bg-primary/15 px-4 py-3 text-sm font-medium text-primary transition-colors hover:bg-primary/20"
          >
            Open Detections &amp; Response
          </Link>
        </div>
      </section>
    </div>
  );
}
