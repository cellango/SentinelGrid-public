import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Link from "next/link";

const detectionCategories = [
  {
    title: "Identity & Access",
    items: [
      "Impossible travel and geo-velocity anomalies",
      "MFA fatigue / push bombing and brute-force",
      "Dormant account reuse and orphaned admin accounts",
      "Privileged role creation/assignment and privilege escalations",
      "Suspicious SSO logins (new device, risky IP, atypical time)",
      "OAuth consent abuse and risky third-party app grants",
      "Password spraying / credential stuffing indicators",
      "Multiple failed logins followed by success (potential compromise)",
    ],
  },
  {
    title: "Cloud (AWS/Azure/GCP)",
    items: [
      "New access keys created/used, long-lived keys in use",
      "Root or owner login without MFA",
      "Security groups or firewalls opened to the world",
      "Public bucket/blob exposure and object ACL changes",
      "IAM policy changes that add broad permissions",
      "Sensitive service escalations (STS, KMS, IAM) and role chaining",
      "CloudTrail/Activity log gaps or tampering indicators",
      "Unusual data transfer volume between regions or services",
    ],
  },
  {
    title: "Endpoint & Runtime",
    items: [
      "Office/Docs spawning PowerShell, cmd, or bash",
      "Unsigned binaries or LOLBins with network access",
      "Script dropper behaviors and encoded PowerShell",
      "Persistence via registry/run keys or launch agents",
      "Suspicious child-parent process trees (e.g., Teams -> PowerShell)",
      "EDR suppression, tamper attempts, or sensor offboarding",
      "Unusual lateral movement (SMB/RDP/WinRM) from workstations",
      "Memory scraping or credential dump tool signatures",
    ],
  },
  {
    title: "SaaS & Email",
    items: [
      "New global admins or app owners in SaaS",
      "MFA disabled for users or groups",
      "Mass downloads/exports from storage and collaboration tools",
      "Suspicious inbox rules and auto-forwarding to external domains",
      "Risky OAuth scopes added to productivity suites",
      "Shared links flipped to public/anyone with the link",
      "Logins from atypical geos/providers for execs",
      "Third-party integrations requesting elevated scopes",
    ],
  },
  {
    title: "Network & Edge",
    items: [
      "DNS tunneling or beaconing patterns",
      "Egress to known C2/malware infrastructure",
      "WAF/edge block spikes with credential stuffing indicators",
      "High-risk geolocation access to internal apps",
      "Tor/VPN/proxy usage attempting authentication",
      "Data exfil volume anomalies to object storage or SaaS",
      "Port scanning or lateral reconnaissance from user subnets",
      "TLS certificate anomalies and deprecated cipher use",
    ],
  },
  {
    title: "AI & Data",
    items: [
      "Prompt-injection and jailbreak attempts on AI endpoints",
      "PII/secrets exfil attempts in model prompts/responses",
      "Abuse of AI tool calls (file system, network, data stores)",
      "Unusual model usage patterns by account or app",
      "Bulk data access anomalies in data warehouses",
      "Data egress from sensitive datasets outside policy",
      "LLM output safety policy violations (toxicity/PII leakage)",
      "High-risk file uploads with malware/PII indicators",
    ],
  },
];

const playbooks = [
  "Lock account, force MFA reset, and expire sessions",
  "Revoke OAuth tokens and disable suspicious third-party apps",
  "Rotate or disable cloud access keys; remove risky roles",
  "Quarantine or roll back public storage buckets/blobs",
  "Block IPs/users at edge/WAF and notify stakeholders",
  "Open ticket + Slack/Teams incident channel with context",
  "Contain endpoint via EDR isolate/quarantine",
  "Disable inbox forwarding rules and restore mailbox settings",
  "Force password reset for affected users/groups",
  "Escalate to on-call with playbook steps and evidence bundle",
];

