import {
  aiShieldAddon,
  getMarketingPlan,
  type MarketingPlanKey,
} from "@/lib/marketing/packages";

export type RoiInputs = {
  currentTools: number;
  currentMonthlySpend: number;
  monthlyOperatorHours: number;
  operatorHourlyRate: number;
  externalReportingMonthlyCost: number;
  targetPlan: MarketingPlanKey;
  includeAiShield: boolean;
};

export type RoiEstimate = {
  currentAnnualToolSpend: number;
  currentAnnualOperatorCost: number;
  currentAnnualExternalCost: number;
  currentAnnualTotal: number;
  sentinelGridAnnualSubscription: number;
  sentinelGridAnnualOperatorCost: number;
  sentinelGridAnnualTotal: number;
  annualSavings: number;
  savingsPercent: number;
  recoveredHoursPerMonth: number;
  packageName: string;
  assumptions: string[];
};

const DEFAULT_RECOVERY_RATES: Record<MarketingPlanKey, number> = {
  protect: 0.2,
  protect_defend: 0.35,
  protect_defend_comply: 0.45,
};

const AI_SHIELD_OPERATOR_PENALTY = 0.04;

export const defaultRoiInputs: RoiInputs = {
  currentTools: 4,
  currentMonthlySpend: 1850,
  monthlyOperatorHours: 28,
  operatorHourlyRate: 70,
  externalReportingMonthlyCost: 300,
  targetPlan: "protect_defend",
  includeAiShield: false,
};

function clampToNonNegative(value: number) {
  return Number.isFinite(value) ? Math.max(0, value) : 0;
}

export function estimateRoi(inputs: RoiInputs): RoiEstimate {
  const normalizedInputs = {
    currentTools: Math.max(1, Math.round(inputs.currentTools)),
    currentMonthlySpend: clampToNonNegative(inputs.currentMonthlySpend),
    monthlyOperatorHours: clampToNonNegative(inputs.monthlyOperatorHours),
    operatorHourlyRate: clampToNonNegative(inputs.operatorHourlyRate),
    externalReportingMonthlyCost: clampToNonNegative(inputs.externalReportingMonthlyCost),
    targetPlan: inputs.targetPlan,
    includeAiShield: inputs.includeAiShield,
  };

  const plan = getMarketingPlan(normalizedInputs.targetPlan);
  const planMonthly = plan.startingPriceMonthly ?? 0;
  const aiShieldMonthly = normalizedInputs.includeAiShield ? 199 : 0;

  const recoveryRateBase = DEFAULT_RECOVERY_RATES[normalizedInputs.targetPlan];
  const recoveryRate = Math.min(
    0.6,
    recoveryRateBase + (normalizedInputs.includeAiShield ? AI_SHIELD_OPERATOR_PENALTY : 0)
  );

  const recoveredHoursPerMonth = normalizedInputs.monthlyOperatorHours * recoveryRate;
  const remainingHoursPerMonth = Math.max(
    0,
    normalizedInputs.monthlyOperatorHours - recoveredHoursPerMonth
  );

  const currentAnnualToolSpend = normalizedInputs.currentMonthlySpend * 12;
  const currentAnnualOperatorCost =
    normalizedInputs.monthlyOperatorHours * normalizedInputs.operatorHourlyRate * 12;
  const currentAnnualExternalCost = normalizedInputs.externalReportingMonthlyCost * 12;
  const currentAnnualTotal =
    currentAnnualToolSpend + currentAnnualOperatorCost + currentAnnualExternalCost;

  const sentinelGridAnnualSubscription = (planMonthly + aiShieldMonthly) * 12;
  const sentinelGridAnnualOperatorCost =
    remainingHoursPerMonth * normalizedInputs.operatorHourlyRate * 12;
  const sentinelGridAnnualTotal =
    sentinelGridAnnualSubscription + sentinelGridAnnualOperatorCost;

  const annualSavings = currentAnnualTotal - sentinelGridAnnualTotal;
  const savingsPercent =
    currentAnnualTotal > 0 ? (annualSavings / currentAnnualTotal) * 100 : 0;

  const assumptions = [
    `SentinelGrid package modeled: ${plan.name}${normalizedInputs.includeAiShield ? ` + ${aiShieldAddon.name}` : ""}.`,
    "Standard onboarding for the core SMB connector path is assumed to be included.",
    `Operator-time recovery is estimated at ${Math.round(recoveryRate * 100)}% based on the selected package and the current point-tool coordination burden.`,
    "This is a directional sales model, not a contractual quote or a substitute for the pricing-validation interviews.",
  ];

  return {
    currentAnnualToolSpend,
    currentAnnualOperatorCost,
    currentAnnualExternalCost,
    currentAnnualTotal,
    sentinelGridAnnualSubscription,
    sentinelGridAnnualOperatorCost,
    sentinelGridAnnualTotal,
    annualSavings,
    savingsPercent,
    recoveredHoursPerMonth,
    packageName: `${plan.name}${normalizedInputs.includeAiShield ? ` + ${aiShieldAddon.name}` : ""}`,
    assumptions,
  };
}
