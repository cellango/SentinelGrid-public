import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function AIShieldPage() {
  const benefits = [
    {
      title: "Drop-in protection",
      icon: "🔌",
      description:
        "Point your apps at the Sentinel AI Gateway instead of the raw LLM endpoint — same API, now with guardrails.",
    },
    {
      title: "Stops prompt-injection and jailbreaks",
      icon: "🛡️",
      description:
        "We inspect prompts and responses in real time to catch jailbreaks, indirect prompt-injection, and policy violations before they hit your models or tools.",
    },
    {
      title: "Prevents data leakage",
      icon: "🔒",
      description:
        "Built-in detectors for PII, secrets, and sensitive documents help keep customer data from leaving your environment or landing in the wrong chat window.",
    },
    {
      title: "Controls AI agents and tools",
      icon: "⚙️",
      description:
        "Every tool call is governed and logged — risky actions can be blocked or require human approval via Slack/Teams.",
    },
    {
      title: "Full audit trail for compliance",
      icon: "📋",
      description:
        "Every AI interaction becomes a structured log you can ship to SentinelGrid SIEM or your own SIEM for investigation, detection rules, and evidence.",
    },
  ];

  const pricingFeatures = [
    "Gateway for up to 100K AI requests/month",
    "Real-time prompt injection & jailbreak detection",
    "PII, secrets, and sensitive data detection",
    "AI agent tool call governance and logging",
    "Integration with SentinelGrid SIEM & SOAR (default)",
    "Option to mirror events to your SIEM/SOAR",
    "Slack/Teams notifications for risky actions",
    "Custom policy configuration",
    "Standard support",
  ];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 py-16 md:py-24">
        <div className="text-center max-w-4xl mx-auto">
          <span className="inline-flex items-center text-xs font-semibold border border-cyan-500/30 rounded-full px-4 py-1.5 text-cyan-400 mb-6 bg-cyan-500/5">
            SentinelGrid AI Shield™
          </span>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
            AI is powerful.{" "}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              Leaking your data into it shouldn&apos;t be.
            </span>
          </h1>
          <p className="text-xl text-slate-300 leading-relaxed mb-8">
            SentinelGrid AI Shield™ sits in front of your LLMs and agents to
            stop prompt-injection, data leaks, and unsafe tool calls — without
            making your developers rewrite their apps.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Get started at $199/month
            </Link>
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              Schedule a demo
            </Link>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">
              Protection that drops right in
            </h2>
            <p className="text-slate-400 text-lg max-w-3xl mx-auto">
              Stop AI risks without changing your code or slowing down your
              developers
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {benefits.map((benefit, idx) => (
              <div
                key={idx}
                className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border border-slate-800 rounded-2xl p-6 hover:border-cyan-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10"
              >
                <div className="text-4xl mb-4">{benefit.icon}</div>
                <h3 className="text-xl font-semibold text-slate-100 mb-3">
                  {benefit.title}
                </h3>
                <p className="text-slate-400 leading-relaxed">
                  {benefit.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why It's Different Section */}
      <section className="py-20 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border-2 border-cyan-500/30 rounded-2xl p-8 md:p-12">
            <div className="flex items-start gap-4 mb-6">
              <div className="text-4xl">⚡</div>
              <div>
                <h2 className="text-2xl md:text-3xl font-semibold text-cyan-400 mb-4">
                  Why it&apos;s different
                </h2>
                <p className="text-lg text-slate-300 leading-relaxed mb-4">
                  Unlike generic &quot;LLM firewalls,&quot; AI Shield is wired
                  into your broader SentinelGrid stack: AI events feed directly
                  into your SIEM, SOAR, IAM, and posture services.
                </p>
                <p className="text-sm text-slate-300 leading-relaxed mb-4">
                  Default: we run it on SentinelGrid SIEM/SOAR. Already have
                  Splunk, Datadog, Chronicle, or another SOC stack? Mirror the
                  same events there without extra effort.
                </p>
                <p className="text-lg text-slate-300 leading-relaxed">
                  You don&apos;t just see AI risks — you can{" "}
                  <span className="text-cyan-400 font-semibold">
                    respond to them
                  </span>
                  .
                </p>
              </div>
            </div>
            <div className="grid md:grid-cols-3 gap-4 mt-8">
              <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-700">
                <p className="text-sm font-semibold text-cyan-400 mb-2">
                  SIEM Integration
                </p>
                <p className="text-xs text-slate-400">
                  Every AI interaction is structured and streamed to
                  SentinelGrid SIEM by default, or to your SIEM if you prefer
                </p>
              </div>
              <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-700">
                <p className="text-sm font-semibold text-cyan-400 mb-2">
                  SOAR Playbooks
                </p>
                <p className="text-xs text-slate-400">
                  Automated responses via SentinelGrid SOAR by default; we can
                  also forward signals to your SOAR to trigger your runbooks
                </p>
              </div>
              <div className="bg-slate-900/60 rounded-lg p-4 border border-slate-700">
                <p className="text-sm font-semibold text-cyan-400 mb-2">
                  IAM Controls
                </p>
                <p className="text-xs text-slate-400">
                  Tie AI usage to identity, enforce policies based on user
                  roles and context
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-6 bg-slate-900/30">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">
              Simple, transparent pricing
            </h2>
            <p className="text-slate-400 text-lg">
              No hidden fees. No surprise bills. Just clear protection for your
              AI.
            </p>
          </div>

          <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 border-2 border-cyan-500 rounded-2xl p-8 md:p-10 shadow-xl shadow-cyan-500/20">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 text-xs font-semibold text-cyan-400 mb-3 bg-cyan-500/10 px-4 py-1 rounded-full">
                BEST VALUE FOR GROWING TEAMS
              </div>
              <h3 className="text-3xl font-bold text-slate-100 mb-2">
                AI Shield Standard
              </h3>
              <div className="flex items-baseline justify-center gap-2 mb-4">
                <span className="text-5xl font-bold text-cyan-400">$199</span>
                <span className="text-xl text-slate-400">/month</span>
              </div>
              <p className="text-slate-400">
                Everything you need to protect your AI applications
              </p>
            </div>

            <div className="border-t border-slate-700 pt-8">
              <h4 className="text-lg font-semibold text-slate-200 mb-4">
                What&apos;s included:
              </h4>
              <div className="grid md:grid-cols-2 gap-4">
                {pricingFeatures.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <span className="text-green-400 mt-1 flex-shrink-0">
                      ✓
                    </span>
                    <span className="text-slate-300">{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t border-slate-700 mt-8 pt-6">
              <p className="text-sm text-slate-400 text-center mb-6">
                Need more requests or custom features?{" "}
                <Link
                  href="/demo"
                  className="text-cyan-400 hover:text-cyan-300 font-medium"
                >
                  Contact us
                </Link>{" "}
                for enterprise pricing.
              </p>
              <p className="text-xs text-slate-500 text-center mb-6">
                SentinelGrid SIEM/SOAR are included. Bring-your-own SIEM/SOAR is
                supported, but you don&apos;t need it to get full value.
              </p>
              <div className="flex flex-wrap gap-4 justify-center">
                <Link
                  href="/signup"
                  className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
                >
                  Get started now
                </Link>
                <Link
                  href="/demo"
                  className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
                >
                  Talk to sales
                </Link>
              </div>
            </div>
          </div>

          <div className="mt-10 text-center bg-slate-900/40 rounded-xl border border-slate-800 p-6">
            <p className="text-slate-300 text-sm leading-relaxed">
              <span className="font-semibold text-cyan-400">
                Already a SentinelGrid customer?
              </span>{" "}
              Add AI Shield to your existing plan for just $149/month.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-semibold mb-6">
            Ready to secure your AI applications?
          </h2>
          <p className="text-lg text-slate-400 mb-8">
            Get started in minutes. No credit card required for the demo.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Start protecting your AI
            </Link>
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              See it in action
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
