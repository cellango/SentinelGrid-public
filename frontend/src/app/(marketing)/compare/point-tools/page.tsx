import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { PointToolComparisonTable } from "@/components/marketing/PointToolComparisonTable";
import { TrackedLink } from "@/components/marketing/TrackedLink";

export const metadata: Metadata = {
  title: "SentinelGrid vs Point Tool Sprawl",
  description:
    "A practical comparison for SMB and mid-market buyers evaluating SentinelGrid against stacks of separate cloud, identity, endpoint, response, and trust tools.",
};

const hiddenCosts = [
  {
    title: "Context loss",
    description:
      "Identity, cloud, endpoint, and response teams keep rebuilding the same story because the tools do not share one operating record.",
  },
  {
    title: "Commercial sprawl",
    description:
      "Separate contracts and separate onboarding projects make the stack feel smaller at first and more expensive over time.",
  },
  {
    title: "Manual reporting",
    description:
      "Leadership updates, audit evidence, and customer-review packets end up living in documents and spreadsheets instead of in the platform itself.",
  },
];

const switchSignals = [
  "You are already paying for multiple security products but still triage work in tickets and chat.",
  "No one can quickly explain the top three open security priorities without screen-sharing multiple tools.",
  "The same finding needs to be rewritten for operators, leadership, and customer-review workflows.",
  "Adding AI security today would mean adding another separate product and another separate queue.",
];

export default function ComparePointToolsPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Comparison
          </p>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
            Why growing teams replace point-tool sprawl with one operator workflow.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-muted">
            The question for smaller teams is usually not whether each point tool is good in
            isolation. It is whether the combined operating model is still coherent once buying,
            triage, response, and reporting all have to work together.
          </p>
        </div>

        <div className="mt-10">
          <PointToolComparisonTable />
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {hiddenCosts.map((item) => (
            <div key={item.title} className="rounded-xl border border-border bg-bg-alt/80 p-6">
              <h2 className="text-xl font-semibold text-text-main">{item.title}</h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">{item.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 rounded-2xl border border-border bg-bg-alt/80 p-8 md:p-10">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              When to switch
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              The stack stops working when the handoffs become the real system.
            </h2>
          </div>
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            {switchSignals.map((signal) => (
              <div
                key={signal}
                className="rounded-xl border border-border bg-bg/80 p-5 text-sm leading-6 text-text-muted"
              >
                {signal}
              </div>
            ))}
          </div>
        </div>

        <div className="mt-12 rounded-2xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 p-8 md:p-10">
          <div className="max-w-4xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              ROI asset
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              Make the cost of point-tool sprawl visible in dollars and hours.
            </h2>
            <p className="mt-4 text-lg leading-8 text-text-main/80">
              The commercial problem is not just license cost. It is the combination of overlapping
              tools, reporting overhead, and operator time lost to handoffs. SentinelGrid now has
              a dedicated ROI model to frame that conversation clearly.
            </p>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <TrackedLink
              href="/roi"
              eventName="marketing_cta_click"
              eventProps={{ source: "compare_point_tools_roi", target: "roi" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Open the ROI model
            </TrackedLink>
            <TrackedLink
              href="/pricing"
              eventName="marketing_nav_click"
              eventProps={{ source: "compare_point_tools_roi", target: "pricing" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Review package pricing
            </TrackedLink>
          </div>
        </div>

        <div className="mt-10 flex flex-wrap gap-3">
          <TrackedLink
            href="/pricing"
            eventName="marketing_nav_click"
            eventProps={{ source: "compare_point_tools", target: "pricing" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Review pricing
          </TrackedLink>
          <TrackedLink
            href="/compare/wiz"
            eventName="marketing_nav_click"
            eventProps={{ source: "compare_point_tools", target: "compare_wiz" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Compare against Wiz
          </TrackedLink>
          <TrackedLink
            href="/roi"
            eventName="marketing_nav_click"
            eventProps={{ source: "compare_point_tools", target: "roi" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Run the ROI model
          </TrackedLink>
          <TrackedLink
            href="/demo"
            eventName="marketing_cta_click"
            eventProps={{ source: "compare_point_tools", target: "demo" }}
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
