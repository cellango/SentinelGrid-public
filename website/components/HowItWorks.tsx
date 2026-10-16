import Link from "next/link";

export function HowItWorks() {
  const steps = [
    {
      number: "1",
      title: "Connect your identity & cloud",
      description:
        "Link your identity provider (Google Workspace, Microsoft 365, Okta, or use SentinelGrid as your IdP). Connect your AWS account(s) using our guided setup – we only need read-only access for monitoring.",
      icon: "🔌",
    },
    {
      number: "2",
      title: "Deploy lightweight agents (optional)",
      description:
        "Install endpoint protection on critical servers and endpoints, or start from our hardened images. We begin collecting host-level security signals right away.",
      icon: "🛡️",
    },
    {
      number: "3",
      title: "Let AI-assisted playbooks watch your environment",
      description:
        "Within hours, your dashboard is populated with high-priority incidents, cloud posture findings, and IAM hygiene issues. Each item comes with a clear explanation and recommended next steps.",
      icon: "⚡",
    },
  ];

  return (
    <section id="how-it-works" className="py-20 px-6 bg-slate-900/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-semibold mb-4">
            From &quot;we should do something about security&quot;
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              to &quot;we&apos;re actually covered&quot;
            </span>
          </h2>
          <p className="text-slate-400 text-lg max-w-3xl mx-auto mt-6">
            Get up and running in hours, not months. No multi-year deployment project required.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {steps.map((step) => (
            <div
              key={step.number}
              className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 hover:border-cyan-500/50 transition-colors"
            >
              <div className="text-3xl mb-3">{step.icon}</div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-cyan-400 font-bold text-lg">{step.number}</span>
                <h3 className="text-xl font-semibold">{step.title}</h3>
              </div>
              <p className="text-slate-400 text-sm leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
        <div className="text-center mt-10">
          <Link
            href="/signup"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Start onboarding
          </Link>
        </div>
      </div>
    </section>
  );
}

