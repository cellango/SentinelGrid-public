import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const quickHits = [
  "Real-time endpoint telemetry with MITRE-mapped detections",
  "Playbooks isolate hosts, kill processes, sweep for IoCs, and block malicious hashes or ports",
  "Approvals for customer-managed SOCs; one-click containment when SentinelGrid runs it for you",
];

const whatsIncluded = [
  {
    title: "Multi-OS coverage",
    description:
      "SentinelGuard agents for Windows, macOS, and Linux with process, file, and network visibility from day one.",
  },
  {
    title: "Integrity and exposure checks",
    description:
      "File integrity monitoring, rootkit detection, vulnerability and asset inventory without extra tooling to wire up.",
  },
  {
    title: "Detection quality",
    description:
      "IOC hits and behavioral detections tuned for ransomware, phishing, and lateral movement with ATT&CK mapping.",
  },
  {
    title: "Automated playbooks",
    description:
      "Containment, process kill, port and hash blocks, forensic captures, and live scripts from the same console.",
  },
  {
    title: "Dashboards and enrichment",
    description:
      "SOC-ready dashboards plus AI explanations, recommended actions, and mapped controls for every alert.",
  },
  {
    title: "Built for multi-tenant",
    description:
      "Per-tenant isolation and approvals so customer-managed SOCs keep control while shared tenants stay hands-off.",
  },
];

const responsePillars = [
  {
    title: "Approvals where you need them",
    description:
      "Customer-managed SOCs can keep approvals in place before isolation or process kill. Managed tenants get instant containment.",
  },
  {
    title: "Automation with guardrails",
    description:
      "Playbooks launch from detections, tickets, or manual commands with full audit trails and tenant scoping.",
  },
  {
    title: "Ticketing in the loop",
    description:
      "Every response updates tickets so security, IT, and ops stay aligned without extra connectors.",
  },
];

const alreadyAvailable = [
  {
    title: "Behavioral analytics",
    description:
      "Process, script, and network behavioral models mapped to MITRE to surface early-stage attacks with less noise.",
  },
  {
    title: "Full telemetry",
    description:
      "Kernel-level context, file/registry/network visibility, hunt results, and sidecar health rolled into one view.",
  },
  {
    title: "Live response",
    description:
      "Pre-built forensic collections and guided remediation flows so analysts contain and investigate from one console.",
  },
];

const fit = [
  {
    title: "Part of the SentinelGrid stack",
    description:
      "EDR, IAM, cloud posture, SIEM search, and ticketing share policy, identity, and automation in one place.",
  },
  {
    title: "Managed or co-managed",
    description:
      "Use SentinelGuard as your SOC or keep your analysts in the loop with approvals and shared runbooks.",
  },
  {
    title: "Deploy in days",
    description:
      "Ship a single agent bundle, get dashboards and playbooks immediately, and avoid stitching consoles together.",
  },
];

