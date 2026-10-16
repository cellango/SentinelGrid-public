import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ComparisonTable } from "@/components/marketing/ComparisonTable";
import { TrackedLink } from "@/components/marketing/TrackedLink";

export const metadata: Metadata = {
  title: "SentinelGrid vs Wiz for Growing Teams",
  description:
    "A practical comparison for SMB and mid-market buyers who want faster onboarding, guided response, and a simpler buying motion than enterprise-first platforms.",
};

const differentiators = [
  "SentinelGrid is optimizing for operator simplicity and guided action, not just cloud graph depth.",
  "The packaging and pricing model is designed to be easier for smaller teams to understand.",
  "The product story combines identity, cloud, endpoint, posture, and AI in one operator workflow.",
];

export default function CompareWizPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Comparison
          </p>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
            Why growing teams choose SentinelGrid over enterprise-first cloud security platforms.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-muted">
            If you need a faster path to visibility, guided response, and predictable pricing,
            SentinelGrid is built for that motion. Wiz remains a strong enterprise benchmark, but
            the buyer and operating model are different.
          </p>
        </div>

        <div className="mt-10">
          <ComparisonTable />
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {differentiators.map((item) => (
            <div key={item} className="rounded-xl border border-border bg-bg-alt/80 p-6 text-sm leading-6 text-text-muted">
              {item}
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          <TrackedLink
            href="/pricing"
            eventName="marketing_nav_click"
            eventProps={{ source: "compare_wiz", target: "pricing" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Review pricing
          </TrackedLink>
          <TrackedLink
            href="/demo"
            eventName="marketing_cta_click"
            eventProps={{ source: "compare_wiz", target: "demo" }}
            className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Book a demo
          </TrackedLink>
        </div>
      </section>
      <Footer />
    </main>
  );
}
