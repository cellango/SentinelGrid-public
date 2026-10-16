import type { OnboardingStatus } from "@/lib/api/onboarding";
import { trackAnalyticsEvent } from "@/lib/analytics/events";
import { isPeopleReady } from "./steps";

const STORAGE_KEY = "sentinelgrid_onboarding_metrics_v1";

export type OnboardingEventName =
  | "signup_started"
  | "signup_lead_created"
  | "signup_payment_viewed"
  | "signup_payment_started"
  | "signup_payment_succeeded"
  | "onboarding_started"
  | "onboarding_step_viewed"
  | "onboarding_step_completed"
  | "onboarding_step_skipped"
  | "onboarding_core_connectors_ready"
  | "onboarding_first_value_ready"
  | "onboarding_completed"
  | "onboarding_cta_click"
  | "onboarding_banner_dismissed";

export interface OnboardingMetrics {
  version: 1;
  lastUpdatedAt: string;
  signupStartedAt?: string;
  leadCreatedAt?: string;
  paymentViewedAt?: string;
  paymentStartedAt?: string;
  paymentSucceededAt?: string;
  onboardingStartedAt?: string;
  firstConnectorConnectedAt?: string;
  coreConnectorsReadyAt?: string;
  firstValueReadyAt?: string;
  onboardingCompletedAt?: string;
  leadId?: string;
  tenantId?: string;
  planTier?: string;
  employeeCount?: number;
  billingPeriod?: "monthly" | "yearly";
  servicesSelected?: Record<string, unknown>;
  completedSteps: string[];
  skippedSteps: string[];
  stepViewedAt: Record<string, string>;
  stepCompletedAt: Record<string, string>;
  stepSkippedAt: Record<string, string>;
}

declare global {
  interface WindowEventMap {
    "sentinelgrid:onboarding-metrics-updated": CustomEvent<OnboardingMetrics>;
  }
}

function isBrowser() {
  return typeof window !== "undefined";
}

function nowIso() {
  return new Date().toISOString();
}

function defaultMetrics(): OnboardingMetrics {
  return {
    version: 1,
    lastUpdatedAt: nowIso(),
    completedSteps: [],
    skippedSteps: [],
    stepViewedAt: {},
    stepCompletedAt: {},
    stepSkippedAt: {},
  };
}

function cloneMetrics(metrics: OnboardingMetrics): OnboardingMetrics {
  return {
    ...metrics,
    completedSteps: [...metrics.completedSteps],
    skippedSteps: [...metrics.skippedSteps],
    stepViewedAt: { ...metrics.stepViewedAt },
    stepCompletedAt: { ...metrics.stepCompletedAt },
    stepSkippedAt: { ...metrics.stepSkippedAt },
    servicesSelected: metrics.servicesSelected
      ? { ...metrics.servicesSelected }
      : undefined,
  };
}

function emitMetricsUpdate(metrics: OnboardingMetrics) {
  if (!isBrowser()) return;
  window.dispatchEvent(
    new CustomEvent("sentinelgrid:onboarding-metrics-updated", {
      detail: metrics,
    })
  );
}

export function readOnboardingMetrics(): OnboardingMetrics | null {
  if (!isBrowser()) return null;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as OnboardingMetrics;
    return {
      ...defaultMetrics(),
      ...parsed,
      completedSteps: Array.isArray(parsed.completedSteps) ? parsed.completedSteps : [],
      skippedSteps: Array.isArray(parsed.skippedSteps) ? parsed.skippedSteps : [],
      stepViewedAt: parsed.stepViewedAt || {},
      stepCompletedAt: parsed.stepCompletedAt || {},
      stepSkippedAt: parsed.stepSkippedAt || {},
    };
  } catch {
    return null;
  }
}

function writeOnboardingMetrics(metrics: OnboardingMetrics) {
  if (!isBrowser()) return metrics;

  localStorage.setItem(STORAGE_KEY, JSON.stringify(metrics));
  emitMetricsUpdate(metrics);
  return metrics;
}

