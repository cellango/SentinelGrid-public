"use client";

import { useState } from "react";

export function ThreePillars() {
  const [selectedPillar, setSelectedPillar] = useState(0);

  const pillars = [
    {
      title: "Cloud stays locked down",
      icon: "☁️",
      description:
        "We continuously scan your AWS accounts for misconfigurations, exposed storage, weak permissions, and vulnerabilities – and help you fix them.",
      features: [
        "Spot public cloud storage before it becomes a breach",
        "Find weak IAM policies and over-privileged roles",
        "Get plain-English fixes for cloud misconfigurations",
        "Continuously monitor for configuration drift",
      ],
      alarms: [
        {
          title: "Public cloud storage exposed",
          description:
            "We'll warn you the moment sensitive cloud storage is exposed to the internet—and help you lock it down safely.",
        },
        {
          title: "Unusual data transfer detected",
          description:
            "We'll spotlight unusual large data transfers so you can catch potential data exfiltration before it becomes a breach.",
        },
      ],
    },
    {
      title: "Accounts stay under control",
      icon: "🔐",
      description:
        "Use SentinelGrid as your identity provider or connect your existing one. Enforce MFA, spot dormant accounts and risky admins, and see who has access to what in one place.",
      features: [
        "Self-service access portal with approvals, not tickets",
        "Automatic detection of dormant accounts and shadow admins",
        "MFA enforcement without the hassle",
        "Access reviews made simple for compliance",
      ],
      alarms: [
        {
          title: "Suspicious sign-in spotted",
          description:
            "We'll spot suspicious sign-ins before they become account takeovers and help you lock the account in a click.",
        },
        {
          title: "Someone quietly became an admin",
          description:
            "We'll alert you anytime someone gains high-risk privileges or quietly becomes an admin.",
        },
        {
          title: "Password attack blocked",
          description:
            "We'll flag password-spray attacks hammering your logins so you can block bad actors and protect accounts.",
        },
      ],
    },
    {
      title: "Alerts turn into actions, not noise",
      icon: "⚡",
      description:
        "We ingest key logs into a right-sized security platform. AI-assisted playbooks cover the most common threats and give you prioritized incidents with clear next steps.",
      features: [
        "AI explains what happened and what to do about it",
        "One-click actions: lock an account, fix a bucket, open a ticket",
        "Built-in playbooks for common threats",
        "Focus on what matters, not endless alerts",
      ],
      alarms: [
        {
          title: "Phishing email reported",
          description:
            "When someone hits 'report phishing,' we'll hunt down every copy of that email and clean it up across your org.",
        },
        {
          title: "Phishing campaign detected",
          description:
            "We'll detect phishing campaigns hitting multiple inboxes and kill the blast radius before people start clicking.",
        },
        {
          title: "Malware caught on endpoint",
          description:
            "We'll catch malware on your endpoints early and walk you through isolating and cleaning the affected machines.",
        },
        {
          title: "Ransomware behavior detected",
          description:
            "If ransomware behavior starts on a server, we'll slam the brakes and guide you through containment and recovery.",
        },
        {
          title: "Lost or stolen device",
          description:
            "We'll treat lost and stolen laptops as security events, not just hardware issues, and help you shut down access fast.",
        },
      ],
    },
  ];

  return (
    <section id="three-pillars" className="py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-5xl font-semibold mb-4">
            What you get out of the box
          </h2>
          <p className="text-slate-400 text-lg max-w-3xl mx-auto">
            Three pillars work together so you can stop worrying about{" "}
            <span className="text-cyan-400">&quot;what did we miss?&quot;</span>{" "}
            and start seeing{" "}
            <span className="text-cyan-400">
              &quot;what do we fix next?&quot;
            </span>
          </p>
        </div>

        {/* Pillar Navigation */}
        <div className="flex flex-col md:flex-row gap-4 mb-8">
          {pillars.map((pillar, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedPillar(idx)}
              className={`flex-1 p-6 rounded-xl border-2 transition-all duration-300 text-left ${
                selectedPillar === idx
                  ? "border-cyan-500 bg-gradient-to-br from-cyan-500/10 to-blue-500/10 shadow-lg shadow-cyan-500/20"
                  : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-3xl">{pillar.icon}</span>
                <h3
                  className={`text-xl font-semibold ${
                    selectedPillar === idx ? "text-cyan-400" : "text-slate-200"
                  }`}
                >
                  {pillar.title}
                </h3>
              </div>
              <p
                className={`text-sm ${
                  selectedPillar === idx ? "text-slate-300" : "text-slate-500"
                }`}
              >
                {pillar.description}
              </p>
            </button>
          ))}
        </div>

        {/* Selected Pillar Content */}
        <div className="bg-gradient-to-br from-slate-900/80 to-slate-900/40 rounded-2xl border border-slate-800 p-8">
          <div className="grid md:grid-cols-2 gap-8">
            {/* Features */}
            <div>
              <h4 className="text-lg font-semibold text-cyan-400 mb-4">
                What it does
              </h4>
              <ul className="space-y-3">
                {pillars[selectedPillar].features.map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <span className="text-green-400 mt-1 flex-shrink-0">
                      ✓
                    </span>
                    <span className="text-slate-300">{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Alarms */}
            <div>
              <h4 className="text-lg font-semibold text-cyan-400 mb-4">
                Real threats we catch
              </h4>
              <div className="space-y-4">
                {pillars[selectedPillar].alarms.map((alarm, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-900/60 rounded-lg border border-slate-700 p-4 hover:border-cyan-500/30 transition-colors"
                  >
                    <h5 className="font-semibold text-slate-200 mb-2 text-sm">
                      {alarm.title}
                    </h5>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {alarm.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="text-center mt-10">
          <a
            href="#pricing"
            className="inline-flex items-center justify-center rounded-full px-8 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            See pricing
          </a>
        </div>
      </div>
    </section>
  );
}

