import { TrackedLink } from "./TrackedLink";

const packageGroups = [
  {
    title: "Production now",
    eyebrow: "Default launch path",
    accent: "text-emerald-300 border-emerald-500/20 bg-emerald-500/10",
    bullets: [
      "Protect for cloud, identity, posture, and baseline detections.",
      "Protect + Defend for the main operator workflow and qualified endpoint coverage.",
      "Protect + Defend + Comply for the narrowed evidence, reporting, and trust-artifact subset.",
    ],
  },
  {
    title: "Controlled add-on",
    eyebrow: "Shown when explicitly relevant",
    accent: "text-fuchsia-300 border-fuchsia-500/20 bg-fuchsia-500/10",
    bullets: [
      "AI Shield only on the approved launch provider path.",
      "AI incidents feed the same queue and trust workflow instead of a separate console.",
      "Unsupported provider paths stay gated until they are equally real and supportable.",
    ],
  },
  {
    title: "Qualified sales-assisted",
    eyebrow: "Needs guided review",
    accent: "text-cyan-300 border-cyan-500/20 bg-cyan-500/10",
    bullets: [
      "Partner and MSP delivery.",
      "Multi-environment or unusual rollout scope.",
      "Complex retention, trust-review, or customer-specific diligence asks.",
    ],
  },
  {
    title: "Out of scope",
    eyebrow: "Not part of the default launch promise",
    accent: "text-amber-200 border-amber-500/20 bg-amber-500/10",
    bullets: [
      "Pentest as part of the initial self-serve SaaS package.",
      "Unsupported AI provider coverage.",
      "Full standalone EDR/XDR replacement or broad enterprise-category parity claims.",
    ],
  },
];

interface LaunchPackageMatrixProps {
  source: string;
  title?: string;
  description?: string;
}

export function LaunchPackageMatrix({
  source,
  title = "What the launch package actually includes",
  description = "The website, demo path, trust packet, and pricing model should all describe the same bounded offer. This is the public launch boundary.",
}: LaunchPackageMatrixProps) {
  return (
    <section className="py-20 px-6 border-t border-border">
      <div className="max-w-7xl mx-auto">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Launch package
          </p>
          <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
            {title}
          </h2>
          <p className="mt-4 text-lg leading-8 text-text-muted">{description}</p>
        </div>

        <div className="mt-10 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {packageGroups.map((group) => (
            <div key={group.title} className="rounded-2xl border border-border bg-bg-alt/80 p-6">
              <div
                className={`inline-flex rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${group.accent}`}
              >
                {group.eyebrow}
              </div>
              <h3 className="mt-4 text-xl font-semibold text-text-main">{group.title}</h3>
              <ul className="mt-4 space-y-3">
                {group.bullets.map((bullet) => (
                  <li key={bullet} className="flex gap-2 text-sm leading-6 text-text-muted">
                    <span className="mt-0.5 text-cyan-400">•</span>
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <TrackedLink
            href="/pricing"
            eventName="marketing_nav_click"
            eventProps={{ source, target: "pricing" }}
            className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Review packages
          </TrackedLink>
          <TrackedLink
            href="/trust"
            eventName="marketing_nav_click"
            eventProps={{ source, target: "trust" }}
            className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Review trust boundaries
          </TrackedLink>
        </div>
      </div>
    </section>
  );
}
