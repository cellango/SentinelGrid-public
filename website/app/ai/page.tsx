import Link from "next/link";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

export default function AIPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-16 md:py-24 text-center">
        <span className="inline-flex items-center text-xs font-semibold border border-cyan-500/30 rounded-full px-4 py-1.5 text-cyan-400 mb-6 bg-cyan-500/5">
          AI-first security
        </span>
        <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-tight mb-6">
          An AI analyst at your beck and call.{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
            Ask in plain English, get action.
          </span>
        </h1>
        <p className="text-xl text-slate-300 leading-relaxed max-w-3xl mx-auto mb-8">
          Our AI agent watches detections, tickets, playbooks, and posture signals. You can ask it questions in natural
          language—no cryptic queries—and it will explain, prioritize, and suggest the next move using the context of your
          environment.
        </p>
        <div className="flex flex-wrap gap-4 justify-center">
          <Link
            href="/demo"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
          >
            See the AI in action
          </Link>
          <Link
            href="/ai-shield"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
          >
            Explore AI security
          </Link>
        </div>
      </section>

      {/* Pillars */}
      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Always-on analyst</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              The agent monitors alerts, tickets, detections, posture, and identity signals. Ask “What matters now?”
              and it gives a narrative with recommended actions—no DSL or query language required.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Trained on your environment</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Learns from your telemetry, playbooks, and past decisions to reduce noise and tailor responses. It keeps data
              scoped to your tenant and respects role-based access.
            </p>
          </div>
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6">
            <p className="text-sm font-semibold text-cyan-400 mb-2">Guardrails built-in</p>
            <p className="text-slate-300 text-sm leading-relaxed">
              Safety policies, audit trails, and approval gates protect actions. The agent proposes; you approve—or automate
              safely with pre-set bounds.
            </p>
          </div>
        </div>
      </section>

      {/* What you can ask */}
      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-3xl md:text-5xl font-semibold mb-4">Ask in natural language</h2>
            <p className="text-slate-400 text-lg max-w-3xl mx-auto">
              No cryptic syntax. Just ask, and the agent combines detections, posture, identity, tickets, and playbooks to
              answer and propose actions.
            </p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              "“What are today’s top 5 risks and what should I do first?”",
              "“Explain this alert to an exec in two sentences.”",
              "“Why did MFA fatigue spike for this team?”",
              "“Show me open tickets older than 3 days that block onboarding.”",
              "“Retest the fixed findings from yesterday’s web scan.”",
              "“Draft a response to the vendor asking about our AI safeguards.”",
            ].map((q) => (
              <div
                key={q}
                className="bg-slate-900/70 rounded-2xl border border-slate-800 p-5 text-sm text-slate-200 leading-relaxed"
              >
                {q}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Strategy */}
      <section className="py-16 px-6 bg-slate-900/30">
        <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-8 items-start">
          <div>
            <h3 className="text-2xl font-semibold mb-4">Our AI strategy</h3>
            <p className="text-slate-300 text-sm leading-relaxed mb-3">
              AI is woven into every surface: detections, playbooks, posture, and identity. The agent is multi-modal: it reads
              events, tickets, dashboards, and findings; it writes narratives, tickets, and suggested actions; it can trigger
              automations when allowed.
            </p>
            <p className="text-slate-300 text-sm leading-relaxed">
              We iterate the model with your feedback loops and keep hard isolation per tenant. No cross-customer training data
              leakage—your context stays yours.
            </p>
          </div>
          <div className="bg-slate-900/70 rounded-2xl border border-slate-800 p-6">
            <h4 className="text-lg font-semibold text-slate-100 mb-3">Built for operators</h4>
            <ul className="space-y-2 text-sm text-slate-300">
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Grounded answers: ties responses back to detections, logs, and tickets in your tenant.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Decision support: ranks options, highlights tradeoffs, and shows likely blast radius.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-cyan-400 mt-0.5">•</span>
                <span>Action proposals: recommends playbooks or drafts commands, with approvals baked in.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-6">
        <div className="max-w-5xl mx-auto bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 border border-cyan-500/20 rounded-3xl p-10 text-center">
          <h3 className="text-3xl font-semibold mb-3">Ready for an AI teammate?</h3>
          <p className="text-slate-300 text-sm md:text-base max-w-3xl mx-auto mb-6">
            Turn on the agent, ask in plain language, and let it draft the next move. We’ll keep training it on your environment
            with your approval gates intact.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors shadow-lg shadow-cyan-400/20"
            >
              Book a walkthrough
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
