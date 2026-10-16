import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { OnboardingEstimator } from "@/components/marketing/OnboardingEstimator";
import { TrackedLink } from "@/components/marketing/TrackedLink";
import { marketingPlans } from "@/lib/marketing/packages";

export const metadata: Metadata = {
  title: "SentinelGrid Solutions For SMB Security Teams",
  description:
    "See how SentinelGrid fits lean internal security teams, IT-led security owners, compliance-driven SaaS teams, and organizations that need one queue instead of point-tool sprawl.",
};

const solutionLanes = [
  {
    title: "Lean internal security teams",
    subtitle: "For teams with one security lead and no appetite for five separate tools.",
    packageFit: "Protect + Defend",
    description:
      "Use SentinelGrid when you need a single queue, guided remediation, and response accountability without building a heavyweight SOC operating model.",
    outcomes: [
      "Faster time to first finding from AWS and Microsoft 365",
      "Shared ownership and SLAs for real remediation work",
      "One place to move from alert to action",
    ],
  },
  {
    title: "IT-led security owners",
    subtitle: "For IT or operations leaders carrying security alongside everything else.",
    packageFit: "Protect",
    description:
      "Start with cloud, identity, posture, and baseline detections so the team gets visibility and guided next steps before it has to scale process or tooling.",
    outcomes: [
      "Immediate visibility across cloud and identity",
      "Less dashboard switching and fewer manual handoffs",
      "Predictable package pricing instead of separate vendor sprawl",
    ],
  },
  {
    title: "Trust and compliance-driven SaaS teams",
    subtitle: "For companies under repeated security-review and audit pressure.",
    packageFit: "Protect + Defend + Comply",
    description:
      "Use SentinelGrid when the same security work needs to support response, leadership updates, audit prep, and customer review artifacts.",
    outcomes: [
      "Evidence workflows tied to live platform findings",
      "Audit-ready exports and trust-center artifacts",
      "One operating record for both operators and auditors",
    ],
  },
  {
    title: "AI-using product and platform teams",
    subtitle: "For teams adding AI runtime security without creating another silo.",
    packageFit: "Protect + Defend + AI Shield",
    description:
      "Add AI Shield when prompt injection, data leakage, and AI misuse need to live in the same queue and response workflow. Add Comply only when the trust and evidence layer is also part of the buying motion.",
    outcomes: [
      "AI alerts promoted into the same incident model",
      "AI-specific response packs and ownership workflows",
      "A controlled launch path instead of another detached AI tool",
    ],
  },
];

const workflow = [
  {
    title: "Connect the default SMB path",
    description:
      "Start with AWS or Azure plus Microsoft 365 / Entra or Google Workspace and validate health before expanding scope.",
  },
  {
    title: "Prioritize one queue",
    description:
      "Correlate cloud, identity, endpoint, posture, and AI signals into a single list of work the team can actually act on.",
  },
  {
    title: "Turn findings into response and reporting",
    description:
      "Use ownership, SLAs, response packs, tickets, and reporting without rebuilding context somewhere else.",
  },
];

export default function SolutionsPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Solutions
          </p>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
            Security workflows built for growing teams, not enterprise sprawl.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-muted">
            SentinelGrid is designed for the teams that need faster time to value, one
            operator-facing workflow, and pricing they can explain internally without a six-month
            buying process.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <TrackedLink
              href="/pricing"
              eventName="marketing_nav_click"
              eventProps={{ source: "solutions_page_hero", target: "pricing" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Review packages
            </TrackedLink>
            <TrackedLink
              href="/customers"
              eventName="marketing_nav_click"
              eventProps={{ source: "solutions_page_hero", target: "customers" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              See customer profiles
            </TrackedLink>
            <TrackedLink
              href="/partners"
              eventName="marketing_nav_click"
              eventProps={{ source: "solutions_page_hero", target: "partners" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Partner or MSP?
            </TrackedLink>
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          {solutionLanes.map((lane) => (
            <article
              key={lane.title}
              className="rounded-[30px] border border-border bg-bg-alt/80 p-6"
            >
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                  {lane.packageFit}
                </span>
              </div>
              <h2 className="mt-4 text-2xl font-semibold text-text-main">{lane.title}</h2>
              <p className="mt-3 text-sm font-medium text-text-main/80">{lane.subtitle}</p>
              <p className="mt-4 text-sm leading-6 text-text-muted">{lane.description}</p>
              <ul className="mt-5 space-y-2">
                {lane.outcomes.map((outcome) => (
                  <li key={outcome} className="flex gap-2 text-sm text-text-muted">
                    <span className="mt-0.5 text-emerald-400">•</span>
                    <span>{outcome}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-border bg-bg-alt/80 p-8 md:p-10">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Operating model
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              The same workflow scales from visibility to action.
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-muted">
              The point of the platform is not having more modules. It is having one operating
              rhythm that works for smaller teams from the first connector through the first
              leadership update.
            </p>
          </div>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {workflow.map((step, index) => (
              <div
                key={step.title}
                className="rounded-xl border border-border bg-bg/80 p-6"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-cyan-500/10 text-sm font-semibold text-cyan-300">
                  {index + 1}
                </span>
                <h3 className="mt-4 text-xl font-semibold text-text-main">{step.title}</h3>
                <p className="mt-3 text-sm leading-6 text-text-muted">{step.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {marketingPlans.map((plan) => (
            <div key={plan.key} className="rounded-xl border border-border bg-bg-alt/80 p-6">
              <h2 className="text-2xl font-semibold text-text-main">{plan.name}</h2>
              <p className="mt-2 text-sm text-cyan-300">{plan.priceLabel}</p>
              <p className="mt-4 text-sm leading-6 text-text-muted">{plan.summary}</p>
              <ul className="mt-5 space-y-2">
                {plan.included.slice(0, 3).map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-text-muted">
                    <span className="mt-0.5 text-cyan-400">•</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 p-8">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Managed delivery
            </p>
            <h2 className="text-3xl font-semibold tracking-tight text-text-main">
              SentinelGrid also supports partner-led and co-managed delivery models.
            </h2>
            <p className="mt-4 text-sm leading-6 text-text-main/80">
              If you run security for many customers or business units, SentinelGrid has a
              qualified partner motion with explicit tenant context, delegated response rules, and
              client-ready reporting. That motion is sales-assisted at launch, not the default
              self-serve website promise.
            </p>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <TrackedLink
              href="/partners"
              eventName="marketing_cta_click"
              eventProps={{ source: "solutions_page_partner_callout", target: "partners" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Review qualified partner motion
            </TrackedLink>
            <TrackedLink
              href="/demo?motion=partner"
              eventName="marketing_cta_click"
              eventProps={{ source: "solutions_page_partner_callout", target: "partner_demo" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Book a partner qualification call
            </TrackedLink>
          </div>
        </div>
      </section>
      <OnboardingEstimator source="solutions_page_estimator" />
      <Footer />
    </main>
  );
}
