import {
  defaultPlanTier,
  isPlanTier,
  planTierOrder,
  type PlanTier,
} from "@/lib/product/catalog";

export type MarketingPlanKey = PlanTier;

export type MarketingPlan = {
  key: MarketingPlanKey;
  name: string;
  shortName: string;
  subtitle: string;
  audience: string;
  startingPriceMonthly: number | null;
  priceLabel: string;
  annualLabel: string;
  badge?: string;
  ctaLabel: string;
  ctaHref: string;
  summary: string;
  included: string[];
  onboarding: string[];
  addOns?: string[];
  comparisonLabel: string;
};

export const marketingPlans: MarketingPlan[] = [
  {
    key: "protect",
    name: "Protect",
    shortName: "Protect",
    subtitle: "Cloud, identity, posture, and baseline detections for lean teams that need visibility now.",
    audience: "Best for teams replacing spreadsheet-driven security checks and one-off point tools.",
    startingPriceMonthly: 299,
    priceLabel: "Starting at $299/mo",
    annualLabel: "or $3,000 billed annually",
    ctaLabel: "Start with Protect",
    ctaHref: "/signup",
    summary: "Immediate coverage for cloud, identity, posture, and baseline security monitoring.",
    included: [
      "Cloud posture and IAM hygiene checks",
      "Baseline detections and response recommendations",
      "Weekly executive-ready reporting",
      "Standard onboarding for core connectors",
      "Email support",
    ],
    onboarding: [
      "AWS or Azure onboarding",
      "Microsoft 365 / Entra or Google Workspace connection",
      "First findings and quick wins in the dashboard",
    ],
    addOns: ["AI Shield", "Extended retention", "Additional connector bundles"],
    comparisonLabel: "Visibility and guided remediation",
  },
  {
    key: "protect_defend",
    name: "Protect + Defend",
    shortName: "Protect + Defend",
    subtitle: "Adds qualified endpoint coverage, response playbooks, and deeper incident workflows.",
    audience: "Best for teams that need a real operator workflow without building or buying a heavyweight SOC stack.",
    startingPriceMonthly: 799,
    priceLabel: "Starting at $799/mo",
    annualLabel: "or $8,000 billed annually",
    badge: "Recommended launch path",
    ctaLabel: "Start with Protect + Defend",
    ctaHref: "/signup",
    summary: "The modern SOC operating layer for teams that need detections, response, and accountability in one place.",
    included: [
      "Everything in Protect",
      "Qualified endpoint coverage and SentinelGuard workflows",
      "Response playbooks and incident coordination",
      "Priority support",
      "Longer default retention and richer analytics",
    ],
    onboarding: [
      "Core connector setup",
      "Endpoint rollout planning",
      "Playbook and response configuration review",
    ],
    addOns: ["AI Shield", "Partner / MSP workflows", "Additional environments"],
    comparisonLabel: "Unified monitoring plus response",
  },
  {
    key: "protect_defend_comply",
    name: "Protect + Defend + Comply",
    shortName: "Protect + Defend + Comply",
    subtitle: "Adds evidence workflows, narrowed compliance reporting, and audit-ready exports.",
    audience: "Best for teams with customer trust pressure, audits, or repeated security reviews.",
    startingPriceMonthly: 1499,
    priceLabel: "Starting at $1,499/mo",
    annualLabel: "or $15,000 billed annually",
    ctaLabel: "Talk to us about Comply",
    ctaHref: "/demo",
    summary: "Security operations plus the reporting and evidence layer needed for trust and compliance motion.",
    included: [
      "Everything in Protect + Defend",
      "Narrowed compliance reporting and evidence workflows",
      "Access reviews and audit-facing exports",
      "Priority onboarding and review sessions",
      "Support for trust and questionnaire workflows",
    ],
    onboarding: [
      "Core connector setup",
      "Compliance scope review",
      "Reporting and evidence configuration",
    ],
    addOns: ["AI Shield", "Long-term archive options", "Expanded trust and review support"],
    comparisonLabel: "Operations plus trust acceleration",
  },
];

