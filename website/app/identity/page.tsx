import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const capabilities = [
  {
    title: "Identity Provider + SSO",
    points: [
      "Built-in IdP with SSO (OIDC/OAuth) and MFA out of the box",
      "Connect external IdPs (Google Workspace, Microsoft 365/Entra, Okta, Keycloak) without per-user uplift",
      "Session policies, device posture awareness, and conditional access",
    ],
  },
  {
    title: "Drag-and-drop policy editor",
    points: [
      "Visual policy builder to craft least-privilege access without writing DSL",
      "Role-based and attribute-based controls with reusable policy blocks",
      "Preview and simulate policies before enforcement; audit trail on changes",
    ],
  },
  {
    title: "Governance & access hygiene",
    points: [
      "Access reviews, dormant account clean-up, and privileged role monitoring",
      "Just-in-time access requests with approval flows and expirations",
      "Identity posture checks: orphaned admins, key hygiene, risky scopes",
    ],
  },
  {
    title: "App and API access",
    points: [
      "App catalog with SSO enablement and scoped access",
      "OAuth client management with safe defaults and scope guardrails",
      "Service-account governance and rotation playbooks",
    ],
  },
  {
    title: "Security automation",
    points: [
      "Automated remediation for risky access: disable, rotate, or downgrade roles",
      "Ticketing and alerting with evidence and suggested owners",
      "Identity signals feed detections and playbooks across SIEM/SOAR",
    ],
  },
  {
    title: "Audit & compliance",
    points: [
      "Complete audit trail on policy changes, approvals, and sign-ins",
      "Reports mapped to common frameworks for evidence collection",
      "Isolation by tenant; no cross-tenant data sharing or training",
    ],
  },
];

export default function IdentityPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-16 md:py-24 text-center">
        <span className="inline-flex items-center text-xs font-semibold border border-cyan-500/30 rounded-full px-4 py-1.5 text-cyan-400 mb-6 bg-cyan-500/5">
          Identity & Access Management
        </span>
        <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
          Identity, SSO, and access policies—managed.{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
            No separate SSO bill.
          </span>
        </h1>
        <p className="text-xl text-slate-300 leading-relaxed max-w-3xl mx-auto mb-8">
          Use SentinelGrid as your IdP or bring your own. You get SSO (OIDC/OAuth), MFA, a drag-and-drop policy editor,
          access governance, and posture checks—without per-user add-ons.
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          <Link
            href="/demo"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
          >
            See a policy built live
          </Link>
          <Link
            href="/contact"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
          >
            Talk with an IAM engineer
          </Link>
        </div>
      </section>

      {/* Capabilities */}
      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">Everything you need for IAM</h2>
            <p className="text-slate-400 text-lg max-w-3xl mx-auto">
              Identity provider, SSO, MFA, governance, and posture in one place—plus a visual policy editor so you don&apos;t
              need to learn another DSL.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {capabilities.map((item) => (
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

      {/* Policy builder highlight */}
      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-8 items-start">
          <div>
            <h3 className="text-2xl font-semibold mb-4">Drag-and-drop policy editor</h3>
            <p className="text-slate-300 text-sm leading-relaxed mb-3">
              Build fine-grained access policies visually. Combine roles, attributes, conditions, and approvals without
              writing policy language. Simulate and preview before enforcing.
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Policies can target users, groups, apps, APIs, and service accounts. Every change is logged, and you can require
              approvals for high-risk updates.
            </p>
          </div>
          <div className="bg-slate-900/70 rounded-2xl border border-slate-800 p-6">
            <h4 className="text-lg font-semibold text-slate-100 mb-3">What you can do</h4>
            <ul className="space-y-2 text-sm text-slate-300">
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Create scoped access for apps and APIs with OIDC/OAuth defaults baked in.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Set context-aware MFA and device requirements.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Model just-in-time access with expirations and approvals.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Simulate policies to see who gets access before you enforce.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 border border-cyan-500/20 rounded-3xl p-10 text-center">
          <h3 className="text-3xl font-semibold mb-3">Ready to simplify IAM?</h3>
          <p className="text-slate-300 text-sm md:text-base max-w-3xl mx-auto mb-6">
            Turn on built-in SSO, MFA, and governance without buying a separate SSO platform. Use our IdP or bring yours—we&apos;ll
            keep your identity posture clean either way.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Book an IAM walkthrough
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
