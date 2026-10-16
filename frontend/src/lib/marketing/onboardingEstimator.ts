import {
  getMarketingPlan,
  type MarketingPlan,
  type MarketingPlanKey,
} from "@/lib/marketing/packages";

export type EstimatorCloudProfile = "single" | "two" | "three_plus";
export type EstimatorIdentityProfile =
  | "microsoft_entra"
  | "google_workspace"
  | "okta"
  | "mixed";
export type EstimatorEndpointProfile = "none" | "pilot" | "full";
export type EstimatorReportingProfile = "standard" | "audit_ready";

export type OnboardingEstimatorInput = {
  cloudProfile: EstimatorCloudProfile;
  identityProfile: EstimatorIdentityProfile;
  endpointProfile: EstimatorEndpointProfile;
  reportingProfile: EstimatorReportingProfile;
};

export type OnboardingEstimate = {
  recommendedPlanKey: MarketingPlanKey;
  recommendedPlan: MarketingPlan;
  setupWindow: string;
  firstValueWindow: string;
  recommendedPath: "signup" | "demo";
  ctaHref: string;
  ctaLabel: string;
  rationale: string[];
  assumptions: string[];
  includedOnboarding: string[];
};

function getRecommendedPlanKey(
  input: OnboardingEstimatorInput
): MarketingPlanKey {
  if (input.reportingProfile === "audit_ready") {
    return "protect_defend_comply";
  }

  if (input.endpointProfile !== "none") {
    return "protect_defend";
  }

  return "protect";
}

function getComplexityScore(input: OnboardingEstimatorInput): number {
  let score = 0;

  score += input.cloudProfile === "single" ? 0 : input.cloudProfile === "two" ? 1 : 2;
  score +=
    input.identityProfile === "microsoft_entra" || input.identityProfile === "google_workspace"
      ? 0
      : input.identityProfile === "okta"
      ? 1
      : 2;
  score += input.endpointProfile === "none" ? 0 : input.endpointProfile === "pilot" ? 1 : 2;

  if (input.reportingProfile === "audit_ready") {
    score += 1;
  }

  return score;
}

function getSetupWindow(score: number) {
  if (score <= 1) return "2-4 hours";
  if (score <= 3) return "Half day to 1 business day";
  if (score <= 5) return "1-2 business days";
  return "2-4 business days";
}

function getFirstValueWindow(score: number) {
  if (score <= 1) return "Same day";
  if (score <= 3) return "Same day to next day";
  if (score <= 5) return "Within 1-2 days";
  return "Within 2-3 days";
}

function getRationale(input: OnboardingEstimatorInput): string[] {
  const items = [];

  if (input.cloudProfile === "single") {
    items.push("One primary cloud environment fits the standard onboarding path.");
  } else if (input.cloudProfile === "two") {
    items.push("Two cloud environments add connector sequencing and validation work.");
  } else {
    items.push("Three or more environments usually need rollout planning before the first full pass.");
  }

  if (input.identityProfile === "microsoft_entra") {
    items.push("Microsoft 365 / Entra is the fastest identity path in the current SMB motion.");
  } else if (input.identityProfile === "google_workspace") {
    items.push("Google Workspace fits the core path, but it is still a lighter implementation than Entra.");
  } else if (input.identityProfile === "okta") {
    items.push("Okta is supported, but it usually needs a little more connector validation than the default Microsoft path.");
  } else {
    items.push("Mixed identity or a not-yet-decided identity path usually benefits from a live rollout discussion.");
  }

  if (input.endpointProfile === "pilot") {
    items.push("A pilot endpoint rollout pushes the fit toward Protect + Defend.");
  } else if (input.endpointProfile === "full") {
    items.push("A broad endpoint rollout usually needs rollout planning, policy review, and guided sequencing.");
  }

  if (input.reportingProfile === "audit_ready") {
    items.push("Audit-ready reporting adds reporting scope and evidence output setup to the first-week path.");
  }

  return items;
}

function getAssumptions(input: OnboardingEstimatorInput): string[] {
  const assumptions = [
    "Standard onboarding is assumed for core connectors and normal SMB permission models.",
    "The estimate assumes one operator-owned rollout rather than a multi-team enterprise project.",
  ];

  if (input.cloudProfile === "single") {
    assumptions.push("One primary AWS or Azure environment is in scope first.");
  } else if (input.cloudProfile === "two") {
    assumptions.push("Two core cloud environments are in scope for the first rollout.");
  } else {
    assumptions.push("Three or more environments are in scope, which usually requires a guided rollout discussion.");
  }

  if (input.endpointProfile === "none") {
    assumptions.push("No endpoint deployment is required in the first pass.");
  } else if (input.endpointProfile === "pilot") {
    assumptions.push("Endpoint rollout is limited to a pilot wave rather than the full fleet.");
  } else {
    assumptions.push("Endpoint coverage is broad from the start, which increases coordination effort.");
  }

  return assumptions;
}

export function estimateOnboardingScenario(
  input: OnboardingEstimatorInput
): OnboardingEstimate {
  const recommendedPlanKey = getRecommendedPlanKey(input);
  const recommendedPlan = getMarketingPlan(recommendedPlanKey);
  const complexityScore = getComplexityScore(input);
  const needsGuidedReview =
    complexityScore >= 5 ||
    input.cloudProfile === "three_plus" ||
    input.identityProfile === "mixed" ||
    input.endpointProfile === "full" ||
    input.reportingProfile === "audit_ready";

  const ctaBase = needsGuidedReview ? "/demo" : "/signup";

  return {
    recommendedPlanKey,
    recommendedPlan,
    setupWindow: getSetupWindow(complexityScore),
    firstValueWindow: getFirstValueWindow(complexityScore),
    recommendedPath: needsGuidedReview ? "demo" : "signup",
    ctaHref: `${ctaBase}?plan=${recommendedPlanKey}`,
    ctaLabel: needsGuidedReview ? "Talk through this rollout" : "Start guided onboarding",
    rationale: getRationale(input),
    assumptions: getAssumptions(input),
    includedOnboarding: recommendedPlan.onboarding,
  };
}
