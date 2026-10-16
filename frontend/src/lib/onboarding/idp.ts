import type { OnboardingStatus } from "@/lib/api/onboarding";

export type OnboardingIdpProvider =
  | "google_workspace"
  | "microsoft_entra"
  | "okta"
  | "sentinelgrid"
  | "keycloak";

type OnboardingIdpMeta = {
  label: string;
  shortLabel: string;
  stepDescription: string;
  ctaLabel: string;
  authHint: string;
  valuePoints: string[];
  prepPoints: string[];
  recommended?: boolean;
};

const DEFAULT_PROVIDER: OnboardingIdpProvider = "microsoft_entra";

const IDP_META: Record<OnboardingIdpProvider, OnboardingIdpMeta> = {
  microsoft_entra: {
    label: "Microsoft 365 / Entra ID",
    shortLabel: "Microsoft 365 / Entra",
    stepDescription:
      "Connect Microsoft 365 / Entra first to surface risky sign-ins, MFA gaps, and exposed admins.",
    ctaLabel: "Connect Microsoft 365 / Entra",
    authHint:
      "Use this if Microsoft is your primary directory. It is the default fastest path for most SMB rollouts.",
    valuePoints: [
      "Risky sign-ins and MFA coverage",
      "Admin role exposure and privileged access gaps",
      "User and group context for downstream findings",
    ],
    prepPoints: [
      "Have a tenant admin ready to approve the connection",
      "Plan to validate MFA policy gaps after the first sync",
      "Pair this with AWS next to unlock cross-domain first findings",
    ],
    recommended: true,
  },
  google_workspace: {
    label: "Google Workspace",
    shortLabel: "Google Workspace",
    stepDescription:
      "Connect Google Workspace first to surface super admin exposure, MFA gaps, and risky OAuth app posture.",
    ctaLabel: "Connect Google Workspace",
    authHint:
      "Use this if Google Workspace is your primary directory and collaboration stack. This is a first-class SMB path.",
    valuePoints: [
      "Super admin and delegated admin exposure",
      "MFA enrollment gaps and identity hygiene",
      "User context for Google-centric SaaS and alert triage",
    ],
    prepPoints: [
      "Have a Google admin ready to approve the connection",
      "Confirm which admin accounts should be reviewed first",
      "Pair this with AWS next to unlock your first prioritized queue",
    ],
  },
  okta: {
    label: "Okta",
    shortLabel: "Okta",
    stepDescription:
      "Connect Okta to review admin roles, app assignments, and identity posture before findings spread across other systems.",
    ctaLabel: "Connect Okta",
    authHint:
      "Use this if Okta is the front door for your workforce apps and login policy.",
    valuePoints: [
      "Admin role visibility and assignment drift",
      "Application access context for downstream incidents",
      "Identity posture for SaaS-heavy environments",
    ],
    prepPoints: [
      "Have your Okta domain and API credentials available",
      "Identify the core app groups you want reviewed first",
      "Plan to pair Okta with AWS or endpoint coverage next",
    ],
  },
  sentinelgrid: {
    label: "SentinelGrid Identity",
    shortLabel: "SentinelGrid Identity",
    stepDescription:
      "Use SentinelGrid Identity if you want SentinelGrid-hosted SSO with MFA and federated login built in.",
    ctaLabel: "Use SentinelGrid Identity",
    authHint:
      "Choose this when you want SentinelGrid to host the identity layer instead of connecting an external directory first.",
    valuePoints: [
      "Hosted SSO and MFA foundation",
      "A single control plane for new tenants",
      "A simpler path for smaller environments without a mature IdP",
    ],
    prepPoints: [
      "Confirm you want SentinelGrid-hosted identity as the system of record",
      "Invite your first admins after the wizard completes",
      "Connect AWS next to unlock posture and incident workflows",
    ],
  },
  keycloak: {
    label: "Keycloak",
    shortLabel: "Keycloak",
    stepDescription:
      "Connect Keycloak to bring self-hosted identity events and admin context into the onboarding flow.",
    ctaLabel: "Connect Keycloak",
    authHint:
      "Use this for self-managed identity deployments that still need the same first-week operator workflow.",
    valuePoints: [
      "Realm and identity-admin context",
      "Self-hosted sign-in and access posture",
      "Identity grounding for downstream findings",
    ],
    prepPoints: [
      "Have the Keycloak realm and admin credentials ready",
      "Confirm the realm you want monitored first",
      "Pair the identity connection with cloud or endpoint coverage next",
    ],
  },
};

export function normalizeOnboardingIdpProvider(value?: string | null): OnboardingIdpProvider | null {
  if (!value) return null;
  const token = String(value).trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
  const aliases: Record<string, OnboardingIdpProvider> = {
    google: "google_workspace",
    google_workspace: "google_workspace",
    googleworkspace: "google_workspace",
    g_suite: "google_workspace",
    gsuite: "google_workspace",
    microsoft: "microsoft_entra",
    microsoft_entra: "microsoft_entra",
    microsoft_365: "microsoft_entra",
    office_365: "microsoft_entra",
    azure_ad: "microsoft_entra",
    azuread: "microsoft_entra",
    entra: "microsoft_entra",
    okta: "okta",
    sentinelgrid: "sentinelgrid",
    keycloak: "keycloak",
  };
  return aliases[token] || null;
}

export function getOnboardingIdpMeta(provider?: string | null): OnboardingIdpMeta {
  const normalized = normalizeOnboardingIdpProvider(provider) || DEFAULT_PROVIDER;
  return IDP_META[normalized];
}

export function getPreferredOnboardingIdp(
  status?: Pick<OnboardingStatus, "idp_provider" | "services_selected"> | null
): OnboardingIdpProvider {
  return (
    normalizeOnboardingIdpProvider(status?.idp_provider) ||
    normalizeOnboardingIdpProvider(status?.services_selected?.idpProvider) ||
    DEFAULT_PROVIDER
  );
}
