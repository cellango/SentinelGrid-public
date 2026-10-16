import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const coverage = [
  { label: "Common Criteria", value: 34, total: 42, highlight: "Mapped to detections, playbooks, and scans" },
  { label: "CCM Alignment", value: 27, total: 32, highlight: "Cloud, identity, and endpoint mapped" },
  { label: "Evidence Items", value: 218, total: 240, highlight: "Auto-collected, timestamped, tenant-scoped" },
];

const reports = [
  { name: "SOC 2 Coverage", type: "Coverage", cadence: "Weekly", status: "Ready" },
  { name: "SOC 2 Evidence Summary", type: "Evidence", cadence: "Weekly", status: "Ready" },
  { name: "CCM Status", type: "Cloud Controls", cadence: "Monthly", status: "Scheduled" },
  { name: "AI Audit Trail", type: "AI Activity", cadence: "On-demand", status: "Ready" },
  { name: "Identity & Access", type: "IAM", cadence: "Weekly", status: "Scheduled" },
  { name: "Endpoint Posture", type: "Endpoint", cadence: "Weekly", status: "Ready" },
  { name: "Incident & Playbooks", type: "Response", cadence: "Monthly", status: "Ready" },
];

const checklist = [
  "Tenant-aware headers on every API call; data isolated per tenant/realm",
  "Evidence and AI activity logs stamped with tenant_id and realm",
  "Playbooks, detections, and scans mapped to SOC 2 criteria",
  "PDF and CSV exports watermarked per tenant with optional share links",
  "Scheduled delivery with per-tenant recipients and expiration",
];

const evidence = [
  { title: "AI activity log", detail: "Guardrails enforced, prompt stored with tenant_id=demo, realm=demo", status: "Recorded" },
  { title: "Identity change", detail: "Access review approval captured with timestamp and approver", status: "Approved" },
  { title: "Endpoint finding", detail: "New agent check-in recorded and linked to SOC 2 CC7.2", status: "Mapped" },
  { title: "Cloud scan", detail: "Configuration drift tied to CCM and SOC 2 CC4.1", status: "Open" },
];

export default function ComplianceLanding() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      <section className="max-w-6xl mx-auto px-6 py-14">
        <div className="grid md:grid-cols-[1.1fr,0.9fr] gap-10 items-start">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-300/80 mb-3">Compliance</p>
            <h1 className="text-4xl md:text-5xl font-semibold leading-tight">
              SOC 2 dashboard — no login needed for this preview
            </h1>
            <p className="mt-5 text-slate-300 text-lg leading-relaxed max-w-xl">
              See how coverage, evidence, and scheduled reports look inside SentinelGrid. This static page mirrors the in-app
              experience without requiring authentication.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/signup"
                className="inline-flex items-center px-6 py-3 rounded-full bg-cyan-400 text-slate-950 font-semibold text-sm hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
              >
                Start trial
              </Link>
              <Link
                href="/trust"
                className="inline-flex items-center px-6 py-3 rounded-full border border-slate-700 text-slate-200 text-sm hover:border-cyan-400 transition-colors"
              >
                View Trust &amp; SOC 2
              </Link>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">Coverage snapshot</span>
              <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                Tenant-aware
              </span>
            </div>
            <div className="space-y-3">
              {coverage.map((item) => {
                const pct = Math.round((item.value / item.total) * 100);
                return (
                  <div key={item.label} className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm text-slate-300">{item.label}</p>
                      <p className="text-sm text-cyan-300 font-semibold">
                        {item.value}/{item.total} ({pct}%)
                      </p>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-cyan-400 to-blue-500" style={{ width: `${pct}%` }} />
                    </div>
                    <p className="text-xs text-slate-400 mt-2">{item.highlight}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="bg-slate-900/40 border-y border-slate-800">
        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
            <div>
              <p className="text-xs uppercase tracking-[0.15em] text-cyan-300">Report library</p>
              <h2 className="text-2xl font-semibold">Pre-built SOC 2 and CCM reports</h2>
              <p className="text-slate-400 text-sm mt-2">
                PDF and CSV downloads, plus scheduled delivery per tenant. No scanner names are exposed—only the outcomes.
              </p>
            </div>
            <div className="flex gap-3">
              <button className="px-4 py-2 text-sm rounded-full bg-slate-800 border border-slate-700 text-slate-200 hover:border-cyan-400">
                Download PDF
              </button>
              <button className="px-4 py-2 text-sm rounded-full bg-slate-800 border border-slate-700 text-slate-200 hover:border-cyan-400">
                Download CSV
              </button>
            </div>
          </div>
          <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/60">
            <div className="grid grid-cols-[1.6fr,1fr,1fr,1fr] px-4 py-3 text-xs uppercase tracking-wide text-slate-400 border-b border-slate-800">
              <span>Name</span>
              <span>Type</span>
              <span>Delivery</span>
              <span>Status</span>
            </div>
            <div className="divide-y divide-slate-800">
              {reports.map((report) => (
                <div key={report.name} className="grid grid-cols-[1.6fr,1fr,1fr,1fr] px-4 py-3 text-sm items-center">
                  <div>
                    <p className="text-slate-100 font-semibold">{report.name}</p>
                    <p className="text-xs text-slate-400">Tenant-stamped exports</p>
                  </div>
                  <span className="text-slate-200">{report.type}</span>
                  <span className="text-slate-300">{report.cadence}</span>
                  <span
                    className={`px-3 py-1 text-xs rounded-full border ${
                      report.status === "Ready"
                        ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                        : "bg-amber-500/10 text-amber-300 border-amber-500/20"
                    }`}
                  >
                    {report.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-6 py-12 grid md:grid-cols-[1.1fr,0.9fr] gap-8">
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <p className="text-xs uppercase tracking-[0.15em] text-cyan-300 mb-2">Evidence &amp; AI audit</p>
          <h3 className="text-xl font-semibold text-slate-100 mb-3">What auditors will see</h3>
          <ul className="space-y-3">
            {checklist.map((item) => (
              <li key={item} className="flex gap-3 text-sm text-slate-200">
                <span className="text-cyan-300">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <div className="mt-6 rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-4 text-sm text-cyan-100">
            Tenant context is attached to every action (tenant_id, realm, user_id) and is validated at the gateway to keep data isolated.
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
          <p className="text-xs uppercase tracking-[0.15em] text-cyan-300 mb-2">Recent evidence</p>
          <div className="space-y-3">
            {evidence.map((item) => (
              <div key={item.title} className="p-4 rounded-xl bg-slate-900/70 border border-slate-800">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-slate-100">{item.title}</p>
                  <span className="text-xs px-2 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    {item.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-12 px-6 bg-slate-900/30">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-3xl font-semibold mb-3">Ready to see it live?</h2>
          <p className="text-slate-300 max-w-2xl mx-auto">
            The authenticated app adds live data, scheduled delivery, and per-tenant evidence export. Start a trial to view your own tenant.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              href="/signup"
              className="inline-flex items-center px-6 py-3 rounded-full bg-cyan-400 text-slate-950 font-semibold text-sm hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Start trial
            </Link>
            <Link
              href="/trust"
              className="inline-flex items-center px-6 py-3 rounded-full border border-slate-700 text-slate-200 text-sm hover:border-cyan-400 transition-colors"
            >
              Learn about tenant isolation
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
