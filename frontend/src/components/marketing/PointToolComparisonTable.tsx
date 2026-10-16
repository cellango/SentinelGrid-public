const comparisonRows = [
  {
    label: "Default operating model",
    sentinelGrid:
      "One operator queue for launch-scoped cloud, identity, posture, qualified endpoint coverage, and optional AI runtime security.",
    pointTools: "Multiple dashboards, separate queues, and manual handoffs between tools.",
  },
  {
    label: "Context and correlation",
    sentinelGrid: "Related findings are grouped into one operating record with ownership and next-step guidance.",
    pointTools: "Analysts or IT owners have to correlate alerts manually across vendors and spreadsheets.",
  },
  {
    label: "Response workflow",
    sentinelGrid: "Guided remediation, ownership, SLAs, ticketing, and response packs in one workflow.",
    pointTools: "Response logic is split across endpoint tools, tickets, chat, and ad hoc runbooks.",
  },
  {
    label: "Commercial model",
    sentinelGrid: "Outcome-based packages with public starting prices and no log-tax headline pricing.",
    pointTools: "Separate contracts, separate onboarding, and hidden cost growth as scope expands.",
  },
  {
    label: "Leadership and trust output",
    sentinelGrid: "The same work can feed leadership reporting, audit exports, and customer review artifacts.",
    pointTools: "Security and trust teams rebuild the same story manually in documents and spreadsheets.",
  },
  {
    label: "AI security fit",
    sentinelGrid:
      "The approved AI Shield launch path extends the same queue, same response model, and same reporting layer.",
    pointTools: "AI runtime tools often create another silo with another workflow and another buyer motion.",
  },
];

export function PointToolComparisonTable() {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-bg-alt/80">
      <div className="grid grid-cols-[0.9fr,1fr,1fr] border-b border-border bg-bg/70">
        <div className="px-5 py-4 text-sm font-semibold text-text-main/80">Category</div>
        <div className="px-5 py-4 text-sm font-semibold text-cyan-300">SentinelGrid</div>
        <div className="px-5 py-4 text-sm font-semibold text-text-muted">
          Point-tool stack
        </div>
      </div>
      {comparisonRows.map((row) => (
        <div
          key={row.label}
          className="grid grid-cols-[0.9fr,1fr,1fr] border-b border-border last:border-b-0"
        >
          <div className="px-5 py-4 text-sm font-medium text-text-main">{row.label}</div>
          <div className="px-5 py-4 text-sm leading-6 text-text-muted">
            {row.sentinelGrid}
          </div>
          <div className="px-5 py-4 text-sm leading-6 text-text-muted/70">{row.pointTools}</div>
        </div>
      ))}
    </div>
  );
}
