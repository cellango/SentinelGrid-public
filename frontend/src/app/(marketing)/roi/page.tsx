import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { RoiCalculator } from "@/components/marketing/RoiCalculator";
import { TrackedLink } from "@/components/marketing/TrackedLink";

export const metadata: Metadata = {
  title: "SentinelGrid ROI Calculator",
  description:
    "Model the cost of point-tool sprawl, manual reporting, and operator overhead against the current SentinelGrid package ladder.",
};

const roiSignals = [
  {
    title: "Tool spend is only part of the problem",
    description:
      "The stack cost usually hides inside triage time, reporting overhead, and the need to rebuild the same security story in multiple places.",
  },
  {
    title: "Point-tool ROI erodes through handoffs",
    description:
      "A cheaper individual tool can still create a more expensive operating model if the team has to correlate everything manually.",
  },
  {
    title: "The right output is directional, not pretend-precise",
    description:
      "This calculator is meant to frame the buying conversation clearly, not replace a formal commercial quote or validation interview.",
  },
];

export default function RoiPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            ROI
          </p>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
            Model the cost of point-tool sprawl against one operator workflow.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-muted">
            This sales asset helps buyers quantify what gets lost when security work is split across
            multiple tools, manual reporting, and disconnected handoffs. Use it as a directional
            planning model, not a substitute for final pricing review.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <TrackedLink
              href="/compare/point-tools"
              eventName="marketing_nav_click"
              eventProps={{ source: "roi_page_hero", target: "compare_point_tools" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Review the point-tool comparison
            </TrackedLink>
            <TrackedLink
              href="/demo"
              eventName="marketing_cta_click"
              eventProps={{ source: "roi_page_hero", target: "demo" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Book a pricing review
            </TrackedLink>
          </div>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {roiSignals.map((signal) => (
            <div key={signal.title} className="rounded-xl border border-border bg-bg-alt/80 p-6">
              <h2 className="text-xl font-semibold text-text-main">{signal.title}</h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">{signal.description}</p>
            </div>
          ))}
        </div>
      </section>

      <RoiCalculator source="roi_page" />

      <Footer />
    </main>
  );
}
