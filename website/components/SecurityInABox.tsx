import Link from "next/link";

export function SecurityInABox() {
  const features = [
    {
      title: "Endpoint Detection & Response",
      description:
        "SentinelGuard agents stream real-time endpoint telemetry with automated response playbooks that isolate hosts, kill processes, and sweep for IoCs.",
      icon: "🖥️",
      href: "/edr",
    },
    {
      title: "AI",
      description:
        "An always-on AI analyst you can ask in natural language. Explains alerts, suggests actions, and learns your environment.",
      icon: "🤖",
      href: "/ai",
    },
    {
      title: "Identity & Access Management",
      description:
        "Built-in IdP with SSO (OIDC/OAuth), MFA, governance, and posture checks—plus a drag-and-drop policy editor for fine-grained access.",
      icon: "🔐",
      href: "/identity",
    },
    {
      title: "Application & Cloud Security",
      description:
        "Static code, secrets, IaC, dependency, container, cloud posture, and web app checks with tickets and retests — no scanner picking required.",
      icon: "🧭",
      href: "/appsec",
    },
    {
      title: "Pen Testing",
      description:
        "Continuous, AI-assisted penetration testing with ticketed findings and retests. Web apps, APIs, and cloud targets covered without scheduling friction.",
      icon: "🧪",
      href: "/ai-pentest",
    },
    {
      title: "AI Security",
      description:
        "Protect AI use across your org: enforce safe prompts, catch data leakage, and govern tool calls whether Shield runs in our cloud or yours.",
      icon: "✨",
      href: "/ai-shield",
    },
    {
      title: "Managed SIEM + SOAR",
      description:
        "Full-stack SIEM and SOAR as a service. We run detections, automations, tickets, and alerts—plug into your stack or use ours.",
      icon: "📡",
      href: "/siem-soar",
    },
  ];

  const services = [
    "SIEM as a Service",
    "SOAR as a Service",
    "SOC as a Service",
    "Identity as a Service",
    "Secrets as a Service",
    "Certificates as a Service",
    "Endpoint telemetry via our free agent (alarms to SIEM/SOAR)",
  ];

  return (
    <section id="security-in-a-box" className="py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-semibold mb-4">
            Security in a Box
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Everything you need for security operations, without building a security team.
            One platform, one bill, one onboarding.
          </p>
        </div>
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature) => {
            const card = (
              <>
                <div className="text-3xl mb-3">{feature.icon}</div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
              </>
            );

            return feature.href ? (
              <Link
                key={feature.title}
                href={feature.href}
                className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 hover:border-cyan-500/60 hover:shadow-lg hover:shadow-cyan-500/10 transition-all focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400"
              >
                {card}
              </Link>
            ) : (
              <div
                key={feature.title}
                className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 hover:border-cyan-500/50 transition-colors"
              >
                {card}
              </div>
            );
          })}
        </div>
        <div className="mt-10 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-2xl border border-cyan-500/20 p-8">
          <h3 className="text-2xl font-semibold mb-3">
            SSO without a separate SSO bill
          </h3>
          <p className="text-slate-300 mb-4 max-w-2xl">
            SentinelGrid includes a built‑in identity provider so small and mid‑sized teams
            don&apos;t have to buy and run a separate SSO platform. Single sign‑on for
            SentinelGrid and your core apps, with MFA and security policies baked in — no seat tax.
          </p>
          <p className="text-slate-400 text-sm">
            Already have SSO? Connect Google Workspace, Microsoft 365 / Entra, Okta or
            Keycloak and we&apos;ll sit on top of it. SentinelGrid reads your users and roles,
            highlights risky accounts, and enforces policies — without forcing you to migrate
            your identity or pay per-user uplift.
          </p>
        </div>

        <div className="mt-8 grid md:grid-cols-[1.2fr,0.8fr] gap-6">
          <div className="bg-slate-900/70 rounded-2xl border border-slate-800 p-6">
            <h3 className="text-2xl font-semibold mb-3">AI Security, end to end</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Add an AI security layer without extra tooling. Choose Shield operated by SentinelGrid or deploy in your environment—either way you get safe prompts, governed tool use, and real-time detections.
            </p>
          </div>
          <div className="bg-slate-900/70 rounded-2xl border border-slate-800 p-6">
            <h3 className="text-2xl font-semibold mb-3">Services we run for you</h3>
            <ul className="space-y-2 text-slate-300 text-sm">
              {services.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="text-cyan-400 mt-0.5">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
