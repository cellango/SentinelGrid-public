'use client';

/**
 * Auth Provider
 * Manages authentication state and Keycloak token
 */

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { clearAuthMetadata } from '@/lib/auth/session';
import { SESSION_AUTH_MARKER } from '@/lib/auth/sessionContract';
import {
  getEffectiveTenantIdFromStorage,
  PARTNER_ACTIVE_TENANT_CONTEXT_KEY,
  PARTNER_HOME_TENANT_ID_KEY,
  PARTNER_TENANT_CONTEXT_EVENT,
  resetPartnerTenantContextStorage,
} from '@/lib/partner/tenantContext';

interface AuthContextType {
  isAuthenticated: boolean;
  hydrated: boolean;
  token: string | null;
  tenantId: string | null;
  planTier: string | null;
  user: {
    id: string;
    email: string;
    roles: string[];
    plan_tier?: string;
  } | null;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<any>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  setPlanTierOverride: (tier: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState<string | null>(null);
  const [user, setUser] = useState<AuthContextType['user'] | null>(null);
  const [planTier, setPlanTier] = useState<string | null>(null);
  const setPlanTierOverride = (tier: string | null) => {
    if (tier) {
      localStorage.setItem('plan_tier_override', tier);
      setPlanTier(tier);
    } else {
      localStorage.removeItem('plan_tier_override');
      const stored = localStorage.getItem('plan_tier');
      setPlanTier(stored);
    }
  };

  const applyAuthenticatedState = ({
    nextTenantId,
    nextUser,
  }: {
    nextTenantId: string;
    nextUser: NonNullable<AuthContextType['user']>;
  }) => {
    const effectiveTenantId = getEffectiveTenantIdFromStorage() || nextTenantId;
    const effectivePlanTier =
      localStorage.getItem('plan_tier_override') || nextUser.plan_tier || localStorage.getItem('plan_tier');

    setToken(SESSION_AUTH_MARKER);
    setTenantId(effectiveTenantId);
    setUser(nextUser);
    setPlanTier(effectivePlanTier || null);
    setIsAuthenticated(true);
  };

  useEffect(() => {
    let cancelled = false;

    const storedPlanTier = localStorage.getItem('plan_tier');
    const planTierOverride = localStorage.getItem('plan_tier_override');

    const hydrateSession = async () => {
      setPlanTier(planTierOverride || storedPlanTier || null);

      try {
        const { refreshToken: refreshTokenAPI } = await import('@/lib/api/auth');
        const response = await refreshTokenAPI();
        if (cancelled) return;

        applyAuthenticatedState({
          nextTenantId: response.user.tenant_id,
          nextUser: {
            id: response.user.id,
            email: response.user.email,
            roles: response.user.roles,
            plan_tier: response.user.plan_tier,
          },
        });
      } catch {
        if (cancelled) return;
        clearAuthMetadata();
        resetPartnerTenantContextStorage();
        setToken(null);
        setTenantId(null);
        setUser(null);
        setPlanTier(planTierOverride || null);
        setIsAuthenticated(false);
      } finally {
        if (!cancelled) {
          setHydrated(true);
        }
      }
    };

    void hydrateSession();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const syncTenantContext = () => {
      setTenantId(getEffectiveTenantIdFromStorage());
    };

    const handleStorage = (event: StorageEvent) => {
      if (
        !event.key ||
        event.key === 'tenant_id' ||
        event.key === PARTNER_ACTIVE_TENANT_CONTEXT_KEY ||
        event.key === PARTNER_HOME_TENANT_ID_KEY
      ) {
        syncTenantContext();
      }
    };

    window.addEventListener('storage', handleStorage);
    window.addEventListener(PARTNER_TENANT_CONTEXT_EVENT, syncTenantContext as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener(PARTNER_TENANT_CONTEXT_EVENT, syncTenantContext as EventListener);
    };
  }, []);

  const login = async (email: string, password: string, rememberMe: boolean = false) => {
    try {
      const { login: loginAPI } = await import('@/lib/api/auth');
      const response = await loginAPI(email, password, rememberMe);
      
      resetPartnerTenantContextStorage();
      applyAuthenticatedState({
        nextTenantId: response.user.tenant_id,
        nextUser: {
          id: response.user.id,
          email: response.user.email,
          roles: response.user.roles,
          plan_tier: response.user.plan_tier,
        },
      });
      
      return response;
    } catch (error: any) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      const { logout: logoutAPI } = await import('@/lib/api/auth');
      await logoutAPI();
    } catch (error) {
      console.error('Logout API error:', error);
    }

    clearAuthMetadata();
    localStorage.removeItem('plan_tier');
    localStorage.removeItem('plan_tier_override');
    resetPartnerTenantContextStorage();
    sessionStorage.clear();
    
    setToken(null);
    setTenantId(null);
    setUser(null);
    setPlanTier(null);
    setIsAuthenticated(false);
  };

  const refreshToken = async () => {
    try {
      const { refreshToken: refreshTokenAPI } = await import('@/lib/api/auth');
      const response = await refreshTokenAPI();

      applyAuthenticatedState({
        nextTenantId: response.user.tenant_id,
        nextUser: {
          id: response.user.id,
          email: response.user.email,
          roles: response.user.roles,
          plan_tier: response.user.plan_tier,
        },
      });
    } catch (error) {
      console.error('Token refresh failed', error);
      await logout();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        hydrated,
        token,
        tenantId,
        planTier,
        user,
        login,
        logout,
        refreshToken,
        setPlanTierOverride,
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
