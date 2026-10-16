export type LaunchWorkflowStepId =
  | "identity"
  | "cloud"
  | "endpoint"
  | "queue"
  | "action";

export type LaunchWorkflowStep = {
  id: LaunchWorkflowStepId;
  stepLabel: string;
  badgeLabel: string;
  title: string;
  description: string;
};

export const launchWorkflowSteps: LaunchWorkflowStep[] = [
  {
    id: "identity",
    stepLabel: "Step 1",
    badgeLabel: "Connect identity",
    title: "Connect identity",
    description:
      "Start with the launch-safe identity path so risky sign-ins, stale MFA, and access hygiene have a real tenant anchor.",
  },
  {
    id: "cloud",
    stepLabel: "Step 2",
    badgeLabel: "Connect cloud",
    title: "Connect cloud",
    description:
      "Bring AWS or Azure posture findings into the same operating plane instead of another admin console.",
  },
  {
    id: "endpoint",
    stepLabel: "Step 3",
    badgeLabel: "Add endpoint coverage",
    title: "Add endpoint coverage",
    description:
      "Add qualified SentinelGuard coverage when endpoint scope is part of the rollout so device state stays in the same queue.",
  },
  {
    id: "queue",
    stepLabel: "Step 4",
    badgeLabel: "See prioritized queue",
    title: "See one prioritized queue",
    description:
      "Review one cross-domain record that ties identity, cloud, endpoint, and optional AI signals into a single operator view.",
  },
  {
    id: "action",
    stepLabel: "Step 5",
    badgeLabel: "Take guided action",
    title: "Take one guided action",
    description:
      "Use a guided action pack with ownership, ticket handoff, and evidence already attached to the same record.",
  },
];

export const launchWorkflowBadgeLabels = launchWorkflowSteps.map(
  (step) => step.badgeLabel
);