function updateOnboardingMetrics(
  mutator: (draft: OnboardingMetrics) => OnboardingMetrics | void
) {
  const current = readOnboardingMetrics() || defaultMetrics();
  const draft = cloneMetrics(current);
  const next = (mutator(draft) as OnboardingMetrics | void) || draft;
  next.lastUpdatedAt = nowIso();
  return writeOnboardingMetrics(next);
}

function addUnique(items: string[], value: string) {
  if (!items.includes(value)) {
    items.push(value);
  }
}

export function trackOnboardingEvent(
  name: OnboardingEventName,
  properties: Record<string, unknown> = {}
) {
  trackAnalyticsEvent(name, properties);
}

export function mergeOnboardingMetricsContext(context: {
  tenantId?: string;
  planTier?: string;
  billingPeriod?: "monthly" | "yearly";
  employeeCount?: number;
  servicesSelected?: Record<string, unknown>;
}) {
  return updateOnboardingMetrics((draft) => {
    if (context.tenantId) {
      draft.tenantId = context.tenantId;
    }
    if (context.planTier) {
      draft.planTier = context.planTier;
    }
    if (context.billingPeriod) {
      draft.billingPeriod = context.billingPeriod;
    }
    if (typeof context.employeeCount === "number") {
      draft.employeeCount = context.employeeCount;
    }
    if (context.servicesSelected) {
      draft.servicesSelected = {
        ...(draft.servicesSelected || {}),
        ...context.servicesSelected,
      };
    }
  });
}

export function recordSignupStarted(properties: {
  source?: string;
  planTier?: string;
} = {}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.signupStartedAt) {
      draft.signupStartedAt = nowIso();
      created = true;
    }
    if (properties.planTier) {
      draft.planTier = properties.planTier;
    }
  });

  if (created) {
    trackOnboardingEvent("signup_started", {
      source: properties.source || "signup_page",
      plan: metrics.planTier,
    });
  }

  return metrics;
}

export function recordSignupLeadCreated(properties: {
  leadId: string;
  planTier?: string;
  employeeCount?: number;
  servicesSelected?: Record<string, unknown>;
}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.leadCreatedAt) {
      draft.leadCreatedAt = nowIso();
      created = true;
    }
    draft.leadId = properties.leadId;
    if (properties.planTier) {
      draft.planTier = properties.planTier;
    }
    if (typeof properties.employeeCount === "number") {
      draft.employeeCount = properties.employeeCount;
    }
    if (properties.servicesSelected) {
      draft.servicesSelected = properties.servicesSelected;
    }
  });

  if (created) {
    trackOnboardingEvent("signup_lead_created", {
      lead_id: properties.leadId,
      plan: properties.planTier,
      employee_count: properties.employeeCount,
    });
  }

  return metrics;
}

export function recordPaymentViewed(properties: {
  source?: string;
  planTier?: string;
} = {}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.paymentViewedAt) {
      draft.paymentViewedAt = nowIso();
      created = true;
    }
    if (properties.planTier) {
      draft.planTier = properties.planTier;
    }
  });

  if (created) {
    trackOnboardingEvent("signup_payment_viewed", {
      source: properties.source || "signup_payment_step",
      plan: properties.planTier || metrics.planTier,
    });
  }

  return metrics;
}

export function recordPaymentStarted(properties: {
  planTier?: string;
  billingPeriod?: "monthly" | "yearly";
  requiresSalesContact?: boolean;
}) {
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.paymentStartedAt) {
      draft.paymentStartedAt = nowIso();
    }
    if (properties.planTier) {
      draft.planTier = properties.planTier;
    }
    if (properties.billingPeriod) {
      draft.billingPeriod = properties.billingPeriod;
    }
  });

  trackOnboardingEvent("signup_payment_started", {
    plan: properties.planTier || metrics.planTier,
    billing_period: properties.billingPeriod,
    sales_contact: properties.requiresSalesContact === true,
  });

  return metrics;
}

