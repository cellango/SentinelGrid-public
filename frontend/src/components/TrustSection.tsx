export function TrustSection() {
  return (
    <section id="trust" className="py-20 px-6">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-semibold mb-4">
            Built to be trusted, not to farm your data
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            SentinelGrid is Cybersecurity‑as‑a‑Service, but we know we&apos;re only useful
            if you trust us with your telemetry.
          </p>
        </div>

        <div className="space-y-8">
          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6">
            <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
              <span className="text-cyan-400">🔒</span>
              Your data, your boundary
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Logs are stored in your region in encrypted object storage and tenant‑specific
              indexes. We don&apos;t mix customer data and we don&apos;t sell it. Every customer
              is a separate tenant with isolated data paths.
            </p>
          </div>

          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6">
            <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
              <span className="text-cyan-400">🛡️</span>
              Least‑privilege access
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Our connectors use read‑only roles and the minimum set of permissions we need
              to monitor your environment. We publish the exact IAM policies we ask you to
              apply. No blanket * permissions; no ability to change resources.
            </p>
          </div>

          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6">
            <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
              <span className="text-cyan-400">🔐</span>
              Encryption by default
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Data is encrypted in transit with TLS 1.2+ and at rest using industry‑standard
              encryption. Keys are managed via cloud KMS or customer‑managed keys for larger
              deployments.
            </p>
          </div>

          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6">
            <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
              <span className="text-cyan-400">🤖</span>
              AI, but not at your expense
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Our security models run in our controlled environment or in your own cloud. Your
              incidents and logs are never sent to public AI services, and your data doesn&apos;t
              train a global model shared with other customers. Per‑tenant adapters ensure
              your incidents don&apos;t bleed into others.
            </p>
          </div>

          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6">
            <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
              <span className="text-cyan-400">📋</span>
              Transparent and auditable
            </h3>
            <p className="text-slate-300 text-sm leading-relaxed">
              Every sensitive action in SentinelGrid — playbooks run, settings changed, access
              granted — is logged. You can export these audit logs into your own logging platform if you
              want an extra copy. Clear data retention windows (e.g. 30 days hot, 12 months
              archive) are visible and configurable.
            </p>
          </div>
        </div>

        <div className="mt-10 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-2xl border border-cyan-500/20 p-8">
          <h3 className="text-2xl font-semibold mb-3">
            How SentinelGrid protects your business
          </h3>
          <ul className="space-y-3 text-slate-300">
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 mt-0.5">•</span>
              <span>
                <strong>Always‑on monitoring.</strong> We continuously ingest identity, cloud
                and endpoint telemetry and normalize it into a security data lake.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 mt-0.5">•</span>
              <span>
                <strong>Built‑in detections.</strong> We ship with a baseline of rules for
                suspicious logins, misconfigurations and common attack patterns tuned for
                small and mid‑sized teams.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 mt-0.5">•</span>
              <span>
                <strong>AI‑assisted triage.</strong> Our security‑aware models review alerts,
                add context from your environment, map them to NIST and MITRE, and recommend
                playbooks — so you see what matters first.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 mt-0.5">•</span>
              <span>
                <strong>Playbooks and automation.</strong> For common scenarios like phishing,
                suspicious logins or public cloud storage, we can run pre‑approved playbooks
                and open tickets automatically.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-cyan-400 mt-0.5">•</span>
              <span>
                <strong>Human review when it counts.</strong> You decide which actions
                we&apos;re allowed to automate and which require approval from your team.
              </span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
}
