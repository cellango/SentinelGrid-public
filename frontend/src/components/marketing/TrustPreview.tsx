import { TrackedLink } from "./TrackedLink";

const trustPoints = [
  "Tenant-isolated storage and access boundaries",
  "Approval controls for sensitive actions and response workflows",
  "No public-model training on customer telemetry",
  "Standard onboarding included for the core SMB connector path",
  "Qualified partner and AI add-on boundaries explained before diligence starts",
];

export function TrustPreview() {
  return (
    <section className="py-20 px-6 bg-bg-alt/50">
      <div className="max-w-7xl mx-auto grid gap-8 lg:grid-cols-[1.1fr,0.9fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Trust
          </p>
          <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
            Clear boundaries, clear approvals, clear pricing.
          </h2>
          <p className="mt-4 text-lg text-text-muted">
            Buyers need to know where data lives, how automation is controlled, and whether the
            commercial model will surprise them later. The launch trust kit makes those answers
            visible before diligence turns into improvisation.
          </p>
          <TrackedLink
            href="/trust"
            eventName="marketing_nav_click"
            eventProps={{ source: "homepage_trust_preview" }}
            className="mt-6 inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
          >
            Read the trust overview
          </TrackedLink>
        </div>

        <div className="rounded-xl border border-border bg-bg/70 p-6">
          <ul className="space-y-4">
            {trustPoints.map((item) => (
              <li key={item} className="flex gap-3 text-sm text-text-main/80">
                <span className="mt-0.5 text-emerald-400">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
