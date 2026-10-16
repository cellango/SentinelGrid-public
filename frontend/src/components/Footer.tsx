import { Logo } from "./Logo";
import { TrackedLink } from "@/components/marketing/TrackedLink";

export function Footer() {
  return (
    <footer className="border-t border-border bg-bg/50 py-12 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="grid md:grid-cols-4 gap-8 mb-8">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <Logo className="w-6 h-6" />
              <span className="font-semibold tracking-wide">
                Sentinel<span className="text-cyan-400">Grid</span>
              </span>
            </div>
            <p className="text-text-muted/70 text-sm">
              One queue for cloud, identity, endpoint, posture, and AI risk for growing teams.
            </p>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Product</h4>
            <ul className="space-y-2 text-sm text-text-muted/70">
              <li>
                <TrackedLink href="/product" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "product" }} className="hover:text-text-main/80">
                  Product overview
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/pricing" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "pricing" }} className="hover:text-text-main/80">
                  Pricing
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/roi" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "roi" }} className="hover:text-text-main/80">
                  ROI calculator
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/solutions" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "solutions" }} className="hover:text-text-main/80">
                  Solutions
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/partners" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "partners" }} className="hover:text-text-main/80">
                  Partner / MSP
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/product/ai-shield" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "ai_shield" }} className="hover:text-text-main/80">
                  AI Shield
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/compare/point-tools" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "compare_point_tools" }} className="hover:text-text-main/80">
                  Compare with point tools
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/compare/wiz" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "compare_wiz" }} className="hover:text-text-main/80">
                  Compare with Wiz
                </TrackedLink>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Company</h4>
            <ul className="space-y-2 text-sm text-text-muted/70">
              <li>
                <TrackedLink href="/customers" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "customers" }} className="hover:text-text-main/80">
                  Customer profiles
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/trust" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "trust" }} className="hover:text-text-main/80">
                  Trust Center
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/demo" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "demo" }} className="hover:text-text-main/80">
                  Book a demo
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/walkthrough" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "walkthrough" }} className="hover:text-text-main/80">
                  First-week walkthrough
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/privacy" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "privacy" }} className="hover:text-text-main/80">
                  Privacy
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/terms" eventName="marketing_nav_click" eventProps={{ source: "footer", target: "terms" }} className="hover:text-text-main/80">
                  Terms
                </TrackedLink>
              </li>
            </ul>
          </div>
          <div>
            <h4 className="font-semibold mb-3">Next step</h4>
            <ul className="space-y-2 text-sm text-text-muted/70">
              <li>
                <TrackedLink href="/signup" eventName="marketing_cta_click" eventProps={{ source: "footer", target: "signup" }} className="hover:text-text-main/80">
                  Get started
                </TrackedLink>
              </li>
              <li>
                <TrackedLink href="/demo" eventName="marketing_cta_click" eventProps={{ source: "footer", target: "demo" }} className="hover:text-text-main/80">
                  Book a demo
                </TrackedLink>
              </li>
            </ul>
          </div>
        </div>
        <div className="border-t border-border pt-6 text-sm text-text-muted/70 text-center">
          <p>© {new Date().getFullYear()} SentinelGrid. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
}
