import Link from "next/link";

export function Pricing() {
  const plans = [
    {
      name: "Micro",
      description: "For teams under 25",
      price: "$99",
      period: "/month",
      features: [
        "Up to 25 users",
        "Managed SIEM + SOAR",
        "AI‑SOC triage",
        "IAM hygiene checks",
        "Built‑in SSO & MFA (IdP included)",
        "Email support",
      ],
      cta: "Start free trial",
      popular: false,
    },
    {
      name: "Startup",
      description: "For teams 25–100",
      price: "$299",
      period: "/month",
      features: [
        "Up to 100 users",
        "Everything in Micro",
        "Cloud posture scanning",
        "Automated playbooks",
        "Priority support",
        "Custom integrations",
      ],
      cta: "Start free trial",
      popular: true,
    },
    {
      name: "Scaleup",
      description: "For teams 100–250",
      price: "$799",
      period: "/month",
      features: [
        "Up to 250 users",
        "Everything in Startup",
        "Advanced analytics",
        "Dedicated support",
        "Custom retention",
        "SLA guarantee",
      ],
      cta: "Contact sales",
      popular: false,
    },
  ];

  return (
    <section id="pricing" className="py-20 px-6 bg-slate-900/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-semibold mb-4">
            Simple pricing for small teams
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            We price by how much of your business we protect, not by log volume.
            No per‑GB log tax. No surprise bills.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`bg-slate-900/60 rounded-xl border p-6 ${
                plan.popular
                  ? "border-cyan-500 shadow-lg shadow-cyan-500/20"
                  : "border-slate-800"
              }`}
            >
              {plan.popular && (
                <div className="text-xs font-semibold text-cyan-400 mb-2">
                  MOST POPULAR
                </div>
              )}
              <h3 className="text-2xl font-semibold mb-1">{plan.name}</h3>
              <p className="text-slate-400 text-sm mb-4">{plan.description}</p>
              <div className="mb-6">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-slate-400">{plan.period}</span>
              </div>
              <ul className="space-y-3 mb-6">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2 text-sm">
                    <span className="text-green-400 mt-0.5">✓</span>
                    <span className="text-slate-300">{feature}</span>
                  </li>
                ))}
              </ul>
              <Link
                href={plan.cta === "Contact sales" ? "/demo" : "/signup"}
                className={`block w-full text-center rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  plan.popular
                    ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
                    : "border border-slate-600 text-slate-200 hover:border-cyan-400"
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
        <div className="mt-10 text-center">
          <p className="text-slate-400 text-sm">
            Need more? <Link href="/demo" className="text-cyan-400 hover:underline">Contact us</Link> for enterprise pricing.
          </p>
        </div>
      </div>
    </section>
  );
}