export const planKeyOrder: MarketingPlanKey[] = [...planTierOrder];
export const defaultMarketingPlanKey: MarketingPlanKey = defaultPlanTier;

export const aiShieldAddon = {
  name: "AI Shield",
  priceLabel: "Starting at $199/mo",
  availabilityLabel: "Controlled add-on for launch",
  description:
    "Add runtime AI security to a qualified SentinelGrid rollout so launch-supported AI traffic lands in the same queue, response workflow, and trust story.",
  positioning:
    "AI Shield is a controlled SentinelGrid add-on for launch, not a detached console or an unlimited self-serve claim.",
  launchNote:
    "Launch support is currently scoped to the production-real OpenAI path through the SentinelGrid AI Shield edge. Additional provider paths stay gated until they are equally real and supportable.",
  highlights: [
    {
      title: "Same queue",
      description:
        "AI alerts and high-severity AI incidents land in the main SentinelGrid operator queue alongside cloud, identity, endpoint, and posture work.",
    },
    {
      title: "Same response model",
      description:
        "AI-specific response packs, ownership, SLAs, and ticketing use the same incident workflow the rest of the platform already uses.",
    },
    {
      title: "Same trust workflow",
      description:
        "AI activity evidence, policy context, and governance reporting extend the same compliance and customer-review workflow instead of creating a parallel process.",
    },
  ],
  packageFit: [
    {
      planKey: "protect" as MarketingPlanKey,
      label: "Protect + AI Shield",
      description:
        "Use only when the rollout is narrow and the launch-supported AI path is the main requirement.",
    },
    {
      planKey: "protect_defend" as MarketingPlanKey,
      label: "Protect + Defend + AI Shield",
      description:
        "This is the primary launch fit when AI incidents need the same operator handoff, response packs, and escalation path as the rest of the platform.",
    },
    {
      planKey: "protect_defend_comply" as MarketingPlanKey,
      label: "Protect + Defend + Comply + AI Shield",
      description:
        "Add the trust and evidence layer when AI governance and customer-review pressure are part of the buying motion.",
    },
  ],
  ctaHref: "/product/ai-shield",
  ctaLabel: "Review AI Shield launch scope",
};

export const pricingFaqs = [
  {
    question: "What does \"starting at\" mean?",
    answer:
      "It covers standard onboarding for core connectors and the base usage profile for each package. Larger environments, unusual retention, or partner-led deployments may require custom pricing.",
  },
  {
    question: "Do you charge by log volume?",
    answer:
      "No. SentinelGrid does not lead with per-GB log pricing. We use package pricing with fair-use thresholds so smaller teams are not punished for sending the telemetry they need.",
  },
  {
    question: "Is onboarding included?",
    answer:
      "Standard onboarding for core connectors is included. That covers the normal setup path for cloud and identity integrations in the target SMB motion.",
  },
  {
    question: "When do I need to talk to sales?",
    answer:
      "If you need unusual retention, complex multi-environment rollouts, qualified partner / MSP delivery, or a larger compliance scope, we will tailor the package with you.",
  },
];

export function getMarketingPlan(key: MarketingPlanKey): MarketingPlan {
  const plan = marketingPlans.find((item) => item.key === key);
  if (!plan) {
    throw new Error(`Unknown marketing plan: ${key}`);
  }
  return plan;
}

export function getMarketingPlanLabel(key: MarketingPlanKey): string {
  return getMarketingPlan(key).name;
}

export function getMarketingPlanBadge(key: MarketingPlanKey): string | undefined {
  return getMarketingPlan(key).badge;
}

export function isMarketingPlanKey(value: string | null | undefined): value is MarketingPlanKey {
  return isPlanTier(value);
}
