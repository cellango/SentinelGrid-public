'use client';

/**
 * Auth Provider
 * Manages authentication state and Keycloak token
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface AuthContextType {
  isAuthenticated: boolean;
  token: string | null;
  tenantId: string | null;
  user: {
    id: string;
    email: string;
    roles: string[];
  } | null;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<any>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [user, setUser] = useState<AuthContextType['user'] | null>(null);

  // Check for existing token on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('access_token');
    const storedTenantId = localStorage.getItem('tenant_id');
    const storedUser = localStorage.getItem('user');

    if (storedToken && storedTenantId) {
      setToken(storedToken);
      setTenantId(storedTenantId);
      setIsAuthenticated(true);
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch (e) {
          console.error('Failed to parse stored user', e);
        }
      }
    }
  }, []);

  const login = async (email: string, password: string, rememberMe: boolean = false) => {
    try {
      const { login: loginAPI } = await import('@/lib/api/auth');
      const response = await loginAPI(email, password, rememberMe);
      
      // Update state
      setToken(response.access_token);
      setTenantId(response.user.tenant_id);
      setUser({
        id: response.user.id,
        email: response.user.email,
        roles: response.user.roles,
      });
      setIsAuthenticated(true);
      
      return response;
    } catch (error: any) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      const refreshTokenValue = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
      if (refreshTokenValue) {
        const { logout: logoutAPI } = await import('@/lib/api/auth');
        await logoutAPI(refreshTokenValue);
      }
    } catch (error) {
      console.error('Logout API error:', error);
      // Continue with local logout even if API call fails
    }
    
    // Clear local storage
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('tenant_id');
    localStorage.removeItem('user');
    sessionStorage.clear();
    
    setToken(null);
    setTenantId(null);
    setUser(null);
    setIsAuthenticated(false);
  };

  const refreshToken = async () => {
    const refreshTokenValue = localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token');
    if (!refreshTokenValue) {
      logout();
      return;
    }

    try {
      const { refreshToken: refreshTokenAPI } = await import('@/lib/api/auth');
      const response = await refreshTokenAPI(refreshTokenValue);
      
      setToken(response.access_token);
      if (response.refresh_token) {
        localStorage.setItem('refresh_token', response.refresh_token);
      }
      
      // Update user info if available
      if (response.user) {
        setUser({
          id: response.user.id,
          email: response.user.email,
          roles: response.user.roles,
        });
        setTenantId(response.user.tenant_id);
      }
    } catch (error) {
      console.error('Token refresh failed', error);
      logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        token,
        tenantId,
        user,
        login,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

