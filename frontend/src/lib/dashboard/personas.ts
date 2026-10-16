export type DashboardPersonaId = 'soc_analyst' | 'executive' | 'it_admin' | 'developer';

export type DashboardPersona = {
  id: DashboardPersonaId;
  label: string;
  description: string;
  landingHref: string;
  workflow: 'Detect' | 'Respond' | 'Govern';
  mobileLandingHref?: string;
};

export const DASHBOARD_PERSONAS: Record<DashboardPersonaId, DashboardPersona> = {
  soc_analyst: {
    id: 'soc_analyst',
    label: 'SOC Analyst',
    description: 'Prioritize active incidents, alerts, and the fastest path to containment.',
    landingHref: '/dashboard/incidents',
    mobileLandingHref: '/dashboard/now',
    workflow: 'Detect',
  },
  executive: {
    id: 'executive',
    label: 'Executive / CISO',
    description: 'Start with posture, reporting, and the highest-risk cross-domain trends.',
    landingHref: '/dashboard/posture',
    mobileLandingHref: '/dashboard/now',
    workflow: 'Govern',
  },
  it_admin: {
    id: 'it_admin',
    label: 'IT Admin',
    description: 'Open workforce access, device trust, and identity operations first.',
    landingHref: '/dashboard/iam/people',
    mobileLandingHref: '/dashboard/now',
    workflow: 'Respond',
  },
  developer: {
    id: 'developer',
    label: 'Developer / AppSec',
    description: 'Jump into detection coverage and app-linked findings before they become incidents.',
    landingHref: '/dashboard/siem/detection-rules',
    mobileLandingHref: '/dashboard/now',
    workflow: 'Detect',
  },
};

const PERSONA_ROLE_MATCHERS: Record<DashboardPersonaId, RegExp[]> = {
  soc_analyst: [
    /\bsoc_analyst\b/i,
    /\bsoc_manager\b/i,
    /\bsecurity_analyst\b/i,
    /\bincident_responder\b/i,
    /\bblue_team\b/i,
  ],
  executive: [
    /\bciso\b/i,
    /\bexecutive\b/i,
    /\bsecurity_officer\b/i,
    /\bboard\b/i,
    /\bview_only\b/i,
    /\bauditor\b/i,
  ],
  it_admin: [
    /\btenant_admin\b/i,
    /\badmin\b/i,
    /\bit_admin\b/i,
    /\biam_admin\b/i,
    /\bhelpdesk\b/i,
    /\bidentity_admin\b/i,
  ],
  developer: [
    /\bdeveloper\b/i,
    /\bengineer\b/i,
    /\bappsec\b/i,
    /\bdevsecops\b/i,
    /\bplatform\b/i,
    /\bsecurity_engineer\b/i,
  ],
};

export const DASHBOARD_PERSONA_STORAGE_KEY = 'sg_dashboard_persona';

export function getMatchingPersonas(roles: string[] | undefined | null): DashboardPersona[] {
  const normalizedRoles = roles || [];
  const matches = Object.entries(PERSONA_ROLE_MATCHERS)
    .filter(([, patterns]) =>
      normalizedRoles.some((role) => patterns.some((pattern) => pattern.test(role)))
    )
    .map(([personaId]) => DASHBOARD_PERSONAS[personaId as DashboardPersonaId]);

  return matches;
}

export function inferDashboardPersona(roles: string[] | undefined | null): DashboardPersona | null {
  const matches = getMatchingPersonas(roles);
  if (matches.length === 1) {
    return matches[0];
  }
  return null;
}

export function getStoredDashboardPersona(): DashboardPersona | null {
  if (typeof window === 'undefined') return null;
  const stored = window.localStorage.getItem(DASHBOARD_PERSONA_STORAGE_KEY);
  if (!stored) return null;
  return DASHBOARD_PERSONAS[stored as DashboardPersonaId] || null;
}

export function setStoredDashboardPersona(personaId: DashboardPersonaId) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(DASHBOARD_PERSONA_STORAGE_KEY, personaId);
}

export function getDashboardLandingHref(options: {
  roles: string[] | undefined | null;
  isMobile: boolean;
}): string | null {
  const persona = getStoredDashboardPersona() || inferDashboardPersona(options.roles);
  if (!persona) {
    return null;
  }
  return options.isMobile ? persona.mobileLandingHref || persona.landingHref : persona.landingHref;
}
