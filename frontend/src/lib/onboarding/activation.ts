import type { OnboardingStatus } from "@/lib/api/onboarding";
import { getOnboardingIdpMeta, getPreferredOnboardingIdp } from "./idp";
import { firstIncompleteIndex, isPeopleReady, normalizeOnboardingSteps } from "./steps";

type StepMeta = {
  label: string;
  description: string;
  ctaLabel: string;
  recommended?: boolean;
};

const STEP_META: Record<string, StepMeta> = {
  cloud: {
    label: "Cloud",
    description:
      "Connect AWS next to pull posture findings, audit logs, and cloud exposure into one queue.",
    ctaLabel: "Connect AWS",
    recommended: true,
  },
  endpoint: {
    label: "Endpoint",
    description:
      "Deploy endpoint coverage so SentinelGrid can validate detections and drive response playbooks.",
    ctaLabel: "Roll out endpoint coverage",
  },
  git: {
    label: "Git",
    description:
      "Add Git context so findings can link directly to repos, code owners, and remediation workflows.",
    ctaLabel: "Connect Git",
  },
  appsec: {
    label: "AppSec",
    description:
      "Bring application security findings into the same queue as cloud and identity risk.",
    ctaLabel: "Connect AppSec",
  },
  ai: {
    label: "AI Shield",
    description:
      "Route AI runtime telemetry into the same operator workflow and policy view.",
    ctaLabel: "Connect AI Shield",
  },
  ticketing: {
    label: "Ticketing",
    description:
      "Define the ticketing handoff, ownership model, and optional Slack notifications so incidents land in a real operating workflow.",
    ctaLabel: "Connect ticketing",
  },
  tenant: {
    label: "Tenant readiness",
    description:
      "Finish default access and birthright readiness so the tenant is fully usable after onboarding.",
    ctaLabel: "Finish tenant setup",
  },
};

export type OnboardingActivationItem = {
  id: string;
  label: string;
  description: string;
  done: boolean;
  href: string;
  ctaLabel: string;
  recommended: boolean;
};

export type OnboardingActivationSummary = {
  totalSteps: number;
  completedSteps: number;
  progressPct: number;
  nextStepId: string | null;
  nextStepLabel: string | null;
  nextStepDescription: string | null;
  targetHref: string;
  items: OnboardingActivationItem[];
  pendingItems: OnboardingActivationItem[];
  coreConnectorsReady: boolean;
  peopleReady: boolean;
  overallComplete: boolean;
};

function getStepMeta(stepId: string, status?: OnboardingStatus | null): StepMeta {
  if (stepId === "idp") {
    const idpMeta = getOnboardingIdpMeta(getPreferredOnboardingIdp(status));
    return {
      label: "Identity",
      description: idpMeta.stepDescription,
      ctaLabel: idpMeta.ctaLabel,
      recommended: idpMeta.recommended === true,
    };
  }
  return (
    STEP_META[stepId] || {
      label: stepId.replace(/_/g, " "),
      description: "Complete this setup step to unlock the next part of the platform.",
      ctaLabel: "Continue setup",
    }
  );
}

export function buildOnboardingActivationSummary(
  status: OnboardingStatus | null
): OnboardingActivationSummary {
  const normalizedSteps = normalizeOnboardingSteps(status);
  const peopleReady = isPeopleReady(status);
  const overallComplete = (status?.overall_complete ?? status?.onboarding_completed) === true;
  const totalSteps = normalizedSteps.length;
  const completedSteps = normalizedSteps.filter((step) => step.done).length;
  const progressPct = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
  const nextStepIndex = totalSteps > 0 ? firstIncompleteIndex(normalizedSteps) : 0;
  const nextStep = normalizedSteps[nextStepIndex];

  const items: OnboardingActivationItem[] = normalizedSteps.map((step, index) => {
    const meta = getStepMeta(step.id, status);
    return {
      id: step.id,
      label: meta.label,
      description: meta.description,
      done: step.done,
      href: `/onboarding?step=${index + 1}`,
      ctaLabel: meta.ctaLabel,
      recommended: meta.recommended === true,
    };
  });

  const pendingItems = items.filter((item) => !item.done);
  const coreConnectorsReady = status?.idp_connected === true && status?.cloud_connected === true;

  return {
    totalSteps,
    completedSteps,
    progressPct,
    nextStepId: nextStep?.id || null,
    nextStepLabel: nextStep ? getStepMeta(nextStep.id, status).label : null,
    nextStepDescription: nextStep ? getStepMeta(nextStep.id, status).description : null,
    targetHref: nextStep ? `/onboarding?step=${nextStepIndex + 1}` : "/onboarding",
    items,
    pendingItems,
    coreConnectorsReady,
    peopleReady,
    overallComplete,
  };
}