export function recordPaymentSucceeded(properties: {
  tenantId?: string;
  planTier?: string;
}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.paymentSucceededAt) {
      draft.paymentSucceededAt = nowIso();
      created = true;
    }
    if (properties.tenantId) {
      draft.tenantId = properties.tenantId;
    }
    if (properties.planTier) {
      draft.planTier = properties.planTier;
    }
  });

  if (created) {
    trackOnboardingEvent("signup_payment_succeeded", {
      tenant_id: properties.tenantId,
      plan: properties.planTier || metrics.planTier,
    });
  }

  return metrics;
}

export function recordOnboardingStarted(properties: {
  initialStep?: number;
  totalSteps?: number;
} = {}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.onboardingStartedAt) {
      draft.onboardingStartedAt = nowIso();
      created = true;
    }
  });

  if (created) {
    trackOnboardingEvent("onboarding_started", {
      initial_step: properties.initialStep,
      total_steps: properties.totalSteps,
    });
  }

  return metrics;
}

export function recordOnboardingStepViewed(properties: {
  stepId: string;
  stepIndex: number;
  totalSteps: number;
}) {
  updateOnboardingMetrics((draft) => {
    if (!draft.stepViewedAt[properties.stepId]) {
      draft.stepViewedAt[properties.stepId] = nowIso();
    }
  });

  trackOnboardingEvent("onboarding_step_viewed", {
    step_id: properties.stepId,
    step_index: properties.stepIndex,
    total_steps: properties.totalSteps,
  });
}

export function recordOnboardingStepCompleted(properties: {
  stepId: string;
  stepIndex: number;
  totalSteps: number;
}) {
  let coreConnectorsReady = false;
  const metrics = updateOnboardingMetrics((draft) => {
    const completedAt = draft.stepCompletedAt[properties.stepId] || nowIso();
    draft.stepCompletedAt[properties.stepId] = completedAt;
    addUnique(draft.completedSteps, properties.stepId);

    if (
      !draft.firstConnectorConnectedAt &&
      (properties.stepId === "idp" || properties.stepId === "cloud")
    ) {
      draft.firstConnectorConnectedAt = completedAt;
    }

    if (
      !draft.coreConnectorsReadyAt &&
      draft.completedSteps.includes("idp") &&
      draft.completedSteps.includes("cloud")
    ) {
      draft.coreConnectorsReadyAt = completedAt;
      coreConnectorsReady = true;
    }
  });

  trackOnboardingEvent("onboarding_step_completed", {
    step_id: properties.stepId,
    step_index: properties.stepIndex,
    total_steps: properties.totalSteps,
  });

  if (coreConnectorsReady) {
    trackOnboardingEvent("onboarding_core_connectors_ready", {
      first_connector_at: metrics.firstConnectorConnectedAt,
      core_connectors_ready_at: metrics.coreConnectorsReadyAt,
    });
  }

  return metrics;
}

export function recordOnboardingStepSkipped(properties: {
  stepId: string;
  stepIndex: number;
  totalSteps: number;
}) {
  updateOnboardingMetrics((draft) => {
    draft.stepSkippedAt[properties.stepId] = draft.stepSkippedAt[properties.stepId] || nowIso();
    addUnique(draft.skippedSteps, properties.stepId);
  });

  trackOnboardingEvent("onboarding_step_skipped", {
    step_id: properties.stepId,
    step_index: properties.stepIndex,
    total_steps: properties.totalSteps,
  });
}

export function recordFirstValueReady(properties: {
  source?: string;
  incidents?: number;
  recommendations?: number;
  cloudIssues?: number;
  identityIssues?: number;
}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.firstValueReadyAt) {
      draft.firstValueReadyAt = nowIso();
      created = true;
    }
  });

  if (created) {
    trackOnboardingEvent("onboarding_first_value_ready", {
      source: properties.source || "welcome_dashboard",
      incidents: properties.incidents || 0,
      recommendations: properties.recommendations || 0,
      cloud_issues: properties.cloudIssues || 0,
      identity_issues: properties.identityIssues || 0,
      first_value_ready_at: metrics.firstValueReadyAt,
    });
  }

  return metrics;
}

