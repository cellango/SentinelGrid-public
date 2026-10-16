import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ProofSection } from "@/components/marketing/ProofSection";
import { TrackedLink } from "@/components/marketing/TrackedLink";
import { aiShieldAddon } from "@/lib/marketing/packages";

export const metadata: Metadata = {
  title: "AI Shield | SentinelGrid",
  description:
    "Review SentinelGrid AI Shield as a controlled launch add-on for runtime AI security. Protect supported AI traffic from prompt injection, data leakage, and policy misuse without creating another console.",
};

const threats = [
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126z" />
      </svg>
    ),
    title: "Prompt Injection",
    description:
      "Detect and block injection attacks that attempt to hijack your AI model behavior, extract system prompts, or bypass safety guardrails.",
    stat: "Runtime detection",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
      </svg>
    ),
    title: "Data Leakage",
    description:
      "Monitor AI outputs for sensitive data exposure — PII, credentials, internal documents, and proprietary information leaving your perimeter.",
    stat: "Output scanning",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
    title: "Policy Violations",
    description:
      "Enforce organizational AI usage policies in real time. Flag tool misuse, unapproved model access, and behavioral anomalies.",
    stat: "Policy engine",
  },
  {
    icon: (
      <svg className="w-6 h-6" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
      </svg>
    ),
    title: "Shadow AI Discovery",
    description:
      "Discover unapproved AI tools and models across your organization. Know what AI is being used before it becomes a security incident.",
    stat: "Continuous audit",
  },
];

const differentiators = [
  {
    title: "Not a sidecar — part of the platform",
    description:
      "AI Shield alerts land in the same War Room, trigger the same playbooks, and feed the same compliance evidence as every other SentinelGrid finding.",
  },
  {
    title: "Same incident model, same response workflow",
    description:
      "AI security incidents use the canonical entity and story model. The SOC analyst investigating a prompt injection attack uses the same tools as the one investigating a cloud misconfiguration.",
  },
  {
    title: "Compliance-ready from day one",
    description:
      "AI risk findings map to SOC 2 criteria and generate audit-ready evidence automatically. No separate AI compliance workflow to learn.",
  },
  {
    title: "Response packs for AI-specific threats",
    description:
      "Pre-built response packs for prompt injection, data leakage, and policy violation. Each pack includes containment steps, evidence collection, and notification templates.",
  },
];

const architecture = [
  { label: "AI App", description: "Your LLM-powered application" },
  { label: "AI Shield SDK", description: "Lightweight runtime interceptor" },
  { label: "SentinelGrid Ingest", description: "Canonical alert creation" },
  { label: "War Room", description: "Prioritized operator queue" },
  { label: "Response Pack", description: "Automated containment" },
  { label: "Compliance Evidence", description: "Audit-ready record" },
];

