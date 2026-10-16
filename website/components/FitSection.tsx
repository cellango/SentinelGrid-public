import Link from "next/link";

export function FitSection() {
  const goodFit = [
    "You have around 20-500 employees",
    "Most of your infrastructure is AWS + SaaS",
    "There's no full-time security team – IT, DevOps, or a tech-savvy founder is wearing that hat",
    "Customers or regulators are starting to ask about security and compliance",
    "You want one place to see 'are we okay?' and to respond when something looks wrong",
  ];

  const notFit = [
    "You already run a large security platform and a 24/7 SOC",
    "Most of your critical systems are on-prem or legacy platforms",
    "You're looking for a DIY toolkit with thousands of knobs instead of an opinionated platform",
  ];

  return (
    <section id="is-it-right" className="py-20 px-6 bg-slate-900/30">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-semibold mb-4">
            Is SentinelGrid a good fit?
          </h2>
          <p className="text-slate-400 text-lg max-w-3xl mx-auto">
            We&apos;re not for everyone – and that&apos;s okay. Here&apos;s how
            to know if we&apos;re right for your team.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-10">
          {/* Good Fit */}
          <div className="bg-gradient-to-br from-green-500/10 to-cyan-500/10 rounded-2xl border-2 border-green-500/30 p-8">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-4xl">✓</span>
              <h3 className="text-2xl font-bold text-green-400">
                You&apos;ll probably love SentinelGrid if...
              </h3>
            </div>
            <ul className="space-y-4">
              {goodFit.map((item, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="text-green-400 mt-1 flex-shrink-0">•</span>
                  <span className="text-slate-200 leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Not a Fit */}
          <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 rounded-2xl border-2 border-slate-700 p-8">
            <div className="flex items-center gap-3 mb-6">
              <span className="text-4xl">⚠️</span>
              <h3 className="text-2xl font-bold text-slate-300">
                We might not be the right tool if...
              </h3>
            </div>
            <ul className="space-y-4">
              {notFit.map((item, idx) => (
                <li key={idx} className="flex items-start gap-3">
                  <span className="text-slate-500 mt-1 flex-shrink-0">•</span>
                  <span className="text-slate-400 leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
            <div className="mt-6 pt-6 border-t border-slate-700">
              <p className="text-sm text-slate-500 italic">
                If you&apos;re in this bucket, we can point you to better
                alternatives. No hard feelings!
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-2xl border border-cyan-500/30 p-8 text-center">
          <h3 className="text-2xl font-semibold mb-4 text-slate-100">
            Ready to see how SentinelGrid would look in your environment?
          </h3>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
              href="/signup"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
            >
              Get pricing in 30 seconds
            </Link>
            <Link
              href="/demo"
              className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium border-2 border-slate-600 text-slate-200 hover:border-cyan-400 transition-colors"
            >
              Book a 20-minute walkthrough
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

