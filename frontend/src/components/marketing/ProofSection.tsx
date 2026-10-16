import { TrackedLink } from "@/components/marketing/TrackedLink";
import {
  launchWorkflowSteps,
  type LaunchWorkflowStepId,
} from "@/lib/marketing/launchWorkflow";

const proofSignals = [
  {
    value: "3",
    label: "core inputs in the launch path",
    detail:
      "Identity, cloud, and qualified endpoint coverage feed the same operator queue before optional AI scope is added.",
  },
  {
    value: "1",
    label: "cross-domain queue instead of disconnected screens",
    detail:
      "Identity, cloud, endpoint, and optional AI context are grouped into the same operating record.",
  },
  {
    value: "1",
    label: "guided action pack tied to the same record",
    detail:
      "Containment, ownership, ticket handoff, and evidence all stay attached to the queue item.",
  },
];

const firstWeekArtifactDetails: Record<
  LaunchWorkflowStepId,
  {
    description: string;
    artifact: string;
  }
> = {
  identity: {
    description:
      "The first proof point is not a slide. It is a visible identity connection with sync state, sign-in context, and access hygiene checks online.",
    artifact:
      "Connector state, sync timestamps, risky sign-ins, stale MFA and access hygiene findings",
  },
  cloud: {
    description:
      "The next proof point is the cloud connection feeding posture and privileged access context into the same launch-safe operating plane.",
    artifact:
      "Cloud posture findings, exposed-resource context, privileged access checks, normalized metadata",
  },
  endpoint: {
    description:
      "If endpoint scope is part of the rollout, the proof point is qualified coverage in the same workflow rather than a separate parity claim.",
    artifact:
      "Pilot coverage state, heartbeat visibility, missing coverage alerts, same-queue routing",
  },
  queue: {
    description:
      "The queue proof is one correlated record: risky sign-in behavior, cloud exposure context, device state, ownership, and the recommended response pack in one place.",
    artifact:
      "Priority, correlated finding, impacted identity, cross-domain context, suggested response pack",
  },
  action: {
    description:
      "The operating proof ends with action. Buyers should see the same work item drive containment, ownership, reporting, and evidence without rebuilding the story elsewhere.",
    artifact:
      "Approved action, ticket handoff, weekly summary note, preserved evidence trail",
  },
};

const firstWeekArtifacts = launchWorkflowSteps.map((step) => ({
  ...step,
  ...firstWeekArtifactDetails[step.id],
}));

const evidenceInputs = [
  "Entra sign-in anomaly",
  "Privileged role assignment",
  "Endpoint heartbeat gap",
];

const evidenceActions = [
  "Revoke active session",
  "Enforce MFA reset",
  "Create owner-assigned follow-up ticket",
];

const summaryItems = [
  "1 high-priority cross-domain record assigned",
  "1 guided response pack approved",
  "Evidence ready for leadership update",
];

type ProofSectionProps = {
  ctaSource?: string;
  compact?: boolean;
  showProductCta?: boolean;
};

