import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { AiShieldPlatformSection } from "@/components/marketing/AiShieldPlatformSection";
import { Footer } from "@/components/Footer";
import { LaunchPackageMatrix } from "@/components/marketing/LaunchPackageMatrix";
import { ProofSection } from "@/components/marketing/ProofSection";
import { TrackedLink } from "@/components/marketing/TrackedLink";
import { launchWorkflowSteps } from "@/lib/marketing/launchWorkflow";

export const metadata: Metadata = {
  title: "SentinelGrid Product",
  description:
    "SentinelGrid packages identity, cloud, posture, qualified endpoint coverage, and optional AI runtime security into one launch-scoped workflow built around one queue and one guided action model.",
};

const domains = [
  {
    title: "Identity",
    description: "Access hygiene, risky accounts, access reviews, and policy gaps tied back to real operator work.",
  },
  {
    title: "Cloud",
    description: "Posture and exposure findings surfaced in the same queue that drives incident and remediation work.",
  },
  {
    title: "Endpoint",
    description:
      "A qualified endpoint coverage path and SentinelGuard response workflows built into the same operator workflow instead of another isolated console.",
  },
  {
    title: "Posture",
    description: "Security posture and asset risk that supports operators, leaders, and compliance conversations.",
  },
  {
    title: "AI Shield",
    description:
      "A controlled AI runtime security add-on on the approved launch provider path, landing in the same queue, guided action packs, and trust workflow instead of a detached AI console.",
  },
  {
    title: "Reporting",
    description:
      "Leadership-friendly summaries and the narrowed launch evidence subset generated from the same operating record.",
  },
];

export default function ProductPage() {
  return (
    <main className="min-h-screen bg-bg text-text-main">
      <Header />
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid gap-10 lg:grid-cols-[1.05fr,0.95fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
              Product
            </p>
            <h1 className="text-4xl md:text-6xl font-semibold tracking-tight">
              Security operations without five consoles.
            </h1>
            <p className="mt-5 text-lg leading-8 text-text-muted">
              SentinelGrid packages identity, cloud, posture, qualified endpoint coverage, and
              optional AI runtime security into one launch-scoped operator workflow so lean teams
              can move from first connection to first guided action without platform sprawl.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href="/signup"
                eventName="marketing_cta_click"
                eventProps={{ source: "product_page_hero", target: "signup" }}
                className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Start guided onboarding
              </TrackedLink>
              <TrackedLink
                href="/walkthrough"
                eventName="marketing_cta_click"
                eventProps={{ source: "product_page_hero", target: "walkthrough" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-6 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                See the operator workflow
              </TrackedLink>
            </div>
          </div>

          <div className="rounded-xl border border-border bg-bg-alt/80 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Unified queue
            </p>
            <ul className="mt-4 space-y-4">
              {launchWorkflowSteps.map((item, index) => (
                <li key={item.id} className="flex gap-3">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-cyan-500/10 text-sm font-semibold text-cyan-300">
                    {index + 1}
                  </span>
                  <div className="pt-1">
                    <p className="text-sm font-semibold text-text-main">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-text-muted">{item.description}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-14">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Queue inputs
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-text-main">
              These domains feed the same operating record.
            </h2>
            <p className="mt-3 text-sm leading-6 text-text-muted">
              The launch package should read like one queue with shared response and evidence, not
              a shopping list of separate modules.
            </p>
          </div>
        </div>

        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {domains.map((domain) => (
            <div key={domain.title} className="rounded-xl border border-border bg-bg-alt/80 p-6">
              <h2 className="text-xl font-semibold text-text-main">{domain.title}</h2>
              <p className="mt-3 text-sm leading-6 text-text-muted">{domain.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-14 rounded-xl border border-cyan-500/20 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 p-8">
          <h2 className="text-2xl font-semibold text-text-main">Start with the operator workflow, not the module list.</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-text-main/80">
            The product story for SMB does not need to mimic enterprise CNAPP marketing. It needs
            to show how the team moves from connection to action and from action to reporting with
            less friction.
          </p>
        </div>
      </section>
      <LaunchPackageMatrix
        source="product_page_launch_package"
        title="How the launch package is segmented"
        description="Product, pricing, demo, and trust language should all map to the same categories: production now, controlled add-on, qualified sales-assisted scope, and out of scope."
      />
      <AiShieldPlatformSection
        source="product_page_ai_shield_section"
        title="AI Shield is part of the launch story, but it is still a controlled add-on."
        description="The main SentinelGrid value proposition is one operating plane. AI Shield extends that plane to runtime AI events, AI-specific guided action packs, and AI governance evidence without forcing teams into a separate product or separate procurement story, but launch support stays scoped to the production-real provider path."
      />
      <ProofSection ctaSource="product_page_proof" compact showProductCta={false} />
      <Footer />
    </main>
  );
}
