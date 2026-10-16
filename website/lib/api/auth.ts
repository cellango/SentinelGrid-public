/**
 * Authentication API client
 * Handles all authentication operations with IAM Agent
 * No Keycloak redirect - all operations via API
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_IAM_AGENT_URL ||
  (typeof window !== 'undefined' && window.location.origin.includes('localhost:3443')
    ? 'https://localhost:3443/api'
    : 'http://localhost:8005');

export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user: {
    id: string;
    email: string;
    tenant_id: string;
    roles: string[];
  };
  signup_completed?: boolean; // Whether the user has completed all signup wizard steps
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
}

/**
 * Login user with email and password
 */
export async function login(
  email: string,
  password: string,
  rememberMe: boolean = false
): Promise<LoginResponse> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/auth/login`
    : `${API_BASE_URL}/api/v1/auth/login`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email,
      password,
      remember_me: rememberMe,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  const data: LoginResponse = await response.json();
  
  // Store tokens
  if (rememberMe) {
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
  } else {
    sessionStorage.setItem('access_token', data.access_token);
    sessionStorage.setItem('refresh_token', data.refresh_token);
  }
  
  localStorage.setItem('tenant_id', data.user.tenant_id);
  localStorage.setItem('user', JSON.stringify(data.user));
  
  // Store full login response including signup_completed status
  localStorage.setItem('login_response', JSON.stringify(data));
  
  return data;
}

/**
 * Signup new customer
 */
export async function signup(request: SignupRequest): Promise<SignupResponse> {
  const url = API_BASE_URL.includes('/api')
    ? `${API_BASE_URL}/v1/auth/signup`
    : `${API_BASE_URL}/api/v1/auth/signup`;

  const response = await fetch(url, {
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
export async function logout(refreshToken: string): Promise<void> {
  try {
    const url = API_BASE_URL.includes('/api')
      ? `${API_BASE_URL}/v1/auth/logout`
      : `${API_BASE_URL}/api/v1/auth/logout`;

    await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch (error) {
    // Don't fail logout even if API call fails
    console.error('Logout API call failed:', error);
  }
  
  // Clear local storage
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('tenant_id');
  localStorage.removeItem('user');
  sessionStorage.clear();
}

/**
 * Refresh access token
 */
export async function refreshToken(refreshToken: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    throw new Error('Token refresh failed');
  }

  const data: LoginResponse = await response.json();
  
  // Update stored tokens
  localStorage.setItem('access_token', data.access_token);
  if (data.refresh_token) {
    localStorage.setItem('refresh_token', data.refresh_token);
  }
  
  return data;
}

/**
 * Get current user info from token
 */
export async function getCurrentUser(accessToken: string): Promise<UserInfo> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    throw new Error('Failed to get user info');
  }

  return await response.json();
}
