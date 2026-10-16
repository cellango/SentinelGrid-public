const comparisonRows = [
  {
    label: "Primary motion",
    sentinelGrid: "Unified operator workflow for SMB and mid-market teams",
    wiz: "Enterprise-first cloud security and exposure prioritization",
  },
  {
    label: "Buyer fit",
    sentinelGrid: "Teams that need fewer tools and faster time to first value",
    wiz: "Teams optimizing for CNAPP breadth and deeper enterprise cloud programs",
  },
  {
    label: "Packaging",
    sentinelGrid: "Outcome-based packages with public starting prices",
    wiz: "Sales-led enterprise packaging",
  },
  {
    label: "Default story",
    sentinelGrid:
      "Identity, cloud, posture, qualified endpoint coverage, and optional AI runtime security in one queue",
    wiz: "Agentless cloud visibility plus graph-driven prioritization",
  },
  {
    label: "SMB appeal",
    sentinelGrid: "Guided remediation and simpler buying motion",
    wiz: "Powerful, but can feel heavy for smaller teams",
  },
];

export function ComparisonTable() {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-bg-alt/80">
      <div className="grid grid-cols-[1fr,1fr,1fr] border-b border-border bg-bg/70">
        <div className="px-5 py-4 text-sm font-semibold text-text-main/80">Category</div>
        <div className="px-5 py-4 text-sm font-semibold text-cyan-300">SentinelGrid</div>
        <div className="px-5 py-4 text-sm font-semibold text-text-muted">Wiz</div>
      </div>
      {comparisonRows.map((row) => (
        <div key={row.label} className="grid grid-cols-[1fr,1fr,1fr] border-b border-border last:border-b-0">
          <div className="px-5 py-4 text-sm font-medium text-text-main">{row.label}</div>
          <div className="px-5 py-4 text-sm leading-6 text-text-muted">{row.sentinelGrid}</div>
          <div className="px-5 py-4 text-sm leading-6 text-text-muted/70">{row.wiz}</div>
        </div>
      ))}
    </div>
  );
}
