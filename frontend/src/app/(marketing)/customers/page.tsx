import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { CustomerProfileGrid } from "@/components/marketing/CustomerProfileGrid";
import { CustomerStoryCards } from "@/components/marketing/CustomerStoryCards";
import { ProofSection } from "@/components/marketing/ProofSection";
import { TrackedLink } from "@/components/marketing/TrackedLink";

export const metadata: Metadata = {
  title: "SentinelGrid Customer Profiles And Proof Paths",
  description:
    "Representative SMB and mid-market customer profiles, first-week proof paths, and the outcomes SentinelGrid is built to deliver for growing teams.",
};

const sharedPatterns = [
  "They need one queue instead of multiple dashboards and spreadsheets.",
  "They need guided remediation, ownership, and reporting from the same work item.",
  "They need AWS or Azure plus Microsoft 365 / Entra or Google Workspace to produce value quickly.",
  "They need trust and compliance output without buying a second workflow first.",
];

export default function CustomersPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Customers
          </p>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
            Representative customer paths for the teams SentinelGrid is built to help.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-muted">
            This page shows the kinds of buyers, operators, and outcomes SentinelGrid is designed
            for. These are representative operating profiles for the SMB motion, not named public
            case studies.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <TrackedLink
              href="/walkthrough"
              eventName="marketing_nav_click"
              eventProps={{ source: "customers_page_hero", target: "walkthrough" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Review the first-week walkthrough
            </TrackedLink>
            <TrackedLink
              href="/demo"
              eventName="marketing_cta_click"
              eventProps={{ source: "customers_page_hero", target: "demo" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Book a demo
            </TrackedLink>
          </div>
        </div>

        <div className="mt-12">
          <CustomerProfileGrid />
        </div>

        <div className="mt-12 rounded-2xl border border-border bg-bg-alt/80 p-8 md:p-10">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Shared buying pattern
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              What these teams have in common is operational compression.
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-muted">
              The buyer may be different, but the operating problem repeats: too many tools, too
              little correlation, and too much manual reporting outside the security workflow.
            </p>
          </div>
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            {sharedPatterns.map((pattern) => (
              <div
                key={pattern}
                className="rounded-xl border border-border bg-bg/80 p-5 text-sm leading-6 text-text-muted"
              >
                {pattern}
              </div>
            ))}
          </div>
        </div>
      </section>
      <CustomerStoryCards source="customers_page_story_cards" showCta={false} />
      <ProofSection ctaSource="customers_page_proof" compact />
      <Footer />
    </main>
  );
}
