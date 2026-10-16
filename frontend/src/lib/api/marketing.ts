import { withSessionAuthorization } from '@/lib/auth/session';

const API_BASE_URL = (() => {
  if (typeof window !== "undefined") {
    return `${window.location.origin}/api`;
  }
  if (process.env.NEXT_PUBLIC_IAM_AGENT_URL) {
    return process.env.NEXT_PUBLIC_IAM_AGENT_URL;
  }
  return "http://localhost:8005";
})();

const ANALYTICS_ANONYMOUS_ID_KEY = "sentinelgrid_analytics_anonymous_id";
const ANALYTICS_SESSION_ID_KEY = "sentinelgrid_analytics_session_id";
const ONBOARDING_METRICS_STORAGE_KEY = "sentinelgrid_onboarding_metrics_v1";

type StoredOnboardingMetrics = {
  planTier?: string;
  billingPeriod?: "monthly" | "yearly";
  employeeCount?: number;
  tenantId?: string;
  servicesSelected?: Record<string, unknown>;
};

export interface ActivationCohortRow {
  segment: string;
  onboarding_started: number;
  core_connectors_ready: number;
  first_value_ready: number;
  onboarding_completed: number;
  start_to_core_rate: number;
  start_to_first_value_rate: number;
  start_to_complete_rate: number;
  avg_hours_to_core: number | null;
  avg_hours_to_first_value: number | null;
  avg_hours_to_completion: number | null;
}

export interface MarketingFunnelSummary {
  window_days: number;
  summary: {
    cta_clicks: number;
    signup_started: number;
    leads_created: number;
    payment_started: number;
    payment_succeeded: number;
    demo_requests: number;
    onboarding_started: number;
    onboarding_completed: number;
  };
  conversion_rates: {
    cta_to_signup: number;
    signup_to_lead: number;
    lead_to_payment: number;
    payment_to_success: number;
    onboarding_start_to_complete: number;
  };
  daily_series: Array<{
    day: string;
    cta_clicks: number;
    signup_started: number;
    leads_created: number;
    payment_started: number;
    payment_succeeded: number;
    demo_requests: number;
  }>;
  top_sources: Array<{
    source: string;
    count: number;
  }>;
  recent_events: Array<{
    event: string;
    source?: string | null;
    lead_id?: string | null;
    plan_tier?: string | null;
    page_path?: string | null;
    occurred_at: string;
    properties: Record<string, unknown>;
  }>;
  demo_qualification: {
    summary: {
      total_demo_requests: number;
      standard_launch_path: number;
      guided_review: number;
      partner_motion: number;
      unknown: number;
    };
    top_guided_review_reasons: Array<{
      reason: string;
      count: number;
    }>;
    recent_demo_requests: Array<{
      source?: string | null;
      lead_id?: string | null;
      plan_tier?: string | null;
      occurred_at: string;
      recommended_path: string;
      motion: string;
      guided_review_reasons: string[];
    }>;
  };
  activation: {
    summary: {
      onboarding_started: number;
      core_connectors_ready: number;
      first_value_ready: number;
      onboarding_completed: number;
    };
    conversion_rates: {
      start_to_core_connectors: number;
      start_to_first_value: number;
      first_value_to_complete: number;
      start_to_complete: number;
    };
    timings_hours: {
      avg_to_core_connectors: number | null;
      avg_to_first_value: number | null;
      avg_to_completion: number | null;
    };
    daily_series: Array<{
      day: string;
      onboarding_started: number;
      core_connectors_ready: number;
      first_value_ready: number;
      onboarding_completed: number;
    }>;
    step_breakdown: Array<{
      step_id: string;
      viewed: number;
      completed: number;
      skipped: number;
      completion_rate: number;
      skip_rate: number;
    }>;
    recent_events: Array<{
      event: string;
      step_id?: string | null;
      source?: string | null;
      plan_tier?: string | null;
      occurred_at: string;
      properties: Record<string, unknown>;
    }>;
    cohorts: {
      plan_tiers: ActivationCohortRow[];
      identity_providers: ActivationCohortRow[];
      trust_motions: ActivationCohortRow[];
      billing_periods: ActivationCohortRow[];
    };
  };
}

function buildMarketingUrl(path: string): string {
  return API_BASE_URL.includes("/api")
    ? `${API_BASE_URL}/v1/marketing${path}`
    : `${API_BASE_URL}/api/v1/marketing${path}`;
}

