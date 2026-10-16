import { customerProfiles } from "@/lib/marketing/customerProfiles";
import { TrackedLink } from "@/components/marketing/TrackedLink";

type CustomerStoryCardsProps = {
  source: string;
  compact?: boolean;
  showCta?: boolean;
};

export function CustomerStoryCards({
  source,
  compact = false,
  showCta = true,
}: CustomerStoryCardsProps) {
  const sectionPadding = compact ? "py-14" : "py-20";

  return (
    <section className={`${sectionPadding} px-6 bg-bg-alt/20`}>
      <div className="max-w-7xl mx-auto">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-cyan-300 mb-3">
            Customer Stories
          </p>
          <h2 className="text-3xl md:text-5xl font-semibold tracking-tight text-text-main">
            Proof in the format buyers actually use internally.
          </h2>
          <p className="mt-4 text-lg leading-8 text-text-muted">
            These story cards are anonymized representative customer motions for the SMB segment.
            They are designed to show the role, company size, deployment path, and outcome shape a
            buyer should expect, even before named public references are available.
          </p>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-3">
          {customerProfiles.map((profile) => (
            <article
              key={profile.key}
              className="rounded-[30px] border border-border bg-bg/70 p-6 shadow-[0_20px_60px_rgba(2,6,23,0.35)]"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
                  Representative story
                </span>
                <span className="rounded-full border border-border-muted px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text-muted">
                  {profile.companySize}
                </span>
              </div>

              <h3 className="mt-4 text-2xl font-semibold tracking-tight text-text-main">
                {profile.label}
              </h3>
              <p className="mt-3 text-sm leading-6 text-text-muted">{profile.role}</p>

              <div className="mt-5 rounded-2xl border border-border bg-bg-alt/90 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                  Primary challenge
                </p>
                <p className="mt-2 text-sm leading-6 text-text-main/80">
                  {profile.primaryChallenge}
                </p>
              </div>

              <div className="mt-4 rounded-2xl border border-border bg-bg-alt/90 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                  Deployment path
                </p>
                <p className="mt-2 text-sm leading-6 text-text-main/80">
                  {profile.deploymentPath}
                </p>
              </div>

              <div className="mt-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-300">
                  Outcome shape
                </p>
                <p className="mt-2 text-sm font-medium text-text-main">
                  {profile.measurableOutcome}
                </p>
                <p className="mt-2 text-sm leading-6 text-text-main/80">
                  {profile.firstWeekOutcome}
                </p>
              </div>

              <blockquote className="mt-5 rounded-2xl border border-cyan-500/20 bg-cyan-500/5 p-4">
                <p className="text-base leading-7 text-text-main">&ldquo;{profile.storyQuote}&rdquo;</p>
                <footer className="mt-3 text-xs uppercase tracking-[0.14em] text-cyan-300">
                  {profile.storyQuoteLabel}
                </footer>
              </blockquote>

              <div className="mt-5 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                <span className="rounded-full border border-border-muted px-3 py-1">
                  {profile.companyType}
                </span>
                <span className="rounded-full border border-border-muted px-3 py-1">
                  {profile.packageFit}
                </span>
              </div>
            </article>
          ))}
        </div>

        {showCta ? (
          <div className="mt-8 flex flex-wrap gap-3">
            <TrackedLink
              href="/customers"
              eventName="marketing_nav_click"
              eventProps={{ source, target: "customers" }}
              className="inline-flex items-center justify-center rounded-full border border-border-muted px-5 py-3 text-sm font-semibold text-text-main hover:border-cyan-400 transition-colors"
            >
              Review the full customer page
            </TrackedLink>
            <TrackedLink
              href="/demo"
              eventName="marketing_cta_click"
              eventProps={{ source, target: "demo" }}
              className="inline-flex items-center justify-center rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Book a proof-focused demo
            </TrackedLink>
          </div>
        ) : null}
      </div>
    </section>
  );
}
