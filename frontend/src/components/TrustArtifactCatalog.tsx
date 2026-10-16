import type { ReactNode } from "react";
import type { TrustArtifactDefinition } from "@/lib/trustArtifacts";

type Variant = "dark" | "light";

interface TrustArtifactCatalogProps {
  artifacts: TrustArtifactDefinition[];
  variant?: Variant;
  actionRenderer?: (artifact: TrustArtifactDefinition) => ReactNode;
}

function classesForVariant(variant: Variant) {
  if (variant === "dark") {
    return {
      card: "rounded-3xl border border-surface-card-border bg-surface-card p-6",
      eyebrow: "text-primary",
      title: "text-text-main",
      body: "text-text-muted",
      pill: "border border-border-faint bg-surface-hover text-text-main",
      section: "border border-border-faint bg-surface-hover text-text-muted",
      divider: "border-border-faint",
      metaLabel: "text-text-muted",
      metaValue: "text-text-main",
    };
  }

  return {
    card: "rounded-3xl border border-surface-card-border bg-surface-card p-6 shadow-sm",
    eyebrow: "text-primary",
    title: "text-text-main",
    body: "text-text-muted",
    pill: "border border-border-faint bg-surface-hover text-text-main",
    section: "border border-border-faint bg-surface-hover text-text-muted",
    divider: "border-border-faint",
    metaLabel: "text-text-muted",
    metaValue: "text-text-main",
  };
}

export function TrustArtifactCatalog({
  artifacts,
  variant = "dark",
  actionRenderer,
}: TrustArtifactCatalogProps) {
  const classes = classesForVariant(variant);

  return (
    <div className="grid gap-6 xl:grid-cols-3">
      {artifacts.map((artifact) => (
        <div key={artifact.id} className={classes.card}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className={`text-xs font-semibold uppercase tracking-[0.14em] ${classes.eyebrow}`}>
                Trust artifact
              </p>
              <h3 className={`mt-3 text-2xl font-semibold ${classes.title}`}>{artifact.title}</h3>
            </div>
            <span className={`rounded-full px-3 py-1 text-xs font-medium ${classes.pill}`}>
              {artifact.templateKey.replace(/_/g, " ")}
            </span>
          </div>

          <p className={`mt-4 text-sm leading-6 ${classes.body}`}>{artifact.summary}</p>

          <dl className={`mt-5 grid gap-4 border-t pt-5 ${classes.divider}`}>
            <div>
              <dt className={`text-xs uppercase tracking-wide ${classes.metaLabel}`}>Audience</dt>
              <dd className={`mt-1 text-sm ${classes.metaValue}`}>{artifact.audience}</dd>
            </div>
            <div>
              <dt className={`text-xs uppercase tracking-wide ${classes.metaLabel}`}>Delivery</dt>
              <dd className={`mt-1 text-sm ${classes.metaValue}`}>{artifact.delivery}</dd>
            </div>
            <div>
              <dt className={`text-xs uppercase tracking-wide ${classes.metaLabel}`}>Refresh cadence</dt>
              <dd className={`mt-1 text-sm ${classes.metaValue}`}>{artifact.refreshCadence}</dd>
            </div>
          </dl>

          <div className="mt-5">
            <p className={`text-xs uppercase tracking-wide ${classes.metaLabel}`}>Included sections</p>
            <div className="mt-3 space-y-2">
              {artifact.sections.map((section) => (
                <div key={`${artifact.id}-${section}`} className={`rounded-2xl px-3 py-2 text-sm ${classes.section}`}>
                  {section}
                </div>
              ))}
            </div>
          </div>

          {actionRenderer ? <div className="mt-5">{actionRenderer(artifact)}</div> : null}
        </div>
      ))}
    </div>
  );
}
