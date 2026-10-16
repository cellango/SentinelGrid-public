import Link from 'next/link';
import type { ComplianceFrameworkStarterPack } from '@/lib/api/compliance';
import { TRUST_ARTIFACTS } from '@/lib/trustArtifacts';

const ARTIFACT_LABELS = TRUST_ARTIFACTS.reduce<Record<string, string>>((accumulator, artifact) => {
  accumulator[artifact.templateKey] = artifact.title;
  return accumulator;
}, {});

function launchStateClasses(value: ComplianceFrameworkStarterPack['launch_state']) {
  if (value === 'live') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }

  return 'border-amber-200 bg-amber-50 text-amber-700';
}

function focusAreaClasses(value: ComplianceFrameworkStarterPack['focus_areas'][number]['status']) {
  if (value === 'ready') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  }
  if (value === 'needs_attention') {
    return 'border-rose-200 bg-rose-50 text-rose-700';
  }
  return 'border-slate-200 bg-slate-100 text-slate-600';
}

export function FrameworkStarterPacksPanel({
  starterPacks,
  multiFrameworkEnabled = false,
}: {
  starterPacks: ComplianceFrameworkStarterPack[];
  multiFrameworkEnabled?: boolean;
}) {
  if (starterPacks.length === 0) {
    return null;
  }

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold text-text-main">Framework Starter Packs</h2>
          <p className="text-text-muted mt-1">
            Use curated SOC 2 and ISO 27001 packs to turn the current trust-evidence layer into concrete audit and customer-review workflows.
          </p>
          {!multiFrameworkEnabled ? (
            <p className="mt-2 text-sm text-text-muted">
              Framework picker rollout is disabled in this runtime; starter packs do not activate full multi-framework control tracking.
            </p>
          ) : null}
        </div>
        <Link
          href="/dashboard/compliance/reports#questionnaire-assist"
          className="inline-flex items-center px-4 py-2 bg-bg-alt text-text-muted rounded-lg hover:bg-surface-hover text-sm font-medium"
        >
          Open questionnaire assist
        </Link>
      </div>

      <div className="mt-6 grid grid-cols-1 xl:grid-cols-2 gap-6">
        {starterPacks.map((pack) => (
          <div key={pack.framework_key} className="rounded-2xl border border-surface-card-border bg-surface-card p-6 shadow">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-text-muted">Framework starter pack</p>
                <h3 className="mt-2 text-2xl font-semibold text-text-main">{pack.framework_name}</h3>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${launchStateClasses(pack.launch_state)}`}>
                {pack.launch_state === 'live' ? 'live pack' : 'starter pack'}
              </span>
            </div>

            <p className="mt-4 text-sm leading-6 text-text-muted">{pack.summary}</p>
            <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
              {pack.note}
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-surface-card-border bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">{pack.score_label}</p>
                <p className="mt-2 text-3xl font-bold text-text-main">{pack.score}/100</p>
              </div>
              <div className="rounded-xl border border-surface-card-border bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">Criteria ready</p>
                <p className="mt-2 text-3xl font-bold text-text-main">{pack.metrics.criteria_ready}</p>
              </div>
              <div className="rounded-xl border border-surface-card-border bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">Needs attention</p>
                <p className="mt-2 text-3xl font-bold text-text-main">{pack.metrics.criteria_needing_attention}</p>
              </div>
              <div className="rounded-xl border border-surface-card-border bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-wide text-text-muted">Evidence items</p>
                <p className="mt-2 text-3xl font-bold text-text-main">{pack.metrics.evidence_items}</p>
              </div>
            </div>

            <div className="mt-5">
              <p className="text-xs uppercase tracking-wide text-text-muted">Focus areas</p>
              <div className="mt-3 space-y-3">
                {pack.focus_areas.map((area) => (
                  <div key={area.key} className="rounded-xl border border-surface-card-border p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-text-main">{area.title}</p>
                        <p className="mt-1 text-sm text-text-muted">{area.description}</p>
                      </div>
                      <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${focusAreaClasses(area.status)}`}>
                        {area.status.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-text-muted">{area.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <p className="text-xs uppercase tracking-wide text-text-muted">Suggested artifacts</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {pack.artifact_template_keys.map((templateKey) => (
                  <span
                    key={templateKey}
                    className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm text-blue-700"
                  >
                    {ARTIFACT_LABELS[templateKey] || templateKey}
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-5">
              <p className="text-xs uppercase tracking-wide text-text-muted">Quick actions</p>
              <div className="mt-3 grid gap-3">
                {pack.quick_actions.map((action) => (
                  <Link
                    key={`${pack.framework_key}-${action.title}`}
                    href={action.href}
                    className="rounded-xl border border-surface-card-border px-4 py-3 hover:bg-slate-50 transition-colors"
                  >
                    <p className="text-sm font-semibold text-text-main">{action.title}</p>
                    <p className="mt-1 text-sm text-text-muted">{action.description}</p>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
