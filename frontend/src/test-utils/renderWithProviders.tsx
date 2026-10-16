import { render, type RenderOptions } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import type { ReactElement, ReactNode } from 'react';

import { createTestQueryClient } from './queryClient';

type AuthUser = {
  id: string;
  email: string;
  roles: string[];
  plan_tier?: string;
};

type AuthProviderValue = {
  isAuthenticated: boolean;
  hydrated: boolean;
  token: string | null;
  tenantId: string | null;
  planTier: string | null;
  user: AuthUser | null;
  login: jest.Mock<Promise<unknown>, [string, string, boolean?]>;
  logout: jest.Mock<Promise<void>, []>;
  refreshToken: jest.Mock<Promise<void>, []>;
  setPlanTierOverride: jest.Mock<void, [string | null]>;
};

type PartnerTenantContextValue = {
  effectiveTenantId: string | null;
  homeTenantId: string | null;
  activeTenant: null;
  isInPartnerTenantContext: boolean;
  enterTenantContext: jest.Mock<void, [unknown]>;
  clearTenantContext: jest.Mock<void, []>;
};

type ProviderOptions = RenderOptions & {
  queryClient?: ReturnType<typeof createTestQueryClient>;
};

export function buildAuthProviderValue(
  overrides: Partial<AuthProviderValue> = {}
): AuthProviderValue {
  return {
    isAuthenticated: false,
    hydrated: true,
    token: 'test-token',
    tenantId: 'test-tenant',
    planTier: 'protect',
    user: {
      id: 'user-1',
      email: 'test@example.com',
      roles: ['SOC_ANALYST'],
      plan_tier: 'protect',
    },
    login: jest.fn(),
    logout: jest.fn().mockResolvedValue(undefined),
    refreshToken: jest.fn().mockResolvedValue(undefined),
    setPlanTierOverride: jest.fn(),
    ...overrides,
  };
}

export function buildPartnerTenantContextValue(
  overrides: Partial<PartnerTenantContextValue> = {}
): PartnerTenantContextValue {
  return {
    effectiveTenantId: 'test-tenant',
    homeTenantId: null,
    activeTenant: null,
    isInPartnerTenantContext: false,
    enterTenantContext: jest.fn(),
    clearTenantContext: jest.fn(),
    ...overrides,
  };
}

export function renderWithProviders(ui: ReactElement, options: ProviderOptions = {}) {
  const queryClient = options.queryClient || createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  return render(ui, { wrapper: Wrapper, ...options });
}
