import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function DemoPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      <Header />
      <div className="max-w-2xl mx-auto px-6 py-20">
        <h1 className="text-4xl font-semibold mb-4">Book a demo</h1>
        <p className="text-slate-400 mb-8">
          See how SentinelGrid can protect your business. Schedule a 30-minute demo with our team.
        </p>
        <form className="space-y-4">
          <div>
            <label className="block text-sm text-slate-300 mb-1">Name</label>
            <input
              type="text"
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-slate-200"
              placeholder="Jane Doe"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-1">Work email</label>
            <input
              type="email"
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-slate-200"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-1">Company name</label>
            <input
              type="text"
              required
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-slate-200"
              placeholder="Company Inc."
            />
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-1">Company size</label>
            <select className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-slate-200">
              <option>&lt; 25 employees</option>
              <option>25 – 100 employees</option>
              <option>100 – 250 employees</option>
              <option>250+ employees</option>
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-300 mb-1">Message (optional)</label>
            <textarea
              rows={4}
              className="w-full rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 text-slate-200"
              placeholder="Tell us what you'd like to see..."
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-full px-6 py-3 text-sm font-medium bg-cyan-400 text-slate-950 hover:bg-cyan-300 transition-colors"
          >
            Schedule demo
          </button>
        </form>
        <p className="text-xs text-slate-400 mt-6 text-center">
          Or{" "}
          <Link href="/signup" className="text-cyan-400 hover:underline">
            start a free trial
          </Link>{" "}
          to explore on your own.
        </p>
      </div>
      <Footer />
    </main>
  );
}