export default function SiemSoarPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="text-center max-w-4xl mx-auto">
          <span className="inline-flex items-center text-xs font-semibold border border-cyan-500/30 rounded-full px-4 py-1.5 text-cyan-400 mb-6 bg-cyan-500/5">
            Managed SIEM + SOAR as a Service
          </span>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
            SIEM and SOAR without the build-out.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              We run it, you get outcomes.
            </span>
          </h1>
          <p className="text-xl text-slate-300 leading-relaxed mb-8">
            Standing up and tuning SIEM/SOAR is expensive and slow. SentinelGrid ships it as a managed
            service—detections, automations, ticketing, and reporting—on our stack or plugged into yours.
          </p>
          <p className="text-sm text-slate-400 max-w-3xl mx-auto mb-6">
            Prefer your own SOC? Keep it. We still run detections, playbooks, and alerts into your tools.
            Want us to run the SOC? That&apos;s the default. No per-GB surprises, no DIY rule writing.
          </p>
          <p className="text-sm text-slate-400 max-w-3xl mx-auto">
            Free endpoint agent streams process/network/auth telemetry into the SIEM with mapped alarms and playbooks—use it
            as-is or alongside your existing EDR.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              See it in action
            </Link>
            <Link
              href="/#pricing"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              View pricing
            </Link>
          </div>
          <div className="mt-6 inline-flex flex-wrap items-center gap-3 text-xs text-slate-400 justify-center">
            <span className="px-3 py-1 rounded-full border border-cyan-500/40 text-cyan-300">
              110+ prebuilt detections
            </span>
            <span className="px-3 py-1 rounded-full border border-cyan-500/40 text-cyan-300">
              Playbooks for identity, cloud, SaaS, AI
            </span>
            <span className="px-3 py-1 rounded-full border border-cyan-500/40 text-cyan-300">
              SentinelGrid SIEM/SOAR included; BYO optional
            </span>
          </div>
        </div>
      </section>

      {/* Value props */}
      <section className="py-12 px-6 bg-slate-900/30">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Turnkey coverage</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Multi-surface detections out of the box: identity, cloud, SaaS, endpoint,
              network, and AI. No rule-writing required to get value day one. Endpoint alarms
              ride in from our free agent or your existing EDR.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Automation built-in</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Prewired SOAR playbooks for containment, comms, and evidence. Use ours by
              default; trigger your SOAR if you already have one.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Transparent model</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              No per-GB log tax surprises. We ship events to SentinelGrid SIEM/SOAR and can
              mirror to Splunk, Datadog, or your SIEM if you need it.
            </p>
          </div>
        </div>
      </section>

      {/* Detections */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">
              110+ prebuilt detections and playbooks
            </h2>
            <p className="text-slate-400 text-lg max-w-3xl mx-auto">
              SIEM and SOAR tuned out of the box so you don&apos;t spend months wiring rules or hunting for signal.
              We handle ingestion, normalization, detections, and automation—you get tickets and verified response.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {detectionCategories.map((category) => (
              <div
                key={category.title}
                className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-slate-800 rounded-2xl p-6"
              >
                <h3 className="text-xl font-semibold text-slate-100 mb-3">
                  {category.title}
                </h3>
                <ul className="space-y-2 text-sm text-slate-400">
                  {category.items.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <span className="text-cyan-400 mt-0.5">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Playbooks */}
      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-3xl md:text-4xl font-semibold mb-4">
              Prebuilt SOAR playbooks
            </h2>
            <p className="text-slate-400 max-w-3xl mx-auto">
              Response you can turn on immediately. We orchestrate across identity, cloud,
              EDR, email, chat, and ticketing — or fire your playbooks if you already have
              them.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <div className="grid md:grid-cols-2 gap-4">
              {playbooks.map((item) => (
                <div key={item} className="flex items-start gap-2 text-sm text-slate-300">
                  <span className="text-green-400 mt-0.5">✓</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-500 mt-4">
              Prefer your tooling? We can trigger your SIEM/SOAR with the same events —
              SentinelGrid SOAR is included so you don&apos;t need to buy and wire one to
              get value.
            </p>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-semibold mb-6">
            Ready to stop building SIEM/SOAR alone?
          </h2>
          <p className="text-lg text-slate-400 mb-8">
            Turn on detections, playbooks, and reporting in days, not quarters. Use our
            SIEM/SOAR out of the box, and mirror to yours if you need to.
          </p>
          <p className="text-sm text-slate-400 mb-8">
            Keep your SOC or use ours — either way, we run detections,
            playbooks, ticketing, and alerting so you don&apos;t have to wire it
            yourself.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Book a demo
            </Link>
            <Link
              href="/signup"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              Get started
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