export function ProofSection({
  ctaSource = "homepage_proof",
  compact = false,
  showProductCta = true,
}: ProofSectionProps) {
  const sectionPadding = compact ? "py-14" : "py-20";

  return (
    <section className={`${sectionPadding} px-6 bg-bg-alt/20`}>
      <div className="max-w-7xl mx-auto">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Proof Path
          </p>
          <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
            Real evidence from your first week, not slides.
          </h2>
          <p className="mt-4 text-lg text-text-muted">
            The strongest proof is what SentinelGrid delivers in your environment: identity,
            cloud, and endpoint context in one queue, then one guided action pack that feeds
            response, leadership, and trust output.
          </p>
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {proofSignals.map((signal) => (
            <div
              key={signal.label}
              className="rounded-xl border border-border bg-bg/70 p-6 shadow-[0_20px_60px_rgba(2,6,23,0.35)]"
            >
              <div className="text-4xl font-semibold tracking-tight text-text-main">
                {signal.value}
              </div>
              <h3 className="mt-4 text-base font-semibold text-text-main">{signal.label}</h3>
              <p className="mt-3 text-sm leading-6 text-text-muted">{signal.detail}</p>
            </div>
          ))}
        </div>

        <div className="mt-10 grid gap-8 lg:grid-cols-[0.92fr,1.08fr]">
          <div className="space-y-4">
            {firstWeekArtifacts.map((artifact) => (
              <div
                key={artifact.id}
                className="rounded-xl border border-border bg-bg/70 p-6"
              >
                <div className="flex items-center justify-between gap-4">
                  <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    {artifact.stepLabel}
                  </span>
                  <span className="text-[11px] uppercase tracking-[0.14em] text-text-main0">
                    Standard SMB path
                  </span>
                </div>
                <h3 className="mt-4 text-xl font-semibold text-text-main">{artifact.title}</h3>
                <p className="mt-3 text-sm leading-6 text-text-muted">{artifact.description}</p>
                <div className="mt-4 rounded-2xl border border-border bg-bg-alt/80 px-4 py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                    What the buyer can verify
                  </p>
                  <p className="mt-2 text-sm text-text-main/80">{artifact.artifact}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-6">
            <div className="rounded-[32px] border border-border bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 p-6 shadow-[0_25px_80px_rgba(2,6,23,0.45)]">
              <div className="flex items-center justify-between gap-4 border-b border-border pb-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    Operator evidence
                  </p>
                  <h3 className="mt-2 text-2xl font-semibold text-text-main">
                    Suspicious login tied to cloud privilege and endpoint coverage drift
                  </h3>
                </div>
                <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-amber-200">
                  High
                </span>
              </div>

              <div className="mt-5 grid gap-4 md:grid-cols-[1.1fr,0.9fr]">
                <div className="rounded-xl border border-border bg-bg-alt/90 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                    Signals grouped into one record
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {evidenceInputs.map((item) => (
                      <span
                        key={item}
                        className="rounded-full border border-border-muted bg-bg/90 px-3 py-1.5 text-xs text-text-main/80"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                  <div className="mt-5 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                      Why it is prioritized
                    </p>
                    <p className="mt-2 text-sm leading-6 text-text-main/80">
                      The same identity is tied to a high-risk sign-in pattern, privileged access,
                      and an endpoint coverage gap. The operator sees one queue item instead of
                      chasing three separate systems.
                    </p>
                  </div>
                </div>

                <div className="rounded-xl border border-border bg-bg-alt/90 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-300">
                    Guided action pack
                  </p>
                  <div className="mt-4 space-y-3">
                    {evidenceActions.map((action, index) => (
                      <div
                        key={action}
                        className="flex items-center gap-3 rounded-2xl border border-border bg-bg/80 px-4 py-3"
                      >
                        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-xs font-semibold text-emerald-300">
                          {index + 1}
                        </span>
                        <span className="text-sm text-text-main/80">{action}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-[28px] border border-border bg-bg/70 p-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    Leadership-ready summary
                  </p>
                  <h3 className="mt-2 text-xl font-semibold text-text-main">
                    The same work item can feed updates outside the SOC workflow.
                  </h3>
                </div>
                <span className="rounded-full border border-border-muted px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text-muted">
                  Weekly report
                </span>
              </div>
              <div className="mt-5 grid gap-4 md:grid-cols-[0.85fr,1.15fr]">
                <div className="rounded-xl border border-border bg-bg-alt/90 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                    Outputs
                  </p>
                  <div className="mt-4 space-y-3">
                    {summaryItems.map((item) => (
                      <div key={item} className="rounded-2xl border border-border bg-bg/80 px-4 py-3 text-sm text-text-main/80">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-bg-alt/90 p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                    Why this matters to buyers
                  </p>
                  <p className="mt-4 text-sm leading-6 text-text-muted">
                    A growing team does not just need detections. It needs one clean operating
                    story that can be handed to an analyst, a manager, and an auditor without
                    rewriting the context every time.
                  </p>
                  <div className="mt-4 rounded-2xl border border-border bg-bg/80 px-4 py-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                      See it in your environment
                    </p>
                    <p className="mt-2 text-sm text-text-main/80">
                      Picture this flow with your own identity, cloud, and endpoint context. That
                      is what the first week delivers.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <TrackedLink
            href="/walkthrough"
            eventName="marketing_cta_click"
            eventProps={{ source: ctaSource, target: "walkthrough" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Walk through the proof live
          </TrackedLink>
          {showProductCta ? (
            <TrackedLink
              href="/product"
              eventName="marketing_cta_click"
              eventProps={{ source: ctaSource, target: "product" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Review the product flow
            </TrackedLink>
          ) : null}
        </div>
      </div>
    </section>
  );
}
