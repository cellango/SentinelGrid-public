import { Header } from "@/components/Header";
import { RotatingStatements } from "@/components/RotatingStatements";
import { TrustBar } from "@/components/TrustBar";
import { ICPSection } from "@/components/ICPSection";
import { ThreePillars } from "@/components/ThreePillars";
import { HowItWorks } from "@/components/HowItWorks";
import { PricingCalculator } from "@/components/PricingCalculator";
import { ComparisonTable } from "@/components/ComparisonTable";
import { SecurityInABox } from "@/components/SecurityInABox";
import { FitSection } from "@/components/FitSection";
import { TrustSection } from "@/components/TrustSection";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="grid md:grid-cols-[1.2fr,1fr] gap-10 items-center">
          <div>
            <span className="inline-flex items-center text-xs font-semibold border border-slate-700 rounded-full px-3 py-1 text-slate-300 mb-4">
              Security as a Service
            </span>
            <h1 className="mt-4 text-4xl md:text-6xl font-semibold tracking-tight leading-tight">
              Security in a box for teams
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
                without a SOC
              </span>
            </h1>
            <p className="mt-6 text-lg text-slate-300 max-w-xl leading-relaxed">
              Cloud, identity, and endpoint protection for companies with 20-500 people – without hiring a security team or buying 5 different tools.
            </p>

            {/* Key Value Props */}
            <div className="mt-6 space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-cyan-400 text-xl mt-0.5">✓</span>
                <p className="text-slate-300">
                  Detect and stop account takeover, cloud misconfig, and phishing
                </p>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-cyan-400 text-xl mt-0.5">✓</span>
                <p className="text-slate-300">
                  Compliance-friendly defaults for SOC 2 / ISO 27001
                </p>
              </div>
            </div>

            <RotatingStatements />

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="#plans"
                className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
              >
                See plans &amp; pricing
              </Link>
              <Link
                href="/demo"
                className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
              >
                Watch a 5-minute overview
              </Link>
            </div>

            <div className="mt-6">
              <p className="text-xs text-slate-500">
                Hosted on AWS • Built on open standards (OIDC, SAML) • Proven security architecture
              </p>
            </div>
          </div>

          {/* Right side: Live preview card */}
          <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-slate-800 rounded-2xl p-6 shadow-xl hover:shadow-cyan-500/10 transition-shadow">
            <p className="text-xs text-slate-400 mb-3 font-medium">Live alert preview</p>
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-red-400 mt-1.5 animate-pulse"></div>
                <div className="flex-1">
                  <p className="font-semibold text-sm text-slate-200">
                    Suspicious login from new location
                  </p>
                  <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                    AI correlated failed logins, new device fingerprint, and IP reputation. Mapped to MITRE T1078 and NIST AC-2, AC-6. Recommended action: Lock account and require re-authentication.
                  </p>
                  <div className="mt-3 flex gap-2 flex-wrap">
                    <span className="px-2 py-1 text-xs bg-red-500/20 text-red-300 rounded border border-red-500/30">
                      High Priority
                    </span>
                    <span className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">
                      Account Takeover
                    </span>
                  </div>
                  <button className="mt-3 text-xs text-cyan-400 hover:text-cyan-300 font-medium">
                    View playbook →
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ICP Section - Built for teams like yours */}
      <ICPSection />

      {/* Three Pillars - What you get */}
      <ThreePillars />

      {/* Security in a Box */}
      <SecurityInABox />

      {/* SOC 2 CTA */}
      <section className="py-14 px-6">
        <div className="max-w-6xl mx-auto grid md:grid-cols-[1.1fr,0.9fr] gap-8 items-center rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900/70 via-slate-900/40 to-slate-900/70 p-8">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-300/80 mb-2">Trust &amp; SOC 2</p>
            <h2 className="text-3xl md:text-4xl font-semibold text-slate-50">Tenant-aware AI, ready for auditors</h2>
            <p className="mt-4 text-slate-300 leading-relaxed">
              SOC 2 dashboards, AI activity logs, and scheduled reports live in the app. Every AI call carries tenant + realm context to keep evidence clean.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/trust"
                className="inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
              >
                See Trust &amp; SOC 2
              </Link>
              <Link
                href="/dashboard/compliance"
                className="inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold border border-slate-700 text-slate-200 hover:border-cyan-400 transition-colors"
              >
                Open SOC 2 Dashboard
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <p className="text-xs text-slate-400">Coverage</p>
              <p className="text-2xl font-semibold">SOC 2</p>
              <p className="text-xs text-cyan-300 mt-1">Mapped to playbooks &amp; detections</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <p className="text-xs text-slate-400">AI Activity</p>
              <p className="text-2xl font-semibold">Tenant-scoped</p>
              <p className="text-xs text-cyan-300 mt-1">Prompt + response audit trail</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <p className="text-xs text-slate-400">Reporting</p>
              <p className="text-2xl font-semibold">PDF / CSV</p>
              <p className="text-xs text-cyan-300 mt-1">Weekly / monthly / quarterly</p>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <p className="text-xs text-slate-400">Isolation</p>
              <p className="text-2xl font-semibold">Per-tenant</p>
              <p className="text-xs text-cyan-300 mt-1">No cross-tenant fallback</p>
            </div>
          </div>
        </div>
      </section>

      {/* Premium Services Section */}
      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">
              Premium security services
            </h2>
            <p className="text-slate-400 text-lg max-w-3xl mx-auto">
              Go beyond the platform with specialized services for AI security and penetration testing
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            {/* AI Shield Card */}
            <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border-2 border-slate-800 rounded-2xl p-8 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10">
              <div className="flex items-start justify-between mb-4">
                <div className="text-4xl">🛡️</div>
                <span className="text-xs font-semibold text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full">
                  $199/mo
                </span>
              </div>
              <h3 className="text-2xl font-bold text-slate-100 mb-3">
                AI Shield
              </h3>
              <p className="text-slate-400 mb-6 leading-relaxed">
                Protect your AI applications from prompt injection, data leaks, and unsafe tool calls with our drop-in AI gateway.
              </p>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Real-time prompt injection & jailbreak detection</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Built-in PII and secrets detection</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>AI agent tool call governance</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Full SIEM integration for compliance</span>
                </li>
              </ul>
              <Link
                href="/ai-shield"
                className="inline-flex items-center justify-center w-full rounded-full px-6 py-3 text-sm font-medium border-2 border-cyan-500 text-cyan-400 hover:bg-cyan-500/10 transition-colors"
              >
                Learn more about AI Shield →
              </Link>
            </div>

            {/* Pentest Agent Card */}
            <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border-2 border-slate-800 rounded-2xl p-8 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10">
              <div className="flex items-start justify-between mb-4">
                <div className="text-4xl">🔍</div>
                <span className="text-xs font-semibold text-cyan-400 bg-cyan-500/10 px-3 py-1 rounded-full">
                  From $4k
                </span>
              </div>
              <h3 className="text-2xl font-bold text-slate-100 mb-3">
                Pentest Agent
              </h3>
              <p className="text-slate-400 mb-6 leading-relaxed">
                Real penetration testing powered by AI automation and human expertise — at a price you can actually budget.
              </p>
              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Automated recon with human verification</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Continuous or one-off engagements</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Clear, executive-friendly reports</span>
                </li>
                <li className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-cyan-400 mt-0.5">✓</span>
                  <span>Upfront pricing, no surprise fees</span>
                </li>
              </ul>
              <Link
                href="/ai-pentest"
                className="inline-flex items-center justify-center w-full rounded-full px-6 py-3 text-sm font-medium border-2 border-cyan-500 text-cyan-400 hover:bg-cyan-500/10 transition-colors"
              >
                Learn more about Pentest Agent →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How it Works - 3 Steps */}
      <HowItWorks />

      {/* Interactive Pricing Calculator */}
      <PricingCalculator />

      {/* Comparison Table */}
      <ComparisonTable />

      {/* Mission & Vision */}
      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-5xl mx-auto space-y-10">
          <div>
            <h2 className="text-3xl md:text-4xl font-semibold mb-3">Mission</h2>
            <p className="text-slate-300 text-lg leading-relaxed">
              SentinelGrid’s mission is to make enterprise-grade cybersecurity effortless and affordable for every organization, not just the Fortune 500.
              We turn complex security operations into an AI-driven service so customers can focus on their core business, not building a SOC.
            </p>
          </div>
          <div>
            <h2 className="text-3xl md:text-4xl font-semibold mb-3">Vision</h2>
            <p className="text-slate-300 text-lg leading-relaxed">
              Our vision is a world where “turning on security” feels as natural as turning on the lights—one platform, one subscription, and always-on AI defenders watching your cloud, code, identities, data, and AI systems.
              SentinelGrid becomes the security utility layer for small and medium businesses: opinionated, automated, and relentlessly on their side.
            </p>
          </div>
        </div>
      </section>

      {/* Is SentinelGrid right for you? */}
      <FitSection />

      {/* Philosophy & Trust */}
      <TrustSection />

      <Footer />
    </main>
  );
}
