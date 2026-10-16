/**
 * Authentication API client
 * Handles all authentication operations with IAM Agent
 * No Keycloak redirect - all operations via API
 */

import {
  clearAuthMetadata,
  persistAuthMetadata,
  setInMemoryAccessToken,
} from '@/lib/auth/session';
import { SESSION_AUTH_MARKER } from '@/lib/auth/sessionContract';

const PUBLIC_AUTH_BASE_URL =
  typeof window !== 'undefined'
    ? ''
    : (process.env.NEXT_PUBLIC_IAM_AGENT_URL || 'http://localhost:8005');

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  token_type?: string;
  user: {
    id: string;
    email: string;
    tenant_id: string;
    roles: string[];
    plan_tier?: string;
  };
  realm?: string;
  session?: {
    authenticated: true;
    transport: 'cookie';
  };
  signup_completed?: boolean; // Whether the user has completed all signup wizard steps
  password_reset_required?: boolean; // Whether password reset is required
}

export interface SignupRequest {
  company_name: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  employee_count: number;
  compliance_required?: boolean;
  pricing_tier?: string;
}

export interface SignupResponse {
  success: boolean;
  tenant_id: string;
  realm: string;
  user_id: string;
  message: string;
}

export interface UserInfo {
  id: string;
  email: string;
  tenant_id: string;
  roles: string[];
  realm: string;
  plan_tier?: string;
}

function persistLoginState(data: LoginResponse) {
  setInMemoryAccessToken(SESSION_AUTH_MARKER);
  persistAuthMetadata({
    user: data.user,
    realm: data.realm,
  });

  sessionStorage.removeItem('auth_message');
}

/**
 * Login user with email and password
 */
export async function login(
  email: string,
  password: string,
  rememberMe: boolean = false
): Promise<LoginResponse> {
  // Use Next.js API route which sets cookie server-side
  // This eliminates timing issues with client-side cookie setting
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // Important: include cookies in request/response
    body: JSON.stringify({
      email,
      password,
      remember_me: rememberMe,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));

    // Check if password reset is required
    if (response.status === 403 && (error.detail === 'password_reset_required' || response.headers.get('X-Password-Reset-Required') === 'true')) {
      const resetError: any = new Error('password_reset_required');
      resetError.password_reset_required = true;
      resetError.email = email;
      throw resetError;
    }
    if (response.status === 412 && error?.error === 'mfa_required') {
      const mfaErr: any = new Error('mfa_required');
      mfaErr.mfa_required = true;
      mfaErr.risk = error;
      mfaErr.email = email;
      mfaErr.password = password;
      throw mfaErr;
    }
    throw new Error(error.detail || 'Login failed');
  }

  const data: LoginResponse = await response.json();
  persistLoginState(data);

  return data;
}

export async function loginMFA(
  email: string,
  password: string,
  otp: string,
  rememberMe: boolean = false
): Promise<LoginResponse> {
  const response = await fetch('/api/auth/login/mfa', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({ email, password, otp, remember_me: rememberMe }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'MFA login failed' }));
    throw new Error(error.detail || 'MFA login failed');
  }

  const data: LoginResponse = await response.json();
  persistLoginState(data);
  return data;
}

/**
 * Signup new customer
 */
export async function signup(request: SignupRequest): Promise<SignupResponse> {
  const response = await fetch(`${PUBLIC_AUTH_BASE_URL}/api/v1/auth/signup`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    let errorData: any;
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: `Signup failed with status ${response.status}` };
    }
    
    // Log the error for debugging
    console.error('Signup API error:', {
      status: response.status,
      statusText: response.statusText,
      errorData: JSON.stringify(errorData, null, 2)
    });
    
    // Handle FastAPI validation errors (422) - detail is an array of error objects
    if (response.status === 422) {
      if (Array.isArray(errorData.detail)) {
        const errorMessages = errorData.detail.map((err: any) => {
          const field = err.loc && Array.isArray(err.loc) 
            ? err.loc.slice(1).join('.') // Skip 'body' from loc array
            : 'field';
          const message = err.msg || err.message || 'Validation error';
          // Make field names more user-friendly
          const friendlyField = field.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
          return `${friendlyField}: ${message}`;
        }).join('; ');
        throw new Error(errorMessages || 'Validation failed');
      } else if (typeof errorData.detail === 'string') {
        throw new Error(errorData.detail);
      } else if (errorData.detail && typeof errorData.detail === 'object') {
        // Try to extract meaningful message from object
        const detailObj = errorData.detail;
        if (detailObj.message) {
          throw new Error(detailObj.message);
        } else if (detailObj.msg) {
          throw new Error(detailObj.msg);
        } else {
          // Last resort: stringify but make it readable
          const keys = Object.keys(detailObj);
          if (keys.length > 0) {
            const messages = keys.map(key => {
              const value = detailObj[key];
              return `${key}: ${typeof value === 'string' ? value : JSON.stringify(value)}`;
            }).join('; ');
            throw new Error(messages);
          }
          throw new Error('Validation failed. Please check your input.');
        }
      }
      throw new Error('Validation failed. Please check your input.');
    }
    
    // Handle other error formats
    if (typeof errorData.detail === 'string') {
      throw new Error(errorData.detail);
    }
    
    if (Array.isArray(errorData.detail)) {
      throw new Error(errorData.detail.map((e: any) => {
        if (typeof e === 'string') return e;
        return e.msg || e.message || JSON.stringify(e);
      }).join('; '));
    }
    
    // Fallback error message
    const errorMessage = errorData.detail || errorData.message || `Signup failed (${response.status})`;
    throw new Error(typeof errorMessage === 'string' ? errorMessage : JSON.stringify(errorMessage));
  }

  return await response.json();
}

/**
 * Logout user and invalidate session
 */
export async function logout(refreshToken?: string): Promise<void> {
  try {
    await fetch('/api/auth/logout', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
    });
  } catch (error) {
    // Don't fail logout even if API call fails
    console.error('Logout API call failed:', error);
  }

  clearAuthMetadata();
  sessionStorage.clear();
}

/**
 * Refresh access token
 */
export async function refreshToken(refreshToken?: string): Promise<LoginResponse> {
  const rememberMe =
    typeof document !== 'undefined' &&
    document.cookie.split(';').some((cookie) => cookie.trim() === 'auth_session_persistence=persistent');
  const response = await fetch('/api/auth/refresh', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      ...(refreshToken ? { refresh_token: refreshToken } : {}),
      ...(rememberMe ? { remember_me: true } : {}),
    }),
  });

  if (!response.ok) {
    throw new Error('Token refresh failed');
  }

  const data: LoginResponse = await response.json();

  persistLoginState(data);
  return data;
}

/**
 * Get current user info from token
 */
export async function getCurrentUser(): Promise<UserInfo> {
  const response = await fetch('/api/auth/me', {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error('Failed to get user info');
  }

  const data: UserInfo = await response.json();
  persistAuthMetadata({
    user: {
      id: data.id,
      email: data.email,
      tenant_id: data.tenant_id,
      roles: data.roles,
      plan_tier: data.plan_tier,
    },
    realm: data.realm,
  });
  return data;
}
