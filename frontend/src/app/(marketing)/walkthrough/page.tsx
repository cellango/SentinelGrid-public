import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { TrackedLink } from "@/components/marketing/TrackedLink";
import {
  launchWorkflowBadgeLabels,
  launchWorkflowSteps,
  type LaunchWorkflowStepId,
} from "@/lib/marketing/launchWorkflow";

export const metadata: Metadata = {
  title: "SentinelGrid First-Week Walkthrough",
  description:
    "See the five-step first-week walkthrough for connecting identity, cloud, and qualified endpoint coverage, then acting from one prioritized queue.",
};

const walkthroughStepDetails: Record<
  LaunchWorkflowStepId,
  {
    summary: string;
    outcomes: string[];
    rightLabel: string;
    rightTitle: string;
    rightBody: string;
    rightItems: string[];
    proofLabel: string;
  }
> = {
  identity: {
    summary:
      "Standard onboarding starts with the default identity path. The first proof point is that the identity system is online and risky access context has a real tenant anchor.",
    outcomes: [
      "Identity connector health and sync timestamps are visible",
      "Risky sign-ins and access hygiene findings are live",
      "The rollout stays on the standard lean-team path",
    ],
    rightLabel: "What the operator sees",
    rightTitle: "Identity connection state with first risky access context",
    rightBody:
      "Microsoft 365 / Entra, Google Workspace, or Okta sign-in activity starts feeding the same working record instead of a disconnected admin view.",
    rightItems: [
      "Identity connected and syncing",
      "Risky sign-ins normalized",
      "Stale MFA and account hygiene checks visible",
    ],
    proofLabel: "Connection proof",
  },
  cloud: {
    summary:
      "The next proof point is the cloud connection adding posture and privilege context to the same operating plane instead of forcing another console hop.",
    outcomes: [
      "AWS or Azure posture findings are normalized",
      "Privileged access and exposure context are correlated",
      "Cloud and identity context stay in one working record",
    ],
    rightLabel: "What the operator sees",
    rightTitle: "Cloud findings feeding the same queue",
    rightBody:
      "Cloud posture issues, privilege findings, and exposure context join the identity record instead of creating a second place to triage.",
    rightItems: [
      "AWS or Azure connected",
      "Posture and privilege findings imported",
      "Cross-domain record enrichment active",
    ],
    proofLabel: "Queue input",
  },
  endpoint: {
    summary:
      "If endpoint scope is part of the launch path, the proof point is qualified coverage inside the same workflow, not a separate product-parity story.",
    outcomes: [
      "Coverage state is visible in the launch workflow",
      "Missing heartbeat or rollout drift is surfaced honestly",
      "Endpoint context joins identity and cloud work",
    ],
    rightLabel: "What the operator sees",
    rightTitle: "Qualified endpoint coverage in the same console",
    rightBody:
      "SentinelGuard coverage state and heartbeat data show up as part of the same operator queue so the team does not need a separate endpoint workflow for first value.",
    rightItems: [
      "Pilot endpoints enrolled",
      "Heartbeat and coverage status visible",
      "Missing coverage alerts routed into the queue",
    ],
    proofLabel: "Coverage proof",
  },
  queue: {
    summary:
      "The queue proof is not just another dashboard card. It is one prioritized record that explains what happened, why it matters, who is affected, and what to do next.",
    outcomes: [
      "Identity, cloud, and endpoint context are grouped into one record",
      "Optional AI signals can land in the same queue when AI Shield is in scope",
      "Response suggestions are visible before the analyst leaves the page",
    ],
    rightLabel: "What the operator sees",
    rightTitle: "One prioritized record instead of three disconnected screens",
    rightBody:
      "The same identity is tied to a risky sign-in, privileged access, and endpoint coverage drift. SentinelGrid surfaces one queue item with the recommended next action and routing.",
    rightItems: [
      "Priority: High",
      "Cross-domain context attached",
      "Suggested response pack ready",
    ],
    proofLabel: "Queue proof",
  },
  action: {
    summary:
      "The operating proof ends with action. The same work item should feed a guided action pack, ownership, leadership updates, and trust evidence without rebuilding the story elsewhere.",
    outcomes: [
      "Guided action steps can be approved from the same record",
      "Ownership and downstream handoff stay attached",
      "Leadership and evidence output come from the same trail",
    ],
    rightLabel: "What you can verify",
    rightTitle: "One operating record, action included",
    rightBody:
      "An SMB team should be able to see how the same finding supports analyst action, a manager update, and trust or audit work. That is the point of the walkthrough.",
    rightItems: [
      "Action approved with owner and due date",
      "Ticket or handoff created from the same record",
      "Evidence timeline preserved for reporting",
    ],
    proofLabel: "Action proof",
  },
};

const walkthroughSteps = launchWorkflowSteps.map((step) => ({
  ...step,
  ...walkthroughStepDetails[step.id],
}));

const includedItems = [
  "Standard identity connection on the launch-safe path",
  "Cloud connection and first normalized findings in the same record",
  "Qualified endpoint coverage tied to the main operator workflow",
  "One prioritized queue item with a guided action pack",
  "Leadership-ready summary and evidence from the same work record",
];

const qualificationNotes = [
  "This walkthrough is the default direct-buyer path, not the partner / MSP motion.",
  "AI Shield fits this story only as the same-queue add-on on the approved launch provider path.",
  "Complex retention, multi-environment rollout, or unusual trust-review asks should move to a guided review instead of being treated as standard onboarding.",
];

