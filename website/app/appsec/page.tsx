import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const coverage = [
  {
    title: "Static code & secrets (SAST)",
    points: [
      "Language-aware checks for injection, auth/session flaws, deserialization, and risky patterns",
      "Secret/key detection in code and history with revoke/rotate playbooks",
      "Pull-request guardrails and suppressions to keep signal high without blocking shipping",
    ],
  },
  {
    title: "Infrastructure as Code",
    points: [
      "Terraform/K8s/CloudFormation misconfig checks (network exposure, IAM drift, encryption, logging)",
      "Baseline policies for critical resources; drift alerts when configs change after approval",
      "Environment snapshots for evidence and fast retest after fixes",
    ],
  },
  {
    title: "Dependencies & containers",
    points: [
      "SBOM + CVE sweep for app dependencies and base images",
      "OS/package hardening checks and pinned-version guidance",
      "Fix groups with upgrade paths and retest automation after changes",
    ],
  },
  {
    title: "Cloud posture",
    points: [
      "Account-level posture checks: identity, storage, network, logging/monitoring",
      "Public exposure, key hygiene, and permission sprawl detection",
      "Findings mapped to action plans and tickets with SLAs",
    ],
  },
  {
    title: "Dynamic app probes (DAST)",
    points: [
      "Authenticated and unauthenticated probes for auth/session, input validation, and configuration issues",
      "Safe-mode testing options; rerun after fixes to prove closure",
      "Findings routed to tickets with reproduction steps and impact notes",
    ],
  },
  {
    title: "Ticketing, playbooks, retest",
    points: [
      "Auto-ticketing with evidence, suggested owners, and severity guidance",
      "Built-in playbooks for rotate/redeploy/reconfigure; we run them or hand off to your team",
      "Retest on close and dashboards that track risk burn-down over time",
    ],
  },
];

export default function AppSecPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="text-center max-w-4xl mx-auto">
          <span className="inline-flex items-center text-xs font-semibold border border-cyan-500/30 rounded-full px-4 py-1.5 text-cyan-400 mb-6 bg-cyan-500/5">
            Application & Cloud Security
          </span>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
            Static, dynamic, and cloud checks.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              Managed for outcomes.
            </span>
          </h1>
          <p className="text-xl text-slate-300 leading-relaxed mb-8">
            One program that covers code, infrastructure, dependencies, secrets, cloud posture,
            and web apps. We run the scanners, triage noise, open tickets, and retest fixes—without
            naming tools or locking you to a vendor.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Run a scan with us
            </Link>
            <Link
              href="/#pricing"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              See pricing
            </Link>
          </div>
          <div className="mt-6 inline-flex flex-wrap items-center gap-3 text-xs text-slate-400 justify-center">
            <span className="px-3 py-1 rounded-full border border-cyan-500/40 text-cyan-300">
              SAST + secrets + IaC + dependencies
            </span>
            <span className="px-3 py-1 rounded-full border border-cyan-500/40 text-cyan-300">
              Cloud posture and drift alerts
            </span>
            <span className="px-3 py-1 rounded-full border border-cyan-500/40 text-cyan-300">
              DAST with retest + ticketing
            </span>
          </div>
        </div>
      </section>

      {/* Coverage */}
      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">What we cover</h2>
            <p className="text-slate-400 text-lg max-w-3xl mx-auto">
              Full-surface scanning across code, infrastructure, cloud accounts, and running apps.
              Findings ship with tickets, playbooks, and retests so the fix actually gets verified.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {coverage.map((item) => (
              <div
                key={item.title}
                className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-slate-800 rounded-2xl p-6"
              >
                <h3 className="text-xl font-semibold text-slate-100 mb-3">{item.title}</h3>
                <ul className="space-y-2 text-sm text-slate-300">
                  {item.points.map((point) => (
                    <li key={point} className="flex items-start gap-2">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Scan without vendor lock</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              We run the right static, dynamic, IaC, dependency, and cloud posture checks for your
              stack. The underlying scanners can change over time; the outcomes stay consistent.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Ticketed fixes & playbooks</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Findings are deduped, prioritized, and opened as tickets with evidence, suggested
              owners, and remediation steps. We can execute the playbooks or hand them to your team.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Retest and prove closure</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Every fix can be retested on demand. Dashboards track risk burn-down, SLA adherence,
              and evidence for compliance without a separate reporting tool.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 border border-cyan-500/20 rounded-3xl p-10 text-center">
          <h3 className="text-3xl font-semibold mb-3">Ready to see coverage end to end?</h3>
          <p className="text-slate-300 text-sm md:text-base max-w-3xl mx-auto mb-6">
            Give us a repo, cloud account, or app URL and we&apos;ll return tickets, playbooks, and
            a retest plan—without asking you to pick tools.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Start a scan
            </Link>
            <Link
              href="/contact"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              Talk with an engineer
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
