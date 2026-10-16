import { customerProfiles } from "@/lib/marketing/customerProfiles";

export function CustomerProfileGrid() {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {customerProfiles.map((profile) => (
        <article
          key={profile.key}
          className="rounded-[30px] border border-border bg-bg-alt/80 p-6 shadow-[0_20px_60px_rgba(2,6,23,0.28)]"
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-cyan-300">
              {profile.companyType}
            </span>
            <span className="rounded-full border border-border-muted px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-text-muted">
              {profile.companySize}
            </span>
          </div>

          <h2 className="mt-4 text-2xl font-semibold tracking-tight text-text-main">
            {profile.label}
          </h2>
          <p className="mt-3 text-sm leading-6 text-text-muted">{profile.headline}</p>

          <div className="mt-5 space-y-3">
            <div className="rounded-2xl border border-border bg-bg/80 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                Typical owner
              </p>
              <p className="mt-2 text-sm text-text-main/80">{profile.role}</p>
            </div>
            <div className="rounded-2xl border border-border bg-bg/80 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
                Recommended package
              </p>
              <p className="mt-2 text-sm font-semibold text-text-main">{profile.packageFit}</p>
            </div>
          </div>

          <p className="mt-5 text-sm leading-6 text-text-muted">{profile.summary}</p>

          <div className="mt-5 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-300">
              First-week output
            </p>
            <p className="mt-2 text-sm leading-6 text-text-main/80">{profile.firstWeekOutcome}</p>
          </div>

          <div className="mt-5 rounded-2xl border border-border bg-bg/80 p-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted/70">
              Why teams switch
            </p>
            <p className="mt-2 text-sm font-medium text-text-main">{profile.outcomeHighlight}</p>
            <p className="mt-2 text-sm leading-6 text-text-muted">{profile.measurableOutcome}</p>
            <ul className="mt-4 space-y-2">
              {profile.proofPoints.map((point) => (
                <li key={point} className="flex gap-2 text-sm text-text-muted">
                  <span className="mt-0.5 text-cyan-400">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
        </article>
      ))}
    </div>
  );
}