export default function WalkthroughPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />

      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid gap-10 lg:grid-cols-[1.05fr,0.95fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              First-week walkthrough
            </p>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
              What SentinelGrid looks like in week one.
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-text-muted">
              This is the self-guided version of the buyer story. It shows the standard launch
              path: connect identity, connect cloud, add qualified endpoint coverage, review one
              prioritized queue item, and take one guided action that feeds reporting output.
            </p>

            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href="/signup"
                eventName="marketing_cta_click"
                eventProps={{ source: "walkthrough_hero", target: "signup" }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Start guided onboarding
              </TrackedLink>
              <TrackedLink
                href="/demo"
                eventName="marketing_cta_click"
                eventProps={{ source: "walkthrough_hero", target: "demo" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Book a live walkthrough
              </TrackedLink>
            </div>

            <div className="mt-8 flex flex-wrap gap-3 text-xs text-text-muted">
              {launchWorkflowBadgeLabels.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-border bg-bg-alt/80 px-3 py-1.5"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 p-6 shadow-[0_25px_80px_rgba(2,6,23,0.45)]">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Timeline
            </p>
            <div className="mt-5 space-y-0">
              {walkthroughSteps.map((step, i) => (
                <div key={step.id} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-[11px] font-bold text-cyan-300">
                      {i + 1}
                    </div>
                    {i < walkthroughSteps.length - 1 && (
                      <div className="w-px flex-1 bg-bg-alt" />
                    )}
                  </div>
                  <div className="pb-6">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                      {step.stepLabel}
                    </p>
                    <h2 className="mt-1 text-base font-semibold text-text-main">{step.title}</h2>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="max-w-7xl mx-auto space-y-8">
          {walkthroughSteps.map((step) => (
            <div
              key={step.id}
              className="grid gap-6 lg:grid-cols-[0.92fr,1.08fr]"
            >
              <div className="rounded-xl border border-border bg-bg-alt/80 p-6">
                <div className="flex items-center justify-between gap-4">
                  <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    {step.stepLabel}
                  </span>
                  <span className="text-[11px] uppercase tracking-[0.14em] text-text-main0">
                    Expected outputs
                  </span>
                </div>
                <h2 className="mt-4 text-2xl font-semibold text-text-main">{step.title}</h2>
                <p className="mt-3 text-sm leading-6 text-text-muted">{step.summary}</p>
                <div className="mt-5 space-y-3">
                  {step.outcomes.map((outcome) => (
                    <div
                      key={outcome}
                      className="rounded-2xl border border-border bg-bg/80 px-4 py-3 text-sm text-text-main/80"
                    >
                      {outcome}
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-border bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900 p-6 shadow-[0_25px_80px_rgba(2,6,23,0.4)]">
                <div className="border-b border-border pb-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    {step.rightLabel}
                  </p>
                  <h3 className="mt-2 text-2xl font-semibold text-text-main">{step.rightTitle}</h3>
                  <p className="mt-3 text-sm leading-6 text-text-muted">{step.rightBody}</p>
                </div>
                <div className="mt-5 space-y-3">
                  {step.rightItems.map((item) => (
                    <div
                      key={item}
                      className="flex items-center justify-between gap-4 rounded-2xl border border-border bg-bg-alt/90 px-4 py-3"
                    >
                      <span className="text-sm text-text-main/80">{item}</span>
                      <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-emerald-300">
                        {step.proofLabel}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="max-w-6xl mx-auto rounded-2xl border border-border bg-bg-alt/80 p-8 md:p-10">
          <div className="grid gap-8 lg:grid-cols-[0.85fr,1.15fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
                Included in the first-week story
              </p>
              <h2 className="text-3xl font-semibold tracking-tight text-text-main">
                What to expect without needing a services project.
              </h2>
              <p className="mt-4 text-sm leading-6 text-text-muted">
                The walkthrough is not meant to over-promise custom setup. It is meant to show the
                standard path clearly enough that a buyer understands what happens first and what
                value they should expect quickly.
              </p>
            </div>
            <div className="space-y-3">
              {includedItems.map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-border bg-bg/80 px-4 py-3 text-sm text-text-main/80"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="max-w-6xl mx-auto rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-8 md:p-10">
          <div className="grid gap-8 lg:grid-cols-[0.9fr,1.1fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
                Launch boundary note
              </p>
              <h2 className="text-3xl font-semibold tracking-tight text-text-main">
                The walkthrough is meant to qualify fit, not to promise every path is standard.
              </h2>
              <p className="mt-4 text-sm leading-6 text-text-main/80">
                The approved launch motion starts narrow on purpose. If your environment needs a
                more complex rollout, the right move is a guided review rather than a looser
                promise.
              </p>
            </div>
            <div className="space-y-3">
              {qualificationNotes.map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-border bg-bg/80 px-4 py-3 text-sm text-text-main/80"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="px-6 pb-24">
        <div className="max-w-6xl mx-auto rounded-2xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 p-8 md:p-12">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Next step
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              Move from the walkthrough to a real onboarding path.
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-main/80">
              Start guided onboarding if you want to see your own environment flow through the same
              sequence, or book a live walkthrough if you want packaging and operator questions
              covered with the team.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href="/signup"
                eventName="marketing_cta_click"
                eventProps={{ source: "walkthrough_final_cta", target: "signup" }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Start guided onboarding
              </TrackedLink>
              <TrackedLink
                href="/demo"
                eventName="marketing_cta_click"
                eventProps={{ source: "walkthrough_final_cta", target: "demo" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Book a live walkthrough
              </TrackedLink>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
