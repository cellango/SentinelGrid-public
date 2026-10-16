/**
 * API Client Configuration
 * Centralized HTTP client for SentinelGrid APIs
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { clearAuthMetadata, getInMemoryAccessToken } from '@/lib/auth/session';
import { getEffectiveTenantIdFromStorage } from '@/lib/partner/tenantContext';

// Get API base URL - use relative URLs in browser so requests go through Next.js proxy
// This ensures proper CORS handling and authentication
const getBaseURL = () => '/api';

const API_BASE_URL = getBaseURL();
const ENTITLEMENT_AGENT_URL = getBaseURL();
const SOAR_AGENT_URL = getBaseURL();
const TENANT_SERVICE_URL = getBaseURL();
const INGESTION_SERVICE_URL = getBaseURL();
const SIEM_AGENT_URL = getBaseURL();
const EMAIL_INGESTION_SERVICE_URL = getBaseURL();
const ORCHESTRATOR_URL = getBaseURL();
const AUTOMATED_RESPONSE_SERVICE_URL = getBaseURL();
const COMPLIANCE_SERVICE_URL = getBaseURL();

/**
 * Create axios instance with default config
 */
function createApiClient(baseURL: string): AxiosInstance {
  const client = axios.create({
    baseURL,
    headers: {
      'Content-Type': 'application/json',
    },
    withCredentials: true, // allow sending cookies for same-origin API calls
  });

  // Request interceptor to add auth token
  client.interceptors.request.use(
    (config) => {
      const token = typeof window !== 'undefined' ? getInMemoryAccessToken() : null;
      const tenantId = typeof window !== 'undefined' ? getEffectiveTenantIdFromStorage() : null;
      const realm = typeof window !== 'undefined'
        ? (localStorage.getItem('realm') ||
          // derive from email domain if stored
          (localStorage.getItem('user_email') || '').split('@')[1]?.split('.')[0] ||
          'sentinelgrid')
        : 'sentinelgrid';
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      
      if (tenantId) {
        config.headers['X-Tenant-ID'] = tenantId;
      }
      if (realm) {
        config.headers['X-Realm'] = realm;
      }
      
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error.response?.status;
      const detail: string =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.response?.data?.error ||
        '';

      const lowerDetail = typeof detail === 'string' ? detail.toLowerCase() : '';
      const authHeader = error.response?.headers?.['www-authenticate'] || '';
      const authHeaderLower = typeof authHeader === 'string' ? authHeader.toLowerCase() : '';

      const tokenLikelyExpired =
        lowerDetail.includes('token') && (lowerDetail.includes('expired') || lowerDetail.includes('invalid'));
      const authHeaderExpired =
        authHeaderLower.includes('bearer') && (authHeaderLower.includes('expired') || authHeaderLower.includes('invalid'));

      // Treat any 401 as auth failure, and 403 when it smells like token/expiry
      if ((status === 401 || (status === 403 && (tokenLikelyExpired || authHeaderExpired))) && typeof window !== 'undefined') {
        clearAuthMetadata();
        // Persist a friendly message to show on login
        sessionStorage.setItem('auth_message', 'Your session expired. Please sign in again.');
        // Redirect to login
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );

  return client;
}

// Main API client (for API Gateway)
export const apiClient = createApiClient(API_BASE_URL);

// Entitlement Agent client (for governance, entitlements)
export const entitlementClient = createApiClient(ENTITLEMENT_AGENT_URL);

// SOAR Agent client (for playbooks)
export const soarClient = createApiClient(SOAR_AGENT_URL);

// Tenant Service client
export const tenantClient = createApiClient(TENANT_SERVICE_URL);

// Ingestion Service client
export const ingestionClient = createApiClient(INGESTION_SERVICE_URL);

// SIEM Agent client
export const siemClient = createApiClient(SIEM_AGENT_URL);

// Email Ingestion Service client
export const emailIngestionClient = createApiClient(EMAIL_INGESTION_SERVICE_URL);

// Orchestrator client
export const orchestratorClient = createApiClient(ORCHESTRATOR_URL);

// Automated Response Service client
export const automatedResponseClient = createApiClient(AUTOMATED_RESPONSE_SERVICE_URL);

// Compliance Service client
export const complianceClient = createApiClient(COMPLIANCE_SERVICE_URL);

// Helper function for paginated responses
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export default apiClient;
