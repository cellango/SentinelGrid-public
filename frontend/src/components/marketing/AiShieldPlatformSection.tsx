import { aiShieldAddon } from "@/lib/marketing/packages";
import { TrackedLink } from "./TrackedLink";

interface AiShieldPlatformSectionProps {
  source: string;
  eyebrow?: string;
  title?: string;
  description?: string;
}

export function AiShieldPlatformSection({
  source,
  eyebrow = "AI Security",
  title = "AI risk uses the same queue and guided action packs, not another product tab.",
  description = "AI Shield extends the main SentinelGrid operator path to AI apps. Buyers should understand that AI runtime findings feed the same queue, guided action packs, ownership workflow, and trust evidence layer as the rest of the platform, but the launch path is intentionally controlled.",
}: AiShieldPlatformSectionProps) {
  return (
    <section className="py-20 px-6 border-t border-border">
      <div className="max-w-7xl mx-auto">
        <div className="grid gap-10 lg:grid-cols-[1.1fr,0.9fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-fuchsia-300 mb-3">
              {eyebrow}
            </p>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
              {title}
            </h2>
            <p className="mt-4 max-w-3xl text-lg leading-8 text-text-muted">{description}</p>

            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {aiShieldAddon.highlights.map((highlight) => (
                <div
                  key={highlight.title}
                  className="rounded-xl border border-fuchsia-500/20 bg-gradient-to-br from-fuchsia-500/10 to-cyan-500/5 p-5"
                >
                  <p className="text-sm font-semibold text-text-main">{highlight.title}</p>
                  <p className="mt-3 text-sm leading-6 text-text-muted">{highlight.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-border bg-bg-alt/80 p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300">
              Package fit
            </p>
            <p className="mt-3 text-sm leading-6 text-text-muted">{aiShieldAddon.positioning}</p>
            <p className="mt-3 text-sm leading-6 text-text-main/80">{aiShieldAddon.launchNote}</p>
            <div className="mt-5 space-y-4">
              {aiShieldAddon.packageFit.map((entry) => (
                <div
                  key={entry.label}
                  className="rounded-2xl border border-border bg-bg/80 p-4"
                >
                  <p className="text-sm font-semibold text-text-main">{entry.label}</p>
                  <p className="mt-2 text-sm leading-6 text-text-muted">{entry.description}</p>
                </div>
              ))}
            </div>
            <div className="mt-6 flex flex-wrap gap-3">
              <TrackedLink
                href={aiShieldAddon.ctaHref}
                eventName="marketing_cta_click"
                eventProps={{ source, target: "ai_shield_page" }}
                className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-fuchsia-500 to-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:brightness-110 transition-all"
              >
                {aiShieldAddon.ctaLabel}
              </TrackedLink>
              <TrackedLink
                href="/pricing"
                eventName="marketing_cta_click"
                eventProps={{ source, target: "pricing" }}
                className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
              >
                See packages and pricing
              </TrackedLink>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