export default function EdrPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid md:grid-cols-[1.1fr,0.9fr] gap-12 items-center">
          <div>
            <span className="inline-flex items-center text-xs font-semibold border border-cyan-500/30 rounded-full px-4 py-1.5 text-cyan-400 mb-4 bg-cyan-500/5">
              SentinelGuard Endpoint Detection & Response
            </span>
            <h1 className="text-4xl md:text-5xl font-semibold tracking-tight leading-tight">
              Endpoint Detection & Response built into SentinelGrid
            </h1>
            <p className="mt-4 text-lg text-slate-300 max-w-2xl leading-relaxed">
              Real-time detection and automated response without juggling agents or consoles.
              SentinelGuard brings telemetry, containment, and ticketing into the same flow your team already uses.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/demo"
                className="inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
              >
                Request a demo
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium border border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
              >
                See alert → response flow
              </Link>
            </div>
            <div className="mt-6 grid sm:grid-cols-2 gap-3 text-sm text-slate-300">
              {quickHits.map((item) => (
                <div
                  key={item}
                  className="flex items-start gap-2 bg-slate-900/50 border border-slate-800 rounded-xl p-3"
                >
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <p className="leading-relaxed">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 shadow-xl">
            <p className="text-xs text-slate-400 mb-3 font-medium">Example playbook</p>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-amber-400 mt-1.5"></div>
                <div className="flex-1">
                  <p className="font-semibold text-sm text-slate-200">
                    Suspicious PowerShell on finance laptop
                  </p>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                    SentinelGuard correlated script block logging, new child process, and outbound connections.
                    Tagged MITRE T1059.001 and linked to ransomware precursors seen in this tenant.
                  </p>
                  <div className="mt-3 flex gap-2 flex-wrap">
                    <span className="px-2 py-1 text-xs bg-amber-500/20 text-amber-200 rounded border border-amber-500/40">
                      Medium
                    </span>
                    <span className="px-2 py-1 text-xs bg-slate-800 text-slate-200 rounded">
                      PowerShell
                    </span>
                    <span className="px-2 py-1 text-xs bg-slate-800 text-slate-200 rounded">
                      MITRE T1059.001
                    </span>
                  </div>
                  <div className="mt-4 grid sm:grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                      <p className="text-slate-300 font-semibold mb-1">Automated</p>
                      <p className="text-slate-400 leading-relaxed">
                        Host isolation queued with approval. Hash blocked on next execution.
                      </p>
                    </div>
                    <div className="bg-slate-900 border border-slate-800 rounded-lg p-3">
                      <p className="text-slate-300 font-semibold mb-1">After approval</p>
                      <p className="text-slate-400 leading-relaxed">
                        Kill suspicious process, sweep for IoCs, and open ticket with forensic bundle.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6">
            <div>
              <h2 className="text-3xl md:text-4xl font-semibold mb-3">What you get today</h2>
              <p className="text-slate-400 max-w-3xl">
                Endpoint coverage, detections, and response ready on day one — no multi-tool integrations required.
              </p>
            </div>
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-5 py-2 text-sm font-medium border border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors w-fit"
            >
              Watch it live
            </Link>
          </div>
          <div className="mt-8 grid md:grid-cols-2 gap-5">
            {whatsIncluded.map((item) => (
              <div
                key={item.title}
                className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 hover:border-cyan-500/40 transition-colors"
              >
                <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-4xl font-semibold mb-3">Automated response with approvals</h2>
            <p className="text-slate-400 max-w-3xl mx-auto">
              We pair automation with control. Customer-managed SOCs can keep approvals; fully managed tenants get instant containment.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-5">
            {responsePillars.map((item) => (
              <div
                key={item.title}
                className="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 hover:border-cyan-500/40 transition-colors"
              >
                <h3 className="text-lg font-semibold mb-2">{item.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-6 items-start">
            <div>
              <h2 className="text-3xl md:text-4xl font-semibold mb-3">What’s live now</h2>
              <p className="text-slate-400 mb-6">
                Endpoint telemetry, detections, and response are available today—no roadmap placeholders.
              </p>
              <div className="space-y-4">
                {alreadyAvailable.map((item) => (
                  <div
                    key={item.title}
                    className="bg-slate-900 border border-slate-800 rounded-2xl p-5 hover:border-cyan-500/40 transition-colors"
                  >
                    <h3 className="text-lg font-semibold mb-1">{item.title}</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">{item.description}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl border border-slate-800 p-6">
              <h3 className="text-xl font-semibold mb-3">How it fits with SentinelGrid</h3>
              <p className="text-slate-300 text-sm leading-relaxed">
                Endpoint coverage plugs directly into detections, ticketing, AI co-pilot, and IAM so you get a coherent security story without gluing products together.
              </p>
              <div className="mt-5 space-y-3">
                {fit.map((item) => (
                  <div key={item.title} className="flex gap-3">
                    <div className="w-10 h-10 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-cyan-400 text-sm font-semibold">
                      ✓
                    </div>
                    <div>
                      <p className="text-slate-200 font-semibold">{item.title}</p>
                      <p className="text-slate-400 text-sm leading-relaxed">{item.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-2xl p-8 md:p-10 text-center">
          <h2 className="text-3xl font-semibold mb-3">See SentinelGuard EDR live</h2>
          <p className="text-slate-300 max-w-3xl mx-auto mb-6">
            Walk through detections, approvals, and automated containment on real demo data. No extra setup, no separate agents to manage.
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Book a demo
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center justify-center rounded-full px-6 py-3 text-sm font-medium border border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              Start in the dashboard
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
