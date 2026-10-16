export default function WhySentinelGrid() {
  return (
    <section id="solutions" className="py-18 px-6">
      <div className="max-w-7xl mx-auto">
        <h2 className="text-3xl font-bold mb-2 tracking-tight">Why teams choose SentinelGrid</h2>
        <div className="grid gap-6 md:grid-cols-3 mt-8">
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h3 className="text-xl font-semibold mb-2">AI‑first, not tool‑first</h3>
            <p className="text-text-muted text-sm">
              SentinelGrid is designed as an AI‑driven SOC from day one — agents do the repetitive work
              while humans handle what matters.
            </p>
          </div>
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h3 className="text-xl font-semibold mb-2">Local, private models</h3>
            <p className="text-text-muted text-sm">
              Run open cybersecurity models locally. Your incidents never train a shared black‑box model
              used by other customers.
            </p>
          </div>
          <div className="bg-[rgba(15,23,42,0.9)] rounded-xl border border-[rgba(15,23,42,0.95)] p-6">
            <h3 className="text-xl font-semibold mb-2">Security that scales</h3>
            <p className="text-text-muted text-sm">
              Add coverage and capabilities without growing headcount.
              Security becomes a subscription, not a hiring crisis.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