function getOrCreateStorageId(storage: Storage, key: string): string {
  const existing = storage.getItem(key);
  if (existing) {
    return existing;
  }

  const value =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `sg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  storage.setItem(key, value);
  return value;
}

function getAnonymousId() {
  if (typeof window === "undefined") return "";
  return getOrCreateStorageId(window.localStorage, ANALYTICS_ANONYMOUS_ID_KEY);
}

function getSessionId() {
  if (typeof window === "undefined") return "";
  return getOrCreateStorageId(window.sessionStorage, ANALYTICS_SESSION_ID_KEY);
}

function readStoredOnboardingMetrics(): StoredOnboardingMetrics | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = localStorage.getItem(ONBOARDING_METRICS_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StoredOnboardingMetrics;
  } catch {
    return null;
  }
}

function deriveEmployeeBand(employeeCount?: number): string | undefined {
  if (typeof employeeCount !== "number" || Number.isNaN(employeeCount) || employeeCount <= 0) {
    return undefined;
  }
  if (employeeCount <= 50) return "1_50";
  if (employeeCount <= 100) return "51_100";
  if (employeeCount <= 250) return "101_250";
  if (employeeCount <= 500) return "251_500";
  return "500_plus";
}

function buildAnalyticsContextProperties() {
  const metrics = readStoredOnboardingMetrics();
  const servicesSelected = metrics?.servicesSelected || {};
  const trustProfile =
    servicesSelected &&
    typeof servicesSelected === "object" &&
    typeof servicesSelected.trustProfile === "object"
      ? (servicesSelected.trustProfile as Record<string, unknown>)
      : undefined;

  return {
    tenant_id: metrics?.tenantId,
    plan: metrics?.planTier,
    plan_tier: metrics?.planTier,
    billing_period: metrics?.billingPeriod,
    employee_count: metrics?.employeeCount,
    employee_band: deriveEmployeeBand(metrics?.employeeCount),
    idp_provider:
      typeof servicesSelected?.idpProvider === "string"
        ? servicesSelected.idpProvider
        : undefined,
    trust_enabled:
      trustProfile && typeof trustProfile.enabled === "boolean"
        ? trustProfile.enabled
        : undefined,
    soc_managed:
      typeof servicesSelected?.socManaged === "boolean"
        ? servicesSelected.socManaged
        : undefined,
    cloud_enabled:
      typeof servicesSelected?.cloud === "boolean"
        ? servicesSelected.cloud
        : undefined,
    git_enabled:
      typeof servicesSelected?.git === "boolean"
        ? servicesSelected.git
        : undefined,
    appsec_enabled:
      typeof servicesSelected?.appsec === "boolean"
        ? servicesSelected.appsec
        : undefined,
    ai_shield_mode:
      typeof servicesSelected?.aiShield === "string"
        ? servicesSelected.aiShield
        : undefined,
  };
}

function shouldPersistAnalyticsEvent(name: string) {
  return (
    name.startsWith("marketing_") ||
    name.startsWith("signup_") ||
    name.startsWith("onboarding_")
  );
}

export function persistAnalyticsEvent(
  name: string,
  properties: Record<string, unknown> = {}
) {
  if (typeof window === "undefined" || !shouldPersistAnalyticsEvent(name)) {
    return;
  }

  const analyticsContext = buildAnalyticsContextProperties();
  const payload = {
    event: name,
    properties: {
      ...analyticsContext,
      ...properties,
    },
    page_path: window.location.pathname,
    referrer: document.referrer || undefined,
    user_agent: navigator.userAgent,
    occurred_at: new Date().toISOString(),
    anonymous_id: getAnonymousId(),
    session_id: getSessionId(),
    lead_id:
      typeof properties.lead_id === "string"
        ? properties.lead_id
        : typeof properties.leadId === "string"
        ? properties.leadId
        : undefined,
  };

  void fetch(buildMarketingUrl("/events"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => undefined);
}

export async function getMarketingFunnelSummary(
  days = 30
): Promise<MarketingFunnelSummary> {
  const headers = withSessionAuthorization({
    "Content-Type": "application/json",
  });

  const response = await fetch(buildMarketingUrl(`/funnel/summary?days=${days}`), {
    method: "GET",
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({ detail: `API call failed with status ${response.status}` }));
    throw new Error(errorData.detail || `API call failed with status ${response.status}`);
  }

  return response.json();
}
