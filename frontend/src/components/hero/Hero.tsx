export default function Hero() {
  return (
    <section id="product" className="py-20 px-6">
      <div className="max-w-7xl mx-auto grid gap-12 md:grid-cols-[1.1fr_1fr] items-center">
        <div>
          <p className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[rgba(148,163,184,0.4)] text-xs text-text-muted bg-[rgba(15,23,42,0.8)] mb-4">
            Security as a Service • AI‑driven SOC
          </p>
          <h1 className="text-4xl md:text-5xl font-bold mb-4 tracking-tight">
            Security is mandatory. A full SOC isn't.
          </h1>
          <p className="text-text-muted mb-6 max-w-xl">
            SentinelGrid gives you an AI‑driven virtual SOC that triages alerts,
            investigates threats, and runs response playbooks — so your team can focus
            on building the business, not chasing incidents.
          </p>
          <div className="flex flex-wrap gap-3 mb-4">
            <a
              href="#contact"
              className="px-5 py-2.5 rounded-full text-sm bg-gradient-to-r from-primary to-secondary text-bg font-semibold hover:brightness-105"
            >
              Book a live demo
            </a>
            <a
              href="#how-it-works"
              className="px-5 py-2.5 rounded-full text-sm bg-transparent border-transparent text-text-muted hover:text-primary"
            >
              See how it works
            </a>
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-text-muted">
            <span>• Always‑on monitoring</span>
            <span>• Local, private AI models</span>
            <span>• No OpenAI keys required</span>
          </div>
        </div>
        <div className="bg-gradient-to-b from-[rgba(34,211,238,0.12)] to-bg rounded-[18px] border border-[rgba(15,23,42,0.95)] shadow-[0_26px_60px_rgba(15,23,42,0.9)] overflow-hidden">
          <div className="px-3.5 py-2.5 flex gap-2 border-b border-[rgba(15,23,42,0.95)]">
            <div className="w-2.5 h-2.5 rounded-full bg-[#22c55e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#eab308]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#ef4444]" />
          </div>
          <div className="p-6">
            <div className="inline-flex px-2.5 py-1 rounded-full border border-[rgba(148,163,184,0.4)] text-xs text-text-muted mb-3">
              Live SOC view
            </div>
            <h2 className="text-lg font-semibold mb-2">
              "Suspicious login from new country"
            </h2>
            <p className="text-xs text-text-muted mb-3">
              AI severity: <strong>High</strong> • Category: Suspicious login
            </p>
            <p className="text-sm mb-3">
              SentinelGrid agents correlated failed logins, new device, and geo change.
              Recommended playbook: <strong>Suspicious login – basic response</strong>.
            </p>
            <ul className="list-none pl-0 mb-4 space-y-1">
              <li className="text-sm text-text-muted pl-5 relative">
                <span className="absolute left-0 text-primary">•</span>
                Flag user session and force password reset
              </li>
              <li className="text-sm text-text-muted pl-5 relative">
                <span className="absolute left-0 text-primary">•</span>
                Notify user and security contact
              </li>
              <li className="text-sm text-text-muted pl-5 relative">
                <span className="absolute left-0 text-primary">•</span>
                Scan for other anomalous activity on the account
              </li>
            </ul>
            <button className="w-full px-4 py-2 rounded-[10px] bg-[rgba(15,23,42,0.8)] border border-border text-text-main hover:border-primary">
              Run response playbook
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

