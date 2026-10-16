/**
 * Payment API client
 * Handles payment-related API calls
 */

import type { PlanTier, ServicesSelected } from "@/lib/product/catalog";
import { withSessionAuthorization } from '@/lib/auth/session';

const API_BASE_URL = (() => {
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api`;
  }
  if (process.env.NEXT_PUBLIC_IAM_AGENT_URL) {
    return process.env.NEXT_PUBLIC_IAM_AGENT_URL;
  }
  return 'http://localhost:8005';
})();

export interface CalculatePriceRequest {
  user_count: number;
  compliance_required: boolean;
  plan_tier?: PlanTier;
  billing_period?: 'monthly' | 'yearly';
  services_selected?: ServicesSelected;
}

export interface PricingInfo {
  package_name?: string;
  plan_tier?: PlanTier;
  package_display?: string;
  user_band?: string;
  base_price: number | null;
  addons: Array<{
    name: string;
    amount: number;
    display: string;
  }>;
  subtotal: number | null;
  discount: number;
  total: number | null;
  display: string;
  billing_period?: string;
  requires_sales_contact: boolean;
}

export interface CreateCheckoutSessionRequest {
  lead_id: string;  // Lead ID instead of tenant_id
  provisioning_token: string;
  billing_period: 'monthly' | 'yearly';
  success_url: string;
  cancel_url: string;
  services_selected?: ServicesSelected;
}

export interface CheckoutSessionResponse {
  session_id: string | null;
  url: string | null;
  free_tier: boolean;
  dev_mode?: boolean;
  message?: string;
}

async function fetchWithAuth(url: string, options?: RequestInit): Promise<Response> {
  const headers = withSessionAuthorization({
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> | undefined),
  });

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: `API call failed with status ${response.status}` }));
    throw new Error(errorData.detail || `API call failed with status ${response.status}`);
  }
  return response;
}

export async function calculatePrice(request: CalculatePriceRequest): Promise<PricingInfo> {
  // API_BASE_URL already includes /api if using nginx proxy, so we need to check
  const url = API_BASE_URL.includes('/api') 
    ? `${API_BASE_URL}/v1/payment/calculate`
    : `${API_BASE_URL}/api/v1/payment/calculate`;
  const response = await fetchWithAuth(url, {
    method: 'POST',
    body: JSON.stringify(request),
  });
  return response.json();
}

export async function createCheckoutSession(request: CreateCheckoutSessionRequest): Promise<CheckoutSessionResponse> {
  const url = API_BASE_URL.includes('/api') 
    ? `${API_BASE_URL}/v1/payment/create-checkout-session`
    : `${API_BASE_URL}/api/v1/payment/create-checkout-session`;
  const response = await fetchWithAuth(url, {
    method: 'POST',
    body: JSON.stringify(request),
  });
  return response.json();
}

export interface PaymentSuccessRequest {
  session_id: string;
  lead_id: string;  // Lead ID instead of tenant_id
  provisioning_token: string;
}

export interface PaymentSuccessResponse {
  success: boolean;
  message: string;
  tenant_id?: string;
  customer_id?: string;
  subscription_id?: string;
  email?: string;
  dev_mode?: boolean;
  password_reset_required?: boolean;
  user_verified?: boolean;  // Whether user was verified in Keycloak
}

export async function handlePaymentSuccess(
  sessionId: string,
  leadId: string,
  provisioningToken: string,
  password?: string
): Promise<PaymentSuccessResponse> {
  const url = API_BASE_URL.includes('/api') 
    ? `${API_BASE_URL}/v1/payment/success`
    : `${API_BASE_URL}/api/v1/payment/success`;
  const payload: any = {
    session_id: sessionId,
    lead_id: leadId,
    provisioning_token: provisioningToken,
  };
  // Include password in dev mode only (when session_id starts with "dev_session_")
  if (password && sessionId.startsWith('dev_session_')) {
    payload.password = password;
    console.log('DEV MODE: Including password in payment success request');
  } else {
    console.log('DEV MODE: No password provided or not dev mode');
  }
  const response = await fetchWithAuth(url, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return response.json();
}

export interface CreatePentestCheckoutRequest {
  amount_cents: number;
  currency?: string;
  success_url: string;
  cancel_url: string;
  engagement_meta?: Record<string, any>;
}

export interface PentestCheckoutResponse {
  session_id: string | null;
  url: string | null;
  free_tier?: boolean;
  dev_mode?: boolean;
  message?: string;
}

export async function createPentestCheckoutSession(
  request: CreatePentestCheckoutRequest
): Promise<PentestCheckoutResponse> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/payment/create-pentest-session`
    : `${API_BASE_URL}/api/v1/payment/create-pentest-session`;

  const response = await fetchWithAuth(url, {
    method: 'POST',
    body: JSON.stringify(request),
  });

  return response.json();
}
