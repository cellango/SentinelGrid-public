import { OnboardingStatus } from '@/lib/api/onboarding';

export type NormalizedStep = {
  id: string;
  done: boolean;
  health?: any;
  tested_at?: string | null;
};

export function isPeopleReady(status: OnboardingStatus | null): boolean {
  if (!status) return true;
  return status.access_profile_ready === true && status.birthright_ready === true;
}

function deriveDoneFromFlags(id: string, status: OnboardingStatus): boolean {
  switch (id) {
    case 'idp':
      return !!(status.step_idp_completed ?? status.idp_connected);
    case 'cloud':
      return !!(status.step_cloud_completed ?? status.cloud_connected);
    case 'endpoint':
      return !!(status.step_endpoint_completed ?? status.endpoint_deployed);
    case 'git':
      return !!(status.step_git_completed ?? status.git_connected);
    case 'appsec':
      return !!status.appsec_connected;
    case 'ai':
      return !!status.ai_connected;
    case 'ticketing':
      return !!status.ticketing_connected;
    case 'tenant':
      return isPeopleReady(status);
    default:
      return false;
  }
}

export function normalizeOnboardingSteps(status: OnboardingStatus | null): NormalizedStep[] {
  if (!status) return [];

  const peopleReady = isPeopleReady(status);
  // In demo, show all steps regardless of services_selected flags
  const forceAll =
    status.services_selected == null ||
    (status as any).tenant_slug === 'demo' ||
    (status as any).tenant_name === 'Demo Company';

  const svc = status.services_selected || {};
  const cloudWanted = forceAll || svc.cloud !== false;
  const gitWanted = forceAll || svc.git !== false; // default git ON unless explicitly disabled
  const appsecWanted = forceAll || !!svc.appsec;
  const aiWanted = forceAll || !!svc.aiShield;
  // If socManaged flag is missing, default to showing ticketing so SOC users can wire handoff
  const ticketingWanted = forceAll || svc.socManaged === false || svc.socManaged === undefined;

  const desiredOrder: string[] = [
    'idp',
    ...(cloudWanted ? ['cloud', 'endpoint'] : []),
    ...(gitWanted ? ['git'] : []),
    ...(appsecWanted ? ['appsec'] : []),
    ...(aiWanted ? ['ai'] : []),
    ...(ticketingWanted ? ['ticketing'] : []),
  ];

  const statusStepsMap = new Map<string, NormalizedStep>();
  if (status.steps && status.steps.length > 0) {
    status.steps.forEach((s) => statusStepsMap.set(s.id, { ...s, done: !!s.done }));
  }

  const normalized: NormalizedStep[] = desiredOrder.map((id) => {
    const existing = statusStepsMap.get(id);
    return {
      id,
      done: existing ? !!existing.done : deriveDoneFromFlags(id, status),
      health: existing?.health,
      tested_at: existing?.tested_at,
    };
  });

  // Append any extra steps returned by the backend that are not in desired order
  if (status.steps && status.steps.length > 0) {
    status.steps.forEach((s) => {
      if (!normalized.find((n) => n.id === s.id) && s.id !== 'tenant') {
        normalized.push({ ...s, done: !!s.done });
      }
    });
  }

  // Always include tenant readiness as the final step (done reflects readiness)
  const tenantExisting = statusStepsMap.get('tenant');
  const tenantDone = tenantExisting ? (!!tenantExisting.done && peopleReady) : peopleReady;
  normalized.push({
    id: 'tenant',
    done: tenantDone,
    health: tenantExisting?.health,
    tested_at: tenantExisting?.tested_at,
  });

  return normalized;
}

export function firstIncompleteIndex(steps: NormalizedStep[]): number {
  const idx = steps.findIndex((s) => !s.done);
  return idx >= 0 ? idx : 0;
}
