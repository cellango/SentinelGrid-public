import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { DemoRequestForm } from "@/components/marketing/DemoRequestForm";
import { OnboardingEstimator } from "@/components/marketing/OnboardingEstimator";
import { TrackedLink } from "@/components/marketing/TrackedLink";

export const metadata: Metadata = {
  title: "Book a SentinelGrid Demo",
  description:
    "See how SentinelGrid connects identity, cloud, endpoint coverage, and optional AI risk into one operator workflow for growing teams.",
};

const agenda = [
  "Connect identity on the default launch path",
  "Connect cloud and normalize the first findings",
  "Add qualified endpoint coverage on the same operator workflow",
  "See one prioritized queue item with cross-domain context",
  "Take one guided action pack and see how optional AI risk uses the same queue",
];

const partnerAgenda = [
  "How the qualified partner motion handles cross-tenant review and explicit tenant-context entry",
  "Which delivery mode fits your service model: advisory, co-managed, or partner-led",
  "How delegated response, approvals, and client reporting work inside one platform",
  "What partner-fit packaging and rollout scope look like for managed tenants",
];

const launchSafeClaims = [
  "Standard demos lead with the five-step operator path: identity, cloud, endpoint coverage, one queue, one guided action.",
  "AI Shield is shown only as the same-queue extension for the approved launch provider path.",
  "Partner workflows are qualified and sales-assisted, not the default self-serve path.",
  "Pentest and other adjacent product lines stay outside the initial core SaaS walkthrough.",
];

const guidedReviewTriggers = [
  "More than one core cloud environment in the first rollout",
  "Mixed or undecided identity architecture",
  "Partner-led delivery or managed-tenant motion",
  "Unusual retention, archive, or trust-review requirements",
  "AI Shield as the primary buying reason instead of an add-on",
];

type DemoPageProps = {
  searchParams?: Promise<{
    motion?: string | string[];
  }>;
};

export default async function DemoPage({ searchParams }: DemoPageProps) {
  const resolvedSearchParams = await searchParams;
  const motion = Array.isArray(resolvedSearchParams?.motion)
    ? resolvedSearchParams.motion[0]
    : resolvedSearchParams?.motion;
  const isPartnerMotion = motion === "partner";
  const pageAgenda = isPartnerMotion ? partnerAgenda : agenda;

  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid gap-10 lg:grid-cols-[0.95fr,1.05fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              {isPartnerMotion ? "Partner demo" : "Book a demo"}
            </p>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
              {isPartnerMotion
                ? "See how SentinelGrid supports managed tenants without cross-tenant chaos."
                : "See one operator path from first connection to first guided action."}
            </h1>
            <p className="mt-5 text-lg leading-8 text-text-muted">
              {isPartnerMotion
                ? "We will walk through the partner operating model, tenant-context guardrails, delivery modes, and how SentinelGrid supports MSP and MSSP service workflows."
                : "We will walk through the five-step launch path, the package fit, and how lean teams get from connection to action without platform sprawl."}
            </p>

            {isPartnerMotion ? (
              <div className="mt-6 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4 text-sm leading-6 text-text-main/80">
                This route is focused on MSP, MSSP, and shared-security-team conversations. If
                you are evaluating SentinelGrid for your own internal team, the standard product
                demo path still covers onboarding, pricing, and the core operator workflow.
              </div>
            ) : null}

            <div className="mt-8 rounded-xl border border-border bg-bg-alt/80 p-6">
              <h2 className="text-xl font-semibold text-text-main">What we will cover</h2>
              <ul className="mt-4 space-y-3">
                {pageAgenda.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-text-muted">
                    <span className="mt-0.5 text-cyan-400">✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="rounded-xl border border-border bg-bg-alt/80 p-6">
                <h2 className="text-xl font-semibold text-text-main">Launch-safe demo boundary</h2>
                <ul className="mt-4 space-y-3">
                  {launchSafeClaims.map((item) => (
                    <li key={item} className="flex gap-2 text-sm text-text-muted">
                      <span className="mt-0.5 text-cyan-400">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 p-6">
                <h2 className="text-xl font-semibold text-text-main">When we switch to a guided review</h2>
                <ul className="mt-4 space-y-3">
                  {guidedReviewTriggers.map((item) => (
                    <li key={item} className="flex gap-2 text-sm text-text-main/80">
                      <span className="mt-0.5 text-cyan-300">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href="/signup"
                eventName="marketing_cta_click"
                eventProps={{ source: isPartnerMotion ? "demo_page_partner" : "demo_page", target: "signup" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Prefer self-serve? Start guided onboarding
              </TrackedLink>
              {isPartnerMotion ? (
                <TrackedLink
                  href="/partners"
                  eventName="marketing_nav_click"
                  eventProps={{ source: "demo_page_partner", target: "partners" }}
                  className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
                >
                  Review the partner path
                </TrackedLink>
              ) : null}
            </div>
          </div>

          <div className="space-y-6">
            <DemoRequestForm />
            <div className="rounded-xl border border-border bg-bg-alt/80 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-2">
                Prefer to book directly?
              </p>
              <p className="text-sm text-text-muted mb-3">
                Pick a 30-minute slot and we will come prepared with a walkthrough tailored to your environment.
              </p>
              <a
                href="https://calendly.com/sentinelgrid/demo"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-full border border-border-muted px-5 py-2.5 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                <svg className="h-4 w-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Open calendar
              </a>
            </div>
          </div>
        </div>
      </section>
      <OnboardingEstimator source="demo_page_estimator" compact />
      <Footer />
    </main>
  );
}
