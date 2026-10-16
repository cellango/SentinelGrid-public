import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { TrackedLink } from "@/components/marketing/TrackedLink";
import {
  partnerDeliveryModes,
  partnerOperatingRules,
  partnerWorkflowStages,
} from "@/lib/partner/workflows";

export const metadata: Metadata = {
  title: "SentinelGrid For Partners And MSPs",
  description:
    "SentinelGrid offers a qualified sales-assisted partner motion for MSPs, MSSPs, and shared-security teams that need explicit tenant context, delegated response guardrails, and client-ready reporting for managed SMB security delivery.",
};

const partnerTypes = [
  {
    title: "Regional MSPs adding security operations",
    description:
      "Extend existing IT service contracts with a cleaner managed-security workflow instead of stitching together more consoles and spreadsheets.",
  },
  {
    title: "MSSPs serving SMB and mid-market customers",
    description:
      "Run multi-tenant prioritization, delegated response, and reporting with stronger context control than a generic cross-tenant admin view.",
  },
  {
    title: "Internal shared-security teams",
    description:
      "Support subsidiaries, business units, or sister companies from one platform without collapsing tenant isolation or audit history.",
  },
];

const partnerOutcomes = [
  "Cross-tenant visibility for prioritization without hidden tenant switching",
  "Explicit tenant context before assignments, tickets, notes, or response actions",
  "Delivery-mode guardrails for advisory, co-managed, and partner-led service models",
  "Client-pack, trust, and reporting workflows built from the same operating record",
];

export default function PartnersPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid gap-10 lg:grid-cols-[1.05fr,0.95fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Qualified partner motion
            </p>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
              Operate many SMB tenants without turning partner access into chaos.
            </h1>
            <p className="mt-5 text-lg leading-8 text-text-muted">
              SentinelGrid gives MSPs, MSSPs, and shared-security teams a qualified
              sales-assisted managed-tenant motion: cross-tenant oversight, explicit
              tenant-context entry, delegated response guardrails, and customer-ready reporting
              from the same operating record.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href="/demo?motion=partner"
                eventName="marketing_cta_click"
                eventProps={{ source: "partners_page_hero", target: "partner_demo" }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Request a partner qualification review
              </TrackedLink>
              <TrackedLink
                href="/walkthrough"
                eventName="marketing_nav_click"
                eventProps={{ source: "partners_page_hero", target: "walkthrough" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                See the direct-buyer launch path
              </TrackedLink>
            </div>
            <div className="mt-6 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4 text-sm leading-6 text-text-main/80">
              The default self-serve launch remains a direct-buyer, single-tenant motion. Partner
              and MSP delivery starts with qualification, delivery-mode review, and rollout
              scoping instead of a broad website-led product promise.
            </div>
            <div className="mt-8 flex flex-wrap gap-3 text-xs text-text-muted">
              {partnerOutcomes.map((item) => (
                <span
                  key={item}
                  className="rounded-full border border-border bg-bg-alt/80 px-3 py-1.5"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-bg-alt/80 p-6 shadow-[0_25px_80px_rgba(2,6,23,0.4)]">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Partner operating flow
            </p>
            <div className="mt-5 space-y-4">
              {partnerWorkflowStages.map((stage, index) => (
                <div
                  key={stage.title}
                  className="rounded-xl border border-border bg-bg/80 p-5"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-cyan-500/10 text-sm font-semibold text-cyan-300">
                      {index + 1}
                    </span>
                    <h2 className="text-lg font-semibold text-text-main">{stage.title}</h2>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-text-muted">
                    {stage.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {partnerTypes.map((item) => (
            <article
              key={item.title}
              className="rounded-xl border border-border bg-bg-alt/80 p-6"
            >
              <h2 className="text-xl font-semibold text-text-main">{item.title}</h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">{item.description}</p>
            </article>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-border bg-bg-alt/80 p-8 md:p-10">
          <div className="max-w-4xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Delivery modes
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              One partner motion, three clear service models.
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-muted">
              SentinelGrid already has the partner operating contract. The marketing route should
              make the service model legible before the buyer ever expects a default self-serve
              console path.
            </p>
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-3">
            {partnerDeliveryModes.map((mode) => (
              <div
                key={mode.id}
                className="rounded-xl border border-border bg-bg/80 p-6"
              >
                <h3 className="text-2xl font-semibold text-text-main">{mode.label}</h3>
                <p className="mt-3 text-sm leading-6 text-text-muted">{mode.summary}</p>
                <div className="mt-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                    Partner owns
                  </p>
                  <ul className="mt-3 space-y-2">
                    {mode.partnerOwns.map((item) => (
                      <li key={item} className="flex gap-2 text-sm text-text-muted">
                        <span className="mt-0.5 text-cyan-400">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="mt-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-300">
                    Customer owns
                  </p>
                  <ul className="mt-3 space-y-2">
                    {mode.customerOwns.map((item) => (
                      <li key={item} className="flex gap-2 text-sm text-text-muted">
                        <span className="mt-0.5 text-emerald-400">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
          <div className="rounded-2xl border border-border bg-bg-alt/80 p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Guardrails
            </p>
            <h2 className="text-3xl font-semibold tracking-tight text-text-main">
              Multi-tenant delivery without blind cross-tenant admin behavior.
            </h2>
            <ul className="mt-6 space-y-3">
              {partnerOperatingRules.map((rule) => (
                <li key={rule} className="flex gap-3 text-sm leading-6 text-text-muted">
                  <span className="mt-0.5 text-cyan-400">✓</span>
                  <span>{rule}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 p-8">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Next step
            </p>
            <h2 className="text-3xl font-semibold tracking-tight text-text-main">
              If you run managed tenants, SentinelGrid should show you the exact partner motion.
            </h2>
            <p className="mt-4 text-sm leading-6 text-text-main/80">
              The right next conversation is not a generic product tour. It is a partner-specific
              qualification walkthrough of delivery mode, tenant-context guardrails, client
              reporting, and how your current service model maps into the platform.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href="/demo?motion=partner"
                eventName="marketing_cta_click"
                eventProps={{ source: "partners_page_final", target: "partner_demo" }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Book a partner qualification call
              </TrackedLink>
              <TrackedLink
                href="/solutions"
                eventName="marketing_nav_click"
                eventProps={{ source: "partners_page_final", target: "solutions" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Review solution paths
              </TrackedLink>
            </div>
          </div>
        </div>
      </section>
      <Footer />
    </main>
  );
}
