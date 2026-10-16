import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const pillars = [
  {
    title: "Tenant-aware AI",
    description: "Every AI call carries tenant + realm context; caches and vector search stay isolated by tenant. No cross-tenant fallback, ever.",
    icon: "🧠",
  },
  {
    title: "Continuous monitoring",
    description: "Identity, cloud, and endpoint telemetry normalized into one lake, mapped to SOC 2 controls, and scored in real time.",
    icon: "📡",
  },
  {
    title: "Automated evidence & reporting",
    description: "Pre-built SOC 2 reports (coverage, CCM status, evidence summary) plus scheduled delivery in PDF/CSV to your inbox.",
    icon: "📄",
  },
  {
    title: "Approvals and auditability",
    description: "Playbooks, AI actions, and sensitive changes are logged with tenant context and approval state, ready for auditors.",
    icon: "✅",
  },
];

const proofPoints = [
  {
    title: "Control mapping you can show",
    detail: "Detections, playbooks, and scans are tagged to SOC 2 criteria; the dashboard shows coverage, gaps, and remediation.",
  },
  {
    title: "AI answers you can trust",
    detail: "AI Activity page logs every response with tenant/realm, prompt preview, and guardrail decisions for evidence.",
  },
  {
    title: "Evidence on a schedule",
    detail: "Weekly, monthly, or quarterly SOC 2 reports with built-in templates. Share links or download as PDF/CSV.",
  },
  {
    title: "Data stays in your lane",
    detail: "Per-tenant indexes, isolated adapters, and strict header validation on gateways to avoid cross-tenant leakage.",
  },
];

export default function TrustPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      <section className="max-w-6xl mx-auto px-6 py-16 md:py-24">
        <div className="grid md:grid-cols-[1.1fr,0.9fr] gap-10 items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-300/80 mb-3">
              Trust &amp; SOC 2
            </p>
            <h1 className="text-4xl md:text-5xl font-semibold leading-tight">
              Tenant-aware AI with
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
                compliance built in
              </span>
            </h1>
            <p className="mt-5 text-slate-300 text-lg leading-relaxed max-w-xl">
              Show auditors how data is isolated, monitored, and reported. Your SOC 2 dashboard, reports, and AI audit trail live in one place.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href="/dashboard/compliance"
                className="inline-flex items-center justify-center px-6 py-3 rounded-full bg-cyan-400 text-slate-950 font-semibold text-sm hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
              >
                Open SOC 2 Dashboard
              </Link>
              <Link
                href="/#pricing"
                className="inline-flex items-center justify-center px-6 py-3 rounded-full border border-slate-700 text-slate-200 text-sm hover:border-cyan-400 transition-colors"
              >
                See pricing
              </Link>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Already a customer? Sign in and head to Compliance → SOC 2 Dashboard.
            </p>
          </div>

          <div className="bg-gradient-to-br from-slate-900/70 to-slate-800/40 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-400">SOC 2 Coverage</span>
              <span className="text-xs px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                Live
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <p className="text-xs text-slate-400">Common Criteria</p>
                <p className="text-3xl font-semibold">34/42</p>
                <p className="text-[11px] text-cyan-300 mt-1">Mapped to detections &amp; playbooks</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <p className="text-xs text-slate-400">Evidence items</p>
                <p className="text-3xl font-semibold">218</p>
                <p className="text-[11px] text-cyan-300 mt-1">Auto-collected and timestamped</p>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <p className="text-xs text-slate-400 mb-2">AI Activity (tenant-scoped)</p>
              <div className="space-y-2 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Prompt inspected</span>
                  <span className="text-xs text-emerald-300">allowed</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Guardrails</span>
                  <span className="text-xs text-slate-400">no PII, no secrets</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Logged as</span>
                  <span className="text-xs text-slate-400">tenant_id=demo, realm=demo</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-14 px-6 bg-slate-900/30">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-2 gap-6">
            {pillars.map((pillar) => (
              <div
                key={pillar.title}
                className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="text-2xl">{pillar.icon}</div>
                  <h3 className="text-xl font-semibold text-slate-100">{pillar.title}</h3>
                </div>
                <p className="text-slate-300 text-sm leading-relaxed">{pillar.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-4xl font-semibold">Show auditors the receipts</h2>
            <p className="text-slate-400 max-w-3xl mx-auto mt-3">
              From control coverage to AI audit logs, everything is exportable and tied to your tenant.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            {proofPoints.map((item) => (
              <div key={item.title} className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
                <h3 className="text-lg font-semibold text-slate-100 mb-2">{item.title}</h3>
                <p className="text-slate-300 text-sm leading-relaxed">{item.detail}</p>
              </div>
            ))}
          </div>

          <div className="mt-10 grid md:grid-cols-[1.2fr,0.8fr] gap-6 items-center">
            <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/20 rounded-2xl p-6">
              <h3 className="text-xl font-semibold text-slate-100 mb-2">SOC 2 report library</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Coverage, CCM status, and evidence summaries are ready to schedule. Add recipients, pick weekly/monthly/quarterly, and we deliver PDFs and CSVs with your tenant watermark.
              </p>
              <ul className="mt-4 space-y-2 text-sm text-slate-200">
                <li className="flex items-start gap-2">
                  <span className="text-cyan-300 mt-0.5">•</span> Download on demand or auto-deliver
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-300 mt-0.5">•</span> Each report tied to tenant_id/realm
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-cyan-300 mt-0.5">•</span> Share links with optional password protection
                </li>
              </ul>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6">
              <h4 className="text-sm text-slate-400 mb-3 uppercase tracking-[0.15em]">In-app path</h4>
              <div className="space-y-3 text-slate-200 text-sm">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs border border-cyan-500/20">
                    1
                  </span>
                  <span>Dashboard → Compliance → SOC 2 Dashboard</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs border border-cyan-500/20">
                    2
                  </span>
                  <span>Review coverage &amp; AI Activity (tenant-scoped logs)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs border border-cyan-500/20">
                    3
                  </span>
                  <span>Schedule reports or download evidence</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-5xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-semibold mb-3">Ready to show SOC 2 progress?</h2>
          <p className="text-slate-300 max-w-2xl mx-auto">
            Log in and open the SOC 2 dashboard for your tenant. Not a customer yet? Start a trial and keep your AI, evidence, and monitoring tenant-aware from day one.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              href="/dashboard/compliance"
              className="inline-flex items-center px-6 py-3 rounded-full bg-cyan-400 text-slate-950 font-semibold text-sm hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Open SOC 2 Dashboard
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center px-6 py-3 rounded-full border border-slate-700 text-slate-200 text-sm hover:border-cyan-400 transition-colors"
            >
              Start trial
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
