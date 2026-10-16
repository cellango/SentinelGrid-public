import { aiShieldAddon, marketingPlans } from "@/lib/marketing/packages";
import { TrackedLink } from "./TrackedLink";

export function HomepagePricingPreview() {
  return (
    <section id="pricing-preview" className="py-20 px-6 bg-bg-alt/50">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Pricing
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              Predictable pricing for teams that need security outcomes, not log math.
            </h2>
            <p className="mt-4 text-text-muted text-lg">
              Start with the package that matches your team today. Standard onboarding for core
              connectors is included, and larger environments can grow without rebuilding later.
            </p>
            <p className="mt-3 text-sm text-cyan-300">
              Most teams should start with Protect + Defend if they want the full operator workflow on day one.
            </p>
          </div>
          <TrackedLink
            href="/pricing"
            eventName="marketing_pricing_click"
            eventProps={{ source: "homepage_pricing_header" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            See full pricing
          </TrackedLink>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {marketingPlans.map((plan) => (
            <div
              key={plan.key}
              className={`rounded-xl border p-6 ${
                plan.badge
                  ? "border-cyan-500/70 bg-bg-alt shadow-xl shadow-cyan-500/10"
                  : "border-border bg-bg-alt/80"
              }`}
            >
              {plan.badge && (
                <div className="mb-3 inline-flex rounded-full bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                  {plan.badge}
                </div>
              )}
              <h3 className="text-2xl font-semibold text-text-main">{plan.name}</h3>
              <p className="mt-2 text-sm leading-6 text-text-muted">{plan.subtitle}</p>
              <div className="mt-6">
                <p className="text-4xl font-semibold text-text-main">{plan.priceLabel}</p>
                <p className="mt-1 text-sm text-text-muted/70">{plan.annualLabel}</p>
              </div>
              <p className="mt-4 text-sm text-text-muted/70">{plan.audience}</p>
              <ul className="mt-6 space-y-3">
                {plan.included.slice(0, 4).map((feature) => (
                  <li key={feature} className="flex gap-2 text-sm text-text-main/80">
                    <span className="mt-0.5 text-cyan-400">✓</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <TrackedLink
                href={plan.ctaHref}
                eventName="marketing_pricing_click"
                eventProps={{ source: "homepage_pricing_card", plan: plan.key }}
                className={`mt-6 inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition-colors ${
                  plan.badge
                    ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
                    : "border border-border-muted text-text-main hover:border-cyan-400"
                }`}
              >
                {plan.ctaLabel}
              </TrackedLink>
            </div>
          ))}
        </div>

        <div className="mt-8 rounded-xl border border-border bg-bg/70 p-6 md:flex md:items-center md:justify-between md:gap-8">
          <div className="max-w-3xl">
            <h3 className="text-xl font-semibold text-text-main">
              Optional launch add-on: {aiShieldAddon.name}
            </h3>
            <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-fuchsia-300">
              {aiShieldAddon.availabilityLabel}
            </p>
            <p className="mt-2 text-sm leading-6 text-text-muted">{aiShieldAddon.description}</p>
            <p className="mt-3 text-sm leading-6 text-text-main/80">{aiShieldAddon.launchNote}</p>
            <ul className="mt-4 space-y-2">
              {aiShieldAddon.highlights.map((item) => (
                <li key={item.title} className="flex gap-2 text-sm text-text-muted">
                  <span className="mt-0.5 text-fuchsia-400">•</span>
                  <span>
                    <span className="font-medium text-text-main">{item.title}:</span> {item.description}
                  </span>
                </li>
              ))}
            </ul>
          </div>
          <div className="mt-4 md:mt-0 md:text-right">
            <p className="text-2xl font-semibold text-cyan-300">{aiShieldAddon.priceLabel}</p>
            <div className="mt-3 flex flex-wrap gap-3 md:justify-end">
              <TrackedLink
                href={aiShieldAddon.ctaHref}
                eventName="marketing_pricing_click"
                eventProps={{ source: "homepage_ai_shield_addon", target: "ai_shield_page" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-4 py-2 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                {aiShieldAddon.ctaLabel}
              </TrackedLink>
              <TrackedLink
                href="/demo"
                eventName="marketing_pricing_click"
                eventProps={{ source: "homepage_ai_shield_addon", target: "demo" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-4 py-2 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Book a demo
              </TrackedLink>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
