export type PlanTier = "protect" | "protect_defend" | "protect_defend_comply";
export type AiShieldMode = "hosted" | "self";
export type TicketingProvider = "internal" | "jira" | "servicenow";

export type ServicesSelected = {
  cloud?: boolean;
  git?: boolean;
  appsec?: boolean;
  aiShield?: AiShieldMode;
  socManaged?: boolean;
  ticketing?: TicketingProvider;
  ticketingProject?: string;
  idpProvider?: string;
  trustProfile?: {
    enabled?: boolean;
    frameworks?: string[];
    primaryDriver?: string;
    targetTimeline?: string;
  };
};

export const planTierOrder: PlanTier[] = [
  "protect",
  "protect_defend",
  "protect_defend_comply",
];

export const defaultPlanTier: PlanTier = planTierOrder[0];

const planTierRank: Record<PlanTier, number> = {
  protect: 1,
  protect_defend: 2,
  protect_defend_comply: 3,
};

function cleanString(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const text = value.trim();
  return text || undefined;
}

export function isPlanTier(value: string | null | undefined): value is PlanTier {
  if (!value) {
    return false;
  }
  return planTierOrder.includes(value as PlanTier);
}

export function normalizePlanTier(value: string | null | undefined): PlanTier | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized === "protect_comply") {
    return "protect_defend_comply";
  }

  return isPlanTier(normalized) ? normalized : null;
}

export function getPlanTierRank(value: string | null | undefined): number {
  const normalized = normalizePlanTier(value);
  return normalized ? planTierRank[normalized] : 0;
}

export function planIncludesCompliance(value: string | null | undefined): boolean {
  return normalizePlanTier(value) === "protect_defend_comply";
}

export function normalizeServicesSelected(raw: unknown): ServicesSelected {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return {};
  }

  const source = raw as Record<string, unknown>;
  const normalized: ServicesSelected = {};

  for (const key of ["cloud", "git", "appsec", "socManaged"] as const) {
    if (typeof source[key] === "boolean") {
      normalized[key] = source[key] as boolean;
    }
  }

  if (source.aiShield === "hosted" || source.aiShield === "self") {
    normalized.aiShield = source.aiShield;
  }

  if (
    source.ticketing === "internal" ||
    source.ticketing === "jira" ||
    source.ticketing === "servicenow"
  ) {
    normalized.ticketing = source.ticketing;
  }

  const ticketingProject = cleanString(source.ticketingProject);
  if (ticketingProject) {
    normalized.ticketingProject = ticketingProject;
  }

  const idpProvider = cleanString(source.idpProvider);
  if (idpProvider) {
    normalized.idpProvider = idpProvider;
  }

  if (
    source.trustProfile &&
    typeof source.trustProfile === "object" &&
    !Array.isArray(source.trustProfile)
  ) {
    const trustProfileSource = source.trustProfile as Record<string, unknown>;
    const trustProfile: NonNullable<ServicesSelected["trustProfile"]> = {};
    if (typeof trustProfileSource.enabled === "boolean") {
      trustProfile.enabled = trustProfileSource.enabled;
    }
    if (Array.isArray(trustProfileSource.frameworks)) {
      const frameworks = trustProfileSource.frameworks
        .map((item) => cleanString(item))
        .filter((item): item is string => Boolean(item));
      if (frameworks.length > 0) {
        trustProfile.frameworks = frameworks;
      }
    }
    const primaryDriver = cleanString(trustProfileSource.primaryDriver);
    if (primaryDriver) {
      trustProfile.primaryDriver = primaryDriver;
    }
    const targetTimeline = cleanString(trustProfileSource.targetTimeline);
    if (targetTimeline) {
      trustProfile.targetTimeline = targetTimeline;
    }
    if (Object.keys(trustProfile).length > 0) {
      normalized.trustProfile = trustProfile;
    }
  }

  return normalized;
}

export function applyPlanDefaults(
  planTier: string | null | undefined,
  servicesSelected?: ServicesSelected
): ServicesSelected {
  const normalizedPlanTier = normalizePlanTier(planTier) || defaultPlanTier;
  const services = normalizeServicesSelected(servicesSelected);

  if (services.cloud === undefined) {
    services.cloud = true;
  }

  if (normalizedPlanTier === "protect_defend_comply") {
    services.trustProfile = {
      ...(services.trustProfile || {}),
      enabled: true,
    };
  }

  return services;
}
