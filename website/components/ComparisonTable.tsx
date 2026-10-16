export function ComparisonTable() {
  const comparisons = [
    {
      category: "EDR / Endpoint",
      protect: "Included (agent + hardened images)",
      defend: "Included",
      comply: "Included",
    },
    {
      category: "Scans",
      protect: "SAST / DAST / vuln / git / cloud / IaC",
      defend: "Same + orchestration and tuning",
      comply: "Same coverage",
    },
    {
      category: "AI Shield",
      protect: "Baseline guardrails (prompt, PII, secrets)",
      defend: "Advanced (tool governance, policies)",
      comply: "Advanced",
    },
    {
      category: "SIEM",
      protect: "Lite (core detections, limited sources/retention)",
      defend: "Full ingest + curated detections",
      comply: "Full ingest + curated detections",
    },
    {
      category: "SOAR & Playbooks",
      protect: "Basic automations",
      defend: "Full library + ticketing integrations",
      comply: "Full library + compliance workflows",
    },
    {
      category: "SOC",
      protect: "Not included",
      defend: "Customer-run or SentinelGrid-managed (option)",
      comply: "Customer-run or SentinelGrid-managed (option)",
    },
    {
      category: "Compliance & Governance",
      protect: "Not included",
      defend: "Not included",
      comply: "Included (SOC2 kit, evidence hub, attestations)",
    },
  ];

  return (
    <>
      {/* Preserve legacy anchor while moving to #plans */}
      <div id="comparison" className="sr-only" aria-hidden="true"></div>
      <section id="plans" className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-semibold mb-4">
            Pick the plan that fits
          </h2>
          <p className="text-slate-400 text-lg max-w-3xl mx-auto">
            Three clear options: Protect, Protect &amp; Defend, and Protect,
            Defend &amp; Comply. Same platform, tuned for how much coverage you
            need.
          </p>
        </div>

        {/* Desktop Table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full bg-gradient-to-br from-slate-900/80 to-slate-900/40 rounded-2xl border border-slate-800 overflow-hidden">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="p-6 text-left text-slate-400 font-medium text-sm w-1/4"></th>
                <th className="p-6 text-center text-slate-400 font-medium">
                  <div className="flex flex-col items-center gap-2">
                    <span className="text-2xl">🛡️</span>
                    <span>Protect</span>
                  </div>
                </th>
                <th className="p-6 text-center text-slate-400 font-medium">
                  <div className="flex flex-col items-center gap-2">
                    <span className="text-2xl">⚡</span>
                    <span>Protect &amp; Defend</span>
                  </div>
                </th>
                <th className="p-6 text-center font-medium">
                  <div className="flex flex-col items-center gap-2">
                    <span className="text-2xl">✅</span>
                    <span className="text-cyan-400">
                      Protect, Defend &amp; Comply
                    </span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {comparisons.map((row, idx) => (
                <tr
                  key={idx}
                  className={`border-b border-slate-800 last:border-b-0 ${
                    idx % 2 === 0 ? "bg-slate-900/20" : ""
                  }`}
                >
                  <td className="p-6 font-semibold text-slate-200">
                    {row.category}
                  </td>
                  <td className="p-6 text-center text-slate-400 text-sm">
                    {row.protect}
                  </td>
                  <td className="p-6 text-center text-slate-400 text-sm">
                    {row.defend}
                  </td>
                  <td className="p-6 text-center text-cyan-400 font-medium text-sm bg-cyan-500/5">
                    {row.comply}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards */}
        <div className="md:hidden space-y-6">
          {comparisons.map((row, idx) => (
            <div
              key={idx}
              className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 rounded-xl border border-slate-800 p-6"
            >
              <h3 className="font-semibold text-slate-200 mb-4 text-lg">
                {row.category}
              </h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <span className="text-xl">🛡️</span>
                  <div className="flex-1">
                    <p className="text-xs text-slate-500 mb-1">Protect</p>
                    <p className="text-sm text-slate-300">{row.protect}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <span className="text-xl">⚡</span>
                  <div className="flex-1">
                    <p className="text-xs text-slate-500 mb-1">
                      Protect &amp; Defend
                    </p>
                    <p className="text-sm text-slate-300">{row.defend}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 bg-cyan-500/5 -mx-6 px-6 py-3 -mb-6 rounded-b-xl">
                  <span className="text-xl">✅</span>
                  <div className="flex-1">
                    <p className="text-xs text-cyan-400 mb-1 font-medium">
                      Protect, Defend &amp; Comply
                    </p>
                    <p className="text-sm text-cyan-400 font-medium">
                      {row.comply}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom CTA */}
        <div className="mt-10 text-center">
          <p className="text-slate-400 mb-4">
            See how SentinelGrid would look in your environment
          </p>
          <a
            href="#pricing"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Get pricing in 30 seconds
          </a>
        </div>
      </div>
    </section>
    </>
  );
}
