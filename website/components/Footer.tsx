import Link from "next/link";
import { Logo } from "./Logo";

export function Footer() {
  return (
    <footer className="border-t border-slate-800 bg-slate-950/50 py-12 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="grid md:grid-cols-5 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <Logo className="w-6 h-6" />
              <span className="font-semibold tracking-wide">
                Sentinel<span className="text-cyan-400">Grid</span>
              </span>
            </div>
            <p className="text-slate-400 text-sm">
              Security in a box for teams that don&apos;t want to build a SOC.
            </p>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Product</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>
                <Link href="/#how-it-works" className="hover:text-slate-200">
                  How it works
                </Link>
              </li>
              <li>
                <Link href="/#security-in-a-box" className="hover:text-slate-200">
                  Security in a Box
                </Link>
              </li>
              <li>
                <Link href="/#pricing" className="hover:text-slate-200">
                  Pricing
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Services</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>
                <Link href="/ai-shield" className="hover:text-slate-200">
                  AI Shield
                </Link>
              </li>
              <li>
                <Link href="/ai-pentest" className="hover:text-slate-200">
                  Pentest Agent
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Company</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>
                <Link href="/trust" className="hover:text-slate-200">
                  Trust &amp; SOC 2
                </Link>
              </li>
              <li>
                <Link href="/demo" className="hover:text-slate-200">
                  Book a demo
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Get started</h4>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>
                <Link href="/signup" className="hover:text-slate-200">
                  Sign up
                </Link>
              </li>
              <li>
                <Link href="/demo" className="hover:text-slate-200">
                  Schedule demo
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-slate-800 pt-6 text-sm text-slate-400 text-center">
          <p>© {new Date().getFullYear()} SentinelGrid. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
