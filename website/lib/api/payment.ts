/**
 * Payment API client
 * Handles payment-related API calls
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_IAM_AGENT_URL || 
  (typeof window !== 'undefined' && window.location.origin.includes('localhost:3443') 
    ? 'https://localhost:3443/api'  // Use nginx proxy for HTTPS (already includes /api)
    : 'http://localhost:8005');

export interface CalculatePriceRequest {
  pricing_tier: string;
  employee_count: number;
  billing_period?: 'monthly' | 'yearly';
  cloud_accounts?: number;
  compliance_required?: boolean;
  extra_log_retention_days?: number;
   service_model?: 'managed' | 'byo_soc';
}

export interface PricingInfo {
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
  tenant_id: string;
  pricing_tier: string;
  employee_count: number;
  billing_period: 'monthly' | 'yearly';
  cloud_accounts?: number;
  compliance_required?: boolean;
  extra_log_retention_days?: number;
  service_model?: 'managed' | 'byo_soc';
  ticketing?: 'sentinelgrid' | 'jira' | 'servicenow';
  enable_appsec?: boolean;
  success_url: string;
  cancel_url: string;
}

export interface CheckoutSessionResponse {
  session_id: string | null;
  url: string | null;
  free_tier: boolean;
  dev_mode?: boolean;
  message?: string;
}

async function fetchWithAuth(url: string, options?: RequestInit): Promise<Response> {
  const accessToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
    ...options?.headers,
  };

  const response = await fetch(url, { ...options, headers });

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

export async function handlePaymentSuccess(sessionId: string, tenantId: string): Promise<{ success: boolean; message: string }> {
  const url = API_BASE_URL.includes('/api') 
    ? `${API_BASE_URL}/v1/payment/success`
    : `${API_BASE_URL}/api/v1/payment/success`;
  const response = await fetchWithAuth(url, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, tenant_id: tenantId }),
  });
  return response.json();
}
