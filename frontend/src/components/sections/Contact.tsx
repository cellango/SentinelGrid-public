'use client';

export default function Contact() {
  return (
    <section id="contact" className="py-18 px-6">
      <div className="max-w-7xl mx-auto grid gap-10 md:grid-cols-[1.1fr_1fr]">
        <div>
          <h2 className="text-3xl font-bold mb-2 tracking-tight">
            Ready to stop treating security as a side project?
          </h2>
          <p className="text-text-muted max-w-xl">
            Tell us a bit about your environment and we'll walk you through how SentinelGrid
            would plug into your stack.
          </p>
        </div>
        <form className="bg-[rgba(15,23,42,0.95)] p-6 rounded-xl border border-[rgba(15,23,42,0.95)]">
          <div className="mb-4">
            <label className="block text-xs text-text-muted mb-1">Work email</label>
            <input
              type="email"
              placeholder="you@company.com"
              required
              className="w-full rounded-[10px] border border-[rgba(31,41,55,1)] bg-bg text-text-main px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
            />
          </div>
          <div className="mb-4">
            <label className="block text-xs text-text-muted mb-1">Company</label>
            <input
              type="text"
              placeholder="Company name"
              required
              className="w-full rounded-[10px] border border-[rgba(31,41,55,1)] bg-bg text-text-main px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
            />
          </div>
          <div className="mb-4">
            <label className="block text-xs text-text-muted mb-1">Rough team size</label>
            <select className="w-full rounded-[10px] border border-[rgba(31,41,55,1)] bg-bg text-text-main px-3 py-2.5 text-sm focus:outline-none focus:border-primary">
              <option>&lt; 100 employees</option>
              <option>100–500 employees</option>
              <option>500–2,000 employees</option>
              <option>2,000+ employees</option>
            </select>
          </div>
          <div className="mb-4">
            <label className="block text-xs text-text-muted mb-1">What are you struggling with?</label>
            <textarea
              rows={3}
              placeholder="Alert overload, no SOC, compliance pressure..."
              className="w-full rounded-[10px] border border-[rgba(31,41,55,1)] bg-bg text-text-main px-3 py-2.5 text-sm focus:outline-none focus:border-primary"
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2.5 rounded-full text-sm bg-gradient-to-r from-primary to-secondary text-bg font-semibold hover:brightness-105"
          >
            Request a demo
          </button>
        </form>
      </div>
    </section>
  );
}