export function recordOnboardingCompleted(properties: {
  source?: string;
  totalSteps?: number;
} = {}) {
  let created = false;
  const metrics = updateOnboardingMetrics((draft) => {
    if (!draft.onboardingCompletedAt) {
      draft.onboardingCompletedAt = nowIso();
      created = true;
    }
  });

  if (created) {
    trackOnboardingEvent("onboarding_completed", {
      source: properties.source || "onboarding_wizard",
      total_steps: properties.totalSteps,
      completed_at: metrics.onboardingCompletedAt,
    });
  }

  return metrics;
}

export function recordOnboardingCtaClick(properties: {
  source: string;
  target?: string;
  stepId?: string | null;
}) {
  trackOnboardingEvent("onboarding_cta_click", {
    source: properties.source,
    target: properties.target,
    step_id: properties.stepId,
  });
}

export function recordOnboardingBannerDismissed(properties: {
  source: string;
  progressPct?: number;
}) {
  trackOnboardingEvent("onboarding_banner_dismissed", {
    source: properties.source,
    progress_pct: properties.progressPct,
  });
}

export function syncOnboardingMetricsFromStatus(status: OnboardingStatus | null) {
  if (!status) {
    return readOnboardingMetrics();
  }

  return updateOnboardingMetrics((draft) => {
    if (status.services_selected) {
      draft.servicesSelected = {
        ...(draft.servicesSelected || {}),
        ...status.services_selected,
      };
    }

    const maybeCompleteStep = (stepId: string, timestamp?: string | null) => {
      if (!draft.stepCompletedAt[stepId]) {
        draft.stepCompletedAt[stepId] = timestamp || nowIso();
      }
      addUnique(draft.completedSteps, stepId);
    };

    if (status.idp_connected || status.step_idp_completed) {
      maybeCompleteStep("idp", status.step_idp_completed_at);
    }
    if (status.cloud_connected || status.step_cloud_completed) {
      maybeCompleteStep("cloud", status.step_cloud_completed_at);
    }
    if (status.endpoint_deployed || status.step_endpoint_completed) {
      maybeCompleteStep("endpoint", status.step_endpoint_completed_at);
    }
    if (status.git_connected || status.step_git_completed) {
      maybeCompleteStep("git", status.step_git_completed_at);
    }
    if (status.appsec_connected) {
      maybeCompleteStep("appsec");
    }
    if (status.ai_connected) {
      maybeCompleteStep("ai");
    }
    if (status.ticketing_connected) {
      maybeCompleteStep("ticketing");
    }

    if (isPeopleReady(status)) {
      maybeCompleteStep("tenant");
    }

    if (!draft.firstConnectorConnectedAt) {
      const firstConnectedTimestamp =
        status.step_idp_completed_at ||
        status.step_cloud_completed_at ||
        (status.idp_connected || status.cloud_connected ? nowIso() : undefined);
      if (firstConnectedTimestamp) {
        draft.firstConnectorConnectedAt = firstConnectedTimestamp;
      }
    }

    if (
      !draft.coreConnectorsReadyAt &&
      (status.idp_connected || status.step_idp_completed) &&
      (status.cloud_connected || status.step_cloud_completed)
    ) {
      draft.coreConnectorsReadyAt = status.step_cloud_completed_at || status.step_idp_completed_at || nowIso();
    }

    const overallComplete = (status.overall_complete ?? status.onboarding_completed) === true;
    if (!draft.onboardingCompletedAt && overallComplete && isPeopleReady(status)) {
      draft.onboardingCompletedAt = nowIso();
    }
  });
}