export default function AIShieldPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid lg:grid-cols-[1.1fr,0.9fr] gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 text-xs font-semibold border border-fuchsia-500/30 bg-fuchsia-500/10 rounded-full px-3 py-1 text-fuchsia-300 mb-4">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              AI Security — Controlled Add-on
            </div>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
              Protect your AI apps<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-fuchsia-400 to-cyan-400">
                without another console.
              </span>
            </h1>
            <p className="mt-5 text-lg leading-8 text-text-muted max-w-xl">
              AI Shield monitors your LLM-powered applications for prompt injection, data leakage,
              and policy violations — and feeds every finding into the same SentinelGrid workflow
              your team already uses.
            </p>
            <div className="mt-5 rounded-2xl border border-fuchsia-500/20 bg-fuchsia-500/10 p-4 text-sm leading-6 text-text-main/80 max-w-2xl">
              <span className="font-semibold text-fuchsia-300">{aiShieldAddon.availabilityLabel}:</span>{" "}
              {aiShieldAddon.launchNote}
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <TrackedLink
                href="/pricing"
                eventName="marketing_cta_click"
                eventProps={{ source: "ai_shield_hero", target: "pricing" }}
                className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-fuchsia-500 to-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:brightness-110 transition-all"
              >
                Talk through the AI Shield add-on
              </TrackedLink>
              <TrackedLink
                href="/demo"
                eventName="marketing_cta_click"
                eventProps={{ source: "ai_shield_hero", target: "demo" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-fuchsia-400 transition-colors"
              >
                See a live demo
              </TrackedLink>
            </div>
          </div>

          {/* Architecture flow */}
          <div className="rounded-xl border border-border bg-bg-alt/80 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fuchsia-300 mb-4">
              How it works
            </p>
            <div className="space-y-3">
              {architecture.map((step, i) => (
                <div key={step.label} className="flex items-center gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-fuchsia-500/10 text-sm font-semibold text-fuchsia-300 flex-shrink-0">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-text-main">{step.label}</p>
                    <p className="text-xs text-text-muted/70">{step.description}</p>
                  </div>
                  {i < architecture.length - 1 && (
                    <svg className="w-4 h-4 text-slate-600 flex-shrink-0" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5L12 21m0 0l-7.5-7.5M12 21V3" />
                    </svg>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-10 rounded-xl border border-border bg-bg-alt/80 p-6">
          <div className="grid gap-6 lg:grid-cols-[1.05fr,0.95fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
                Package story
              </p>
              <h2 className="mt-3 text-2xl font-semibold text-text-main">
                {aiShieldAddon.positioning}
              </h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">{aiShieldAddon.description}</p>
              <p className="mt-3 text-sm leading-6 text-text-main/80">{aiShieldAddon.launchNote}</p>
            </div>
            <div className="grid gap-3">
              {aiShieldAddon.packageFit.map((entry) => (
                <div key={entry.label} className="rounded-2xl border border-border bg-bg/80 p-4">
                  <p className="text-sm font-semibold text-text-main">{entry.label}</p>
                  <p className="mt-2 text-sm leading-6 text-text-muted">{entry.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Threat coverage */}
      <section className="max-w-7xl mx-auto px-6 py-16 border-t border-border">
        <div className="text-center mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Threat Coverage
          </p>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
            AI-native threats need AI-native defense.
          </h2>
          <p className="mt-4 text-text-muted max-w-2xl mx-auto">
            Traditional security tools were not designed for LLM applications. AI Shield covers the
            launch-supported attack surface that matters now without pretending every provider path is equally ready.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {threats.map((threat) => (
            <div
              key={threat.title}
              className="rounded-xl border border-border bg-bg-alt/80 p-6 hover:border-fuchsia-500/30 transition-colors"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-fuchsia-500/10 flex items-center justify-center text-fuchsia-400 flex-shrink-0">
                  {threat.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-lg font-semibold text-text-main">{threat.title}</h3>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-fuchsia-300 bg-fuchsia-500/10 border border-fuchsia-500/20 px-2 py-0.5 rounded-full">
                      {threat.stat}
                    </span>
                  </div>
                  <p className="text-sm leading-6 text-text-muted">{threat.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Differentiators */}
      <section className="max-w-7xl mx-auto px-6 py-16 border-t border-border">
        <div className="text-center mb-12">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Why SentinelGrid
          </p>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight">
            AI security that fits how you already work.
          </h2>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {differentiators.map((d) => (
            <div
              key={d.title}
              className="rounded-xl border border-cyan-500/20 bg-gradient-to-br from-cyan-500/5 to-fuchsia-500/5 p-6"
            >
              <h3 className="text-lg font-semibold text-text-main mb-2">{d.title}</h3>
              <p className="text-sm leading-6 text-text-muted">{d.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-6 py-16 border-t border-border">
        <div className="rounded-xl border border-fuchsia-500/20 bg-gradient-to-r from-fuchsia-500/10 to-cyan-500/10 p-8 md:p-12 text-center">
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-4">
            Your AI applications deserve real security.
          </h2>
          <p className="text-text-muted max-w-2xl mx-auto mb-8">
            Add AI runtime security through the launch-supported path and keep the same platform, same workflow, and same trust story.
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <TrackedLink
              href="/pricing"
              eventName="marketing_cta_click"
              eventProps={{ source: "ai_shield_bottom_cta", target: "pricing" }}
              className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-fuchsia-500 to-cyan-400 px-8 py-3.5 text-sm font-semibold text-slate-950 hover:brightness-110 transition-all"
            >
              See pricing and packages
            </TrackedLink>
            <TrackedLink
              href="/product"
              eventName="marketing_cta_click"
              eventProps={{ source: "ai_shield_bottom_cta", target: "product" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-8 py-3.5 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              See the full platform
            </TrackedLink>
          </div>
        </div>
      </section>

      <ProofSection ctaSource="ai_shield_proof" compact showProductCta={false} />
      <Footer />
    </main>
  );
}
