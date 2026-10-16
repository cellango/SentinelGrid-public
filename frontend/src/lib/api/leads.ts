/**
 * Leads API client
 * Handles lead creation (incomplete signups before payment)
 */

import type { PlanTier, ServicesSelected } from "@/lib/product/catalog";

export type DemoMotion = "standard" | "partner";
export type DemoIdentityProfile =
  | "microsoft_entra"
  | "google_workspace"
  | "okta"
  | "mixed";
export type DemoRolloutScope = "single_environment" | "multi_environment";
export type DemoRetentionProfile = "standard" | "extended_or_archive";
export type DemoAIShieldFit = "none" | "add_on" | "primary";

const API_BASE_URL = (() => {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api`;
  }
  if (process.env.NEXT_PUBLIC_IAM_AGENT_URL) {
    return process.env.NEXT_PUBLIC_IAM_AGENT_URL;
  }
  return 'http://localhost:8005';
})();

export interface CreateLeadRequest {
  email: string;
  company_name: string;
  first_name: string;
  last_name: string;
  password: string;
  user_count: number;
  compliance_required: boolean;
  plan_tier?: PlanTier;
  tenant_slug?: string;
  services_selected?: ServicesSelected;
}

export interface UpdateLeadRequest {
  compliance_required?: boolean;
  plan_tier?: PlanTier;
  tenant_slug?: string;
  services_selected?: ServicesSelected;
}

export interface CreateDemoRequestRequest {
  email: string;
  company_name: string;
  first_name: string;
  last_name: string;
  company_size: string;
  notes?: string;
  plan_tier?: PlanTier;
  source?: string;
  motion?: DemoMotion;
  identity_profile?: DemoIdentityProfile;
  rollout_scope?: DemoRolloutScope;
  retention_profile?: DemoRetentionProfile;
  ai_shield_fit?: DemoAIShieldFit;
}

export interface LeadResponse {
  success: boolean;
  lead_id: string;
  session_token?: string;
  pricing: {
    package_name: string;
    plan_tier?: PlanTier;
    package_display?: string;
    user_band: string;
    base_price: number | null;
    total: number | null;
    display: string;
    requires_sales_contact: boolean;
  };
  message: string;
}

export interface DemoRequestResponse {
  success: boolean;
  lead_id: string;
  message: string;
}

function buildLeadsUrl(path: string): string {
  return API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/leads${path}`
    : `${API_BASE_URL}/api/v1/leads${path}`;
}

export async function createLead(request: CreateLeadRequest): Promise<LeadResponse> {
  const url = buildLeadsUrl('/create');
  if (typeof window !== 'undefined') {
    // Helpful for debugging local env routing issues
    // eslint-disable-next-line no-console
    console.log('📡 createLead -> URL', url);
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `API call failed with status ${response.status}` }));
    throw new Error(errorData.detail || `API call failed with status ${response.status}`);
  }

  return response.json();
}

export async function updateLead(
  leadId: string,
  provisioningToken: string,
  request: UpdateLeadRequest
): Promise<LeadResponse> {
  const url = buildLeadsUrl(`/${leadId}`);

  const response = await fetch(url, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${provisioningToken}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `API call failed with status ${response.status}` }));
    throw new Error(errorData.detail || `API call failed with status ${response.status}`);
  }

  return response.json();
}

export async function createDemoRequest(
  request: CreateDemoRequestRequest
): Promise<DemoRequestResponse> {
  const url = buildLeadsUrl('/demo-request');

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `API call failed with status ${response.status}` }));
    throw new Error(errorData.detail || `API call failed with status ${response.status}`);
  }

  return response.json();
}

export async function getLead(leadId: string, provisioningToken: string): Promise<any> {
  const url = buildLeadsUrl(`/${leadId}`);
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${provisioningToken}`,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `API call failed with status ${response.status}` }));
    throw new Error(errorData.detail || `API call failed with status ${response.status}`);
  }

  return response.json();
}
