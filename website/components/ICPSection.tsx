export function ICPSection() {
  const personas = [
    {
      title: "Fast-growing SaaS & AI startups",
      subtitle: "20-250 people",
      icon: "🚀",
      points: [
        "Most workloads running on AWS",
        "Customers asking about SOC 2 / ISO 27001",
        "One person 'owns' security on top of their day job",
      ],
    },
    {
      title: "Tech-enabled services companies",
      subtitle: "50-500 people",
      icon: "🏢",
      points: [
        "Sensitive client data in cloud apps",
        "A small IT/ops team, no 24/7 SOC",
        "Worried about ransomware, phishing, and misconfigured cloud",
      ],
    },
    {
      title: "Modern SMBs on AWS & SaaS",
      subtitle: "20-200 people",
      icon: "☁️",
      points: [
        "Using Google Workspace / Microsoft 365 / Okta today",
        "Want better visibility without buying a full SIEM + MDR stack",
        "Need to protect the business as it scales",
      ],
    },
  ];

  return (
    <section id="built-for" className="py-20 px-6 bg-slate-900/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-semibold mb-4">
            Built for companies that need security,
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400">
              not a security department
            </span>
          </h2>
          <p className="text-slate-400 text-lg max-w-3xl mx-auto mt-6">
            If this sounds like you, SentinelGrid is probably a great fit.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {personas.map((persona, idx) => (
            <div
              key={idx}
              className="relative group bg-gradient-to-br from-slate-900/80 to-slate-900/40 rounded-2xl border border-slate-800 p-8 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-xl hover:shadow-cyan-500/10"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-blue-500/5 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative">
                <div className="text-5xl mb-4">{persona.icon}</div>
                <h3 className="text-xl font-semibold mb-2 text-slate-100">
                  {persona.title}
                </h3>
                <p className="text-cyan-400 text-sm font-medium mb-4">
                  {persona.subtitle}
                </p>
                <ul className="space-y-3">
                  {persona.points.map((point, pidx) => (
                    <li
                      key={pidx}
                      className="flex items-start gap-2 text-sm text-slate-300"
                    >
                      <span className="text-cyan-400 mt-0.5 flex-shrink-0">
                        •
                      </span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-gradient-to-r from-slate-900/60 to-slate-800/60 rounded-xl border border-slate-700 p-6 text-center">
          <p className="text-slate-300 text-sm leading-relaxed">
            <span className="font-semibold text-slate-200">
              Not our sweet spot:
            </span>{" "}
            Fortune 500s with a 15-person SOC, huge on-prem estates, or
            multi-year SIEM migrations. We&apos;re focused on making smaller
            teams big-company secure.
          </p>
        </div>
      </div>
    </section>
  );
}

