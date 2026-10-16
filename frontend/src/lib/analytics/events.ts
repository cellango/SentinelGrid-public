import { persistAnalyticsEvent } from "@/lib/api/marketing";

declare global {
  interface Window {
    dataLayer?: Array<Record<string, unknown>>;
  }
}

export function trackAnalyticsEvent(
  name: string,
  properties: Record<string, unknown> = {}
) {
  if (typeof window === "undefined") return;

  const payload = {
    event: name,
    ...properties,
  };

  window.dataLayer?.push(payload);
  window.dispatchEvent(
    new CustomEvent("sentinelgrid:analytics-event", {
      detail: payload,
    })
  );
  persistAnalyticsEvent(name, properties);
}
