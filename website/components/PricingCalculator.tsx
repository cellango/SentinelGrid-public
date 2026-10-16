"use client";

import { useState } from "react";
import Link from "next/link";

export function PricingCalculator() {
  const [teamSize, setTeamSize] = useState(0); // 0=1-25, 1=26-50, 2=51-100, 3=101-250, 4=250+
  const [selectedPlan, setSelectedPlan] = useState<
    "protect" | "protect_defend" | "protect_defend_comply"
  >("protect");

  const teamSizes = [
    { label: "1-25", range: "1-25 people" },
    { label: "26-50", range: "26-50 people" },
    { label: "51-100", range: "51-100 people" },
    { label: "101-250", range: "101-250 people" },
    { label: "250+", range: "250+ people" },
  ];

  const pricingTiers = [
    {
      protect: [249, 399],
      protect_defend: [449, 599],
      protect_defend_comply: [549, 699],
    }, // 1-25
    {
      protect: [449, 649],
      protect_defend: [649, 899],
      protect_defend_comply: [849, 1099],
    }, // 26-50
    {
      protect: [699, 999],
      protect_defend: [999, 1399],
      protect_defend_comply: [1299, 1799],
    }, // 51-100
    {
      protect: [1099, 1599],
      protect_defend: [1599, 2199],
      protect_defend_comply: [1999, 2799],
    }, // 101-250
    {
      protect: [0, 0],
      protect_defend: [0, 0],
      protect_defend_comply: [0, 0],
    }, // 250+ (Contact sales)
  ];

  const getPrice = (plan: "protect" | "protect_defend" | "protect_defend_comply") => {
    const [min, max] = pricingTiers[teamSize][plan];
    if (min === 0 || max === 0) return "Contact us";
    return `$${min}-$${max}/month`;
  };

  const plans = [
    {
      key: "protect" as const,
      name: "Protect",
      subtitle: "Secure your stack",
      features: [
        "Endpoint protection (agent + hardened images)",
        "Continuous scans: SAST / DAST / vuln / git / cloud / IaC",
        "Baseline AI Shield (prompt, PII, secrets guardrails)",
        "SIEM Lite (core detections, limited sources/retention)",
        "Basic automation & built-in playbooks",
      ],
    },
    {
      key: "protect_defend" as const,
      name: "Protect & Defend",
      subtitle: "Modern SOC in a box",
      badge: "Most popular",
      features: [
        "Everything in Protect",
        "Advanced AI Shield (tool governance + policies)",
        "Full SIEM ingest with curated detections",
        "SOAR: full playbook library + ticketing integrations",
        "SOC: customer-run or SentinelGrid-managed option",
      ],
    },
    {
      key: "protect_defend_comply" as const,
      name: "Protect, Defend & Comply",
      subtitle: "Secure + SOC + compliance",
      features: [
        "Everything in Protect & Defend",
        "Compliance & governance (SOC2 kit, evidence hub, mapping)",
        "Access reviews & joiner-mover-leaver automation",
        "Audit-ready exports (PDF / CSV) + attestations",
        "Risk & regulatory tracking",
      ],
    },
  ];

  return (
    <section id="pricing" className="py-20 px-6 bg-slate-900/30">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-semibold mb-4">
            Three clear packages, one platform
          </h2>
          <p className="text-slate-400 text-lg max-w-3xl mx-auto">
            Choose Protect, Protect &amp; Defend, or Protect, Defend &amp;
            Comply. Set your team size, pick the coverage level, and see the
            range — no surprise overages.
          </p>
        </div>

        {/* Interactive Controls */}
        <div className="max-w-3xl mx-auto mb-12 bg-gradient-to-br from-slate-900/80 to-slate-900/40 rounded-2xl border border-slate-800 p-8">
          {/* Team Size Slider */}
          <div className="mb-8">
            <label className="block text-lg font-semibold text-slate-200 mb-4">
              How many people are in your company?
            </label>
            <div className="relative">
              <input
                type="range"
                min="0"
                max="4"
                value={teamSize}
                onChange={(e) => setTeamSize(parseInt(e.target.value))}
                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer slider"
                style={{
                  background: `linear-gradient(to right, #06b6d4 0%, #06b6d4 ${
                    (teamSize / 4) * 100
                  }%, #334155 ${(teamSize / 4) * 100}%, #334155 100%)`,
                }}
              />
              <div className="flex justify-between mt-3">
                {teamSizes.map((size, idx) => (
                  <button
                    key={idx}
                    onClick={() => setTeamSize(idx)}
                    className={`text-sm transition-colors ${
                      teamSize === idx
                        ? "text-cyan-400 font-semibold"
                        : "text-slate-500 hover:text-slate-400"
                    }`}
                  >
                    {size.label}
                  </button>
                ))}
              </div>
            </div>
            <p className="text-center text-xl font-semibold text-cyan-400 mt-4">
              {teamSizes[teamSize].range}
            </p>
          </div>

          {/* Plan Selector */}
          <div className="border-t border-slate-700 pt-8">
            <label className="block text-lg font-semibold text-slate-200 mb-4">
              Which package fits?
            </label>
            <div className="grid md:grid-cols-3 gap-3">
              {plans.map((plan) => (
                <button
                  key={plan.key}
                  onClick={() => setSelectedPlan(plan.key)}
                  className={`flex flex-col gap-1 rounded-xl border-2 p-4 text-left transition-all ${
                    selectedPlan === plan.key
                      ? "border-cyan-500 bg-cyan-500/10 text-cyan-300"
                      : "border-slate-700 bg-slate-900/40 text-slate-300 hover:border-slate-600"
                  }`}
                >
                  <span className="text-sm font-semibold">{plan.name}</span>
                  <span className="text-xs text-slate-400">
                    {plan.subtitle}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Package Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-10">
          {plans.map((plan, idx) => (
            <div
              key={idx}
              className={`relative rounded-2xl border-2 p-8 transition-all duration-300 ${
                selectedPlan === plan.key
                  ? "border-cyan-500 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 shadow-xl shadow-cyan-500/20 scale-105"
                  : "border-slate-800 bg-slate-900/40"
              }`}
              onClick={() => setSelectedPlan(plan.key)}
            >
              {plan.badge && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white text-xs font-bold px-4 py-1 rounded-full">
                  {plan.badge}
                </div>
              )}
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-slate-100 mb-2">
                  {plan.name}
                </h3>
                <p className="text-sm text-slate-400">{plan.subtitle}</p>
              </div>
              <div className="mb-6">
                <div className="text-3xl font-bold text-cyan-400">
                  {getPrice(plan.key)}
                </div>
                {teamSize !== 4 && (
                  <p className="text-xs text-slate-500 mt-2">
                    For {teamSizes[teamSize].range}
                  </p>
                )}
              </div>
              <ul className="space-y-3 mb-8">
                {plan.features.map((feature, fidx) => (
                  <li
                    key={fidx}
                    className="flex items-start gap-2 text-sm text-slate-300"
                  >
                    <span className="text-green-400 mt-0.5 flex-shrink-0">
                      ✓
                    </span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <Link
                href="/signup"
                className={`block w-full text-center rounded-full px-6 py-3 text-sm font-medium transition-colors ${
                  selectedPlan === plan.key
                    ? "bg-cyan-400 text-slate-950 hover:bg-cyan-300"
                    : "border-2 border-slate-600 text-slate-200 hover:border-cyan-400"
                }`}
              >
                {teamSize === 4 ? "Talk to us" : "Get your exact quote"}
              </Link>
            </div>
          ))}
        </div>

        {/* Included allowances */}
        <div className="mb-10 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
            <h3 className="text-lg font-semibold text-slate-100">
              Included allowances (no surprise metering)
            </h3>
            <p className="text-sm text-slate-400">
              If you outgrow these, we move you to the next band—no per-GB or per-run fees.
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[720px]">
              <thead>
                <tr className="text-slate-400 border-b border-slate-800">
                  <th className="py-3 pr-4 text-left font-medium">Plan</th>
                  <th className="py-3 pr-4 text-left font-medium">Endpoints</th>
                  <th className="py-3 pr-4 text-left font-medium">Cloud accts</th>
                  <th className="py-3 pr-4 text-left font-medium">Apps / repos</th>
                  <th className="py-3 pr-4 text-left font-medium">Container images/mo</th>
                  <th className="py-3 pr-4 text-left font-medium">Log ingest + hot retention</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-900">
                <tr className="text-slate-200">
                  <td className="py-3 pr-4 font-semibold">Protect</td>
                  <td className="py-3 pr-4">Up to 150</td>
                  <td className="py-3 pr-4">Up to 3</td>
                  <td className="py-3 pr-4">Up to 25</td>
                  <td className="py-3 pr-4">Up to 50</td>
                  <td className="py-3 pr-4">5 GB/day • 30 days hot</td>
                </tr>
                <tr className="text-slate-200">
                  <td className="py-3 pr-4 font-semibold">Protect &amp; Defend</td>
                  <td className="py-3 pr-4">Up to 500</td>
                  <td className="py-3 pr-4">Up to 6</td>
                  <td className="py-3 pr-4">Up to 75</td>
                  <td className="py-3 pr-4">Up to 150</td>
                  <td className="py-3 pr-4">20 GB/day • 60 days hot</td>
                </tr>
                <tr className="text-slate-200">
                  <td className="py-3 pr-4 font-semibold">Protect, Defend &amp; Comply</td>
                  <td className="py-3 pr-4">Up to 1000</td>
                  <td className="py-3 pr-4">Up to 12</td>
                  <td className="py-3 pr-4">Up to 150</td>
                  <td className="py-3 pr-4">Up to 300</td>
                  <td className="py-3 pr-4">40 GB/day • 90 days hot</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500 mt-3">
            Larger environments? We size you into the next band or a custom block. No per-GB surprise bills, no per-run automation fees.
          </p>
        </div>

        {/* Unlimited items */}
        <div className="mb-10 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h4 className="text-sm font-semibold text-slate-100 mb-2">
            Always unlimited
          </h4>
          <ul className="text-sm text-slate-300 space-y-2">
            <li className="flex gap-2">
              <span className="text-green-400">✓</span> Compliance reports and exports (PDF / CSV)
            </li>
            <li className="flex gap-2">
              <span className="text-green-400">✓</span> Ticketing / automation runs (normal use)
            </li>
          </ul>
        </div>

        {/* Reassurance */}
        <div className="text-center bg-gradient-to-r from-slate-900/60 to-slate-800/60 rounded-xl border border-slate-700 p-6">
          <p className="text-slate-300 text-sm leading-relaxed max-w-3xl mx-auto">
            <span className="font-semibold text-cyan-400">
              No surprise overages.
            </span>{" "}
            Each plan includes a fair amount of log volume and retention. If you
            consistently outgrow what&apos;s included, we&apos;ll help you tune
            noisy sources or move to a plan that fits – we won&apos;t meter you
            into surprise bills.
          </p>
        </div>
      </div>

      {/* Mini FAQ */}
      <div className="max-w-7xl mx-auto mt-10 bg-slate-900/40 border border-slate-800 rounded-xl p-6">
        <h4 className="text-lg font-semibold text-slate-100 mb-4">
          Pricing FAQ (fast)
        </h4>
        <div className="grid md:grid-cols-3 gap-4 text-sm text-slate-300">
          <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-4">
            <p className="font-semibold text-slate-100 mb-1">
              What&apos;s included?
            </p>
            <p className="text-slate-400">
              Published allowances for endpoints, cloud accounts, apps/repos,
              containers, and log ingest + hot retention. If you grow, we move
              you to the next band—no hidden meters.
            </p>
          </div>
          <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-4">
            <p className="font-semibold text-slate-100 mb-1">
              Do you meter logs?
            </p>
            <p className="text-slate-400">
              No per-GB penalties. Each plan includes a clear GB/day and hot
              retention. Outgrow it? We right-size you, not silently upcharge.
            </p>
          </div>
          <div className="rounded-lg bg-slate-900/60 border border-slate-800 p-4">
            <p className="font-semibold text-slate-100 mb-1">
              Reports and tickets?
            </p>
            <p className="text-slate-400">
              Compliance reports/exports and ticketing/automation runs are
              included and unlimited for normal use—no per-run fees.
            </p>
          </div>
        </div>
      </div>

      <style jsx>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, #06b6d4, #0891b2);
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
          transition: all 0.2s;
        }
        .slider::-webkit-slider-thumb:hover {
          transform: scale(1.2);
          box-shadow: 0 0 15px rgba(6, 182, 212, 0.7);
        }
        .slider::-moz-range-thumb {
          width: 24px;
          height: 24px;
          background: linear-gradient(135deg, #06b6d4, #0891b2);
          border: none;
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
          transition: all 0.2s;
        }
        .slider::-moz-range-thumb:hover {
          transform: scale(1.2);
          box-shadow: 0 0 15px rgba(6, 182, 212, 0.7);
        }
      `}</style>
    </section>
  );
}
