import { aiShieldAddon, marketingPlans, pricingFaqs } from "@/lib/marketing/packages";
import { TrackedLink } from "./TrackedLink";

export function PricingComparison() {
  return (
    <div className="space-y-10">
      <div className="grid gap-6 lg:grid-cols-3">
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
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold text-text-main">{plan.name}</h2>
                <p className="mt-2 text-sm leading-6 text-text-muted">{plan.subtitle}</p>
              </div>
              <span className="rounded-full border border-border-muted px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text-muted">
                {plan.comparisonLabel}
              </span>
            </div>
            <div className="mt-6">
              <p className="text-4xl font-semibold text-text-main">{plan.priceLabel}</p>
              <p className="mt-1 text-sm text-text-muted/70">{plan.annualLabel}</p>
            </div>
            <p className="mt-4 text-sm text-text-muted/70">{plan.audience}</p>
            <div className="mt-6 grid gap-5">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Included
                </h3>
                <ul className="mt-3 space-y-2">
                  {plan.included.map((feature) => (
                    <li key={feature} className="flex gap-2 text-sm text-text-main/80">
                      <span className="mt-0.5 text-cyan-400">✓</span>
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-text-muted">
                  Standard onboarding
                </h3>
                <ul className="mt-3 space-y-2">
                  {plan.onboarding.map((item) => (
                    <li key={item} className="flex gap-2 text-sm text-text-muted">
                      <span className="mt-0.5 text-emerald-400">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <TrackedLink
              href={plan.ctaHref}
              eventName="marketing_pricing_click"
              eventProps={{ source: "pricing_page_card", plan: plan.key }}
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

      <div className="rounded-xl border border-border bg-bg-alt/80 p-6">
        <div className="grid gap-8 lg:grid-cols-[1.1fr,0.9fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Pricing policy
            </p>
            <h2 className="text-2xl font-semibold text-text-main">
              What is included and when pricing becomes custom
            </h2>
            <ul className="mt-5 space-y-3 text-sm leading-6 text-text-muted">
              <li>Standard onboarding for core connectors is included.</li>
              <li>SentinelGrid does not lead with per-GB log pricing.</li>
              <li>Annual billing receives a built-in discount.</li>
              <li>Custom pricing applies for unusual retention, qualified partner / MSP rollouts, or complex environments.</li>
              <li>Most teams should start with Protect + Defend when they need the full operator workflow.</li>
              <li>AI Shield is a controlled add-on for launch with launch-scoped provider support.</li>
            </ul>
          </div>
          <div className="rounded-2xl border border-border bg-bg/80 p-5">
            <h3 className="text-lg font-semibold text-text-main">{aiShieldAddon.name}</h3>
            <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-fuchsia-300">
              {aiShieldAddon.availabilityLabel}
            </p>
            <p className="mt-2 text-2xl font-semibold text-cyan-300">{aiShieldAddon.priceLabel}</p>
            <p className="mt-3 text-sm leading-6 text-text-muted">{aiShieldAddon.description}</p>
            <p className="mt-3 text-sm leading-6 text-text-main/80">{aiShieldAddon.launchNote}</p>
            <ul className="mt-4 space-y-2">
              {aiShieldAddon.packageFit.map((entry) => (
                <li key={entry.label} className="flex gap-2 text-sm text-text-muted">
                  <span className="mt-0.5 text-fuchsia-400">•</span>
                  <span>
                    <span className="font-medium text-text-main">{entry.label}:</span> {entry.description}
                  </span>
                </li>
              ))}
            </ul>
            <div className="mt-5 flex flex-wrap gap-3">
              <TrackedLink
                href={aiShieldAddon.ctaHref}
                eventName="marketing_pricing_click"
                eventProps={{ source: "pricing_page_ai_shield", target: "ai_shield_page" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-4 py-2 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                {aiShieldAddon.ctaLabel}
              </TrackedLink>
              <TrackedLink
                href="/demo"
                eventName="marketing_pricing_click"
                eventProps={{ source: "pricing_page_ai_shield", target: "demo" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-4 py-2 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Book a demo
              </TrackedLink>
              <TrackedLink
                href="/partners"
                eventName="marketing_pricing_click"
                eventProps={{ source: "pricing_page_ai_shield", target: "partners" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-4 py-2 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                Partner qualification
              </TrackedLink>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {pricingFaqs.map((faq) => (
          <div key={faq.question} className="rounded-2xl border border-border bg-bg-alt/80 p-5">
            <h3 className="text-lg font-semibold text-text-main">{faq.question}</h3>
            <p className="mt-3 text-sm leading-6 text-text-muted">{faq.answer}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
