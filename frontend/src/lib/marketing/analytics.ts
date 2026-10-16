import { trackAnalyticsEvent } from "@/lib/analytics/events";

export type MarketingEventName =
  | "marketing_cta_click"
  | "marketing_nav_click"
  | "marketing_pricing_click"
  | "marketing_demo_submit";

export function trackMarketingEvent(
  name: MarketingEventName,
  properties: Record<string, unknown> = {}
) {
  if (typeof window === "undefined") return;

  const payload = { event: name, ...properties };
  trackAnalyticsEvent(name, properties);
  window.dispatchEvent(
    new CustomEvent("sentinelgrid:marketing-event", {
      detail: payload,
    })
  );
}
