import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { OnboardingEstimator } from "@/components/marketing/OnboardingEstimator";
import { PricingComparison } from "@/components/marketing/PricingComparison";
import { TrackedLink } from "@/components/marketing/TrackedLink";
import { aiShieldAddon } from "@/lib/marketing/packages";

export const metadata: Metadata = {
  title: "SentinelGrid Pricing",
  description:
    "Predictable pricing for growing teams, with Protect + Defend as the primary operator package and AI Shield as a controlled launch add-on. Public starting prices, standard onboarding included for core connectors, and no log-tax headline pricing.",
};

export default function PricingPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Pricing
          </p>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
            Predictable security pricing. No log tax.
          </h1>
          <p className="mt-5 text-lg leading-8 text-text-muted">
            Start with the package that matches your team today. Standard onboarding for core
            connectors is included, and larger environments can move to custom pricing without
            forcing a new operating model.
          </p>
          <p className="mt-3 text-sm text-cyan-300">
            If you want the full queue, incident, and response workflow on day one, start with Protect + Defend.
          </p>
          <div className="mt-6 rounded-2xl border border-fuchsia-500/20 bg-fuchsia-500/10 p-4 text-sm leading-6 text-text-main/80">
            <span className="font-semibold text-fuchsia-300">{aiShieldAddon.name}</span> is a{" "}
            <span className="font-semibold text-text-main">{aiShieldAddon.availabilityLabel.toLowerCase()}</span>. It starts at{" "}
            <span className="font-semibold text-text-main">{aiShieldAddon.priceLabel.replace("Starting at ", "")}</span> and
            uses the launch-supported AI path instead of implying blanket provider or self-serve support.
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <TrackedLink
              href="/signup"
              eventName="marketing_pricing_click"
              eventProps={{ source: "pricing_page_hero", target: "signup" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Get started
            </TrackedLink>
            <TrackedLink
              href="/demo"
              eventName="marketing_pricing_click"
              eventProps={{ source: "pricing_page_hero", target: "demo" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Book a demo
            </TrackedLink>
          </div>
        </div>

        <div className="mt-12">
          <PricingComparison />
        </div>
      </section>
      <OnboardingEstimator source="pricing_page_estimator" />
      <Footer />
    </main>
  );
}
