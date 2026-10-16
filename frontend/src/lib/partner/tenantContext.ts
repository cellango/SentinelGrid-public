'use client';

import { useCallback, useEffect, useState } from 'react';
import type { PartnerDeliveryMode } from '@/lib/partner/workflows';

export const PARTNER_ACTIVE_TENANT_CONTEXT_KEY = 'partner_active_tenant_context';
export const PARTNER_HOME_TENANT_ID_KEY = 'partner_home_tenant_id';
export const PARTNER_TENANT_CONTEXT_EVENT = 'sentinelgrid:partner-tenant-context-change';

export interface PartnerTenantContext {
  tenantId: string;
  tenantName: string;
  deliveryMode: PartnerDeliveryMode;
  plan: string;
  approvalMode: string;
  enteredAt: string;
}

export interface PartnerTenantContextInput {
  tenantId: string;
  tenantName: string;
  deliveryMode: PartnerDeliveryMode;
  plan: string;
  approvalMode: string;
}

export interface PartnerTenantState {
  effectiveTenantId: string | null;
  homeTenantId: string | null;
  activeTenant: PartnerTenantContext | null;
  isInPartnerTenantContext: boolean;
}

function dispatchPartnerTenantContextChange() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(PARTNER_TENANT_CONTEXT_EVENT));
}

function readActivePartnerTenantContext(): PartnerTenantContext | null {
  if (typeof window === 'undefined') return null;

  const raw = localStorage.getItem(PARTNER_ACTIVE_TENANT_CONTEXT_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as PartnerTenantContext;
    if (!parsed?.tenantId || !parsed?.tenantName) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function getPartnerTenantStateFromStorage(): PartnerTenantState {
  if (typeof window === 'undefined') {
    return {
      effectiveTenantId: null,
      homeTenantId: null,
      activeTenant: null,
      isInPartnerTenantContext: false,
    };
  }

  const activeTenant = readActivePartnerTenantContext();
  const homeTenantId = localStorage.getItem(PARTNER_HOME_TENANT_ID_KEY);
  const currentTenantId = localStorage.getItem('tenant_id');

  return {
    effectiveTenantId: activeTenant?.tenantId || currentTenantId,
    homeTenantId,
    activeTenant,
    isInPartnerTenantContext: Boolean(activeTenant?.tenantId),
  };
}

export function getEffectiveTenantIdFromStorage(): string | null {
  return getPartnerTenantStateFromStorage().effectiveTenantId;
}

export function resetPartnerTenantContextStorage() {
  if (typeof window === 'undefined') return;

  localStorage.removeItem(PARTNER_ACTIVE_TENANT_CONTEXT_KEY);
  localStorage.removeItem(PARTNER_HOME_TENANT_ID_KEY);
  dispatchPartnerTenantContextChange();
}

export function enterPartnerTenantContext(nextTenant: PartnerTenantContextInput) {
  if (typeof window === 'undefined') return;

  const existingState = getPartnerTenantStateFromStorage();
  const currentTenantId = localStorage.getItem('tenant_id');

  if (!existingState.isInPartnerTenantContext && currentTenantId && currentTenantId !== nextTenant.tenantId) {
    localStorage.setItem(PARTNER_HOME_TENANT_ID_KEY, currentTenantId);
  } else if (!existingState.homeTenantId && currentTenantId) {
    localStorage.setItem(PARTNER_HOME_TENANT_ID_KEY, currentTenantId);
  }

  const context: PartnerTenantContext = {
    ...nextTenant,
    enteredAt: new Date().toISOString(),
  };

  localStorage.setItem(PARTNER_ACTIVE_TENANT_CONTEXT_KEY, JSON.stringify(context));
  localStorage.setItem('tenant_id', nextTenant.tenantId);
  dispatchPartnerTenantContextChange();
}

export function clearPartnerTenantContext() {
  if (typeof window === 'undefined') return;

  const homeTenantId = localStorage.getItem(PARTNER_HOME_TENANT_ID_KEY);

  localStorage.removeItem(PARTNER_ACTIVE_TENANT_CONTEXT_KEY);

  if (homeTenantId) {
    localStorage.setItem('tenant_id', homeTenantId);
  }

  localStorage.removeItem(PARTNER_HOME_TENANT_ID_KEY);
  dispatchPartnerTenantContextChange();
}

export function usePartnerTenantContext() {
  const [state, setState] = useState<PartnerTenantState>(() => getPartnerTenantStateFromStorage());

  useEffect(() => {
    const syncState = () => setState(getPartnerTenantStateFromStorage());
    const handleStorage = (event: StorageEvent) => {
      if (
        !event.key ||
        event.key === 'tenant_id' ||
        event.key === PARTNER_ACTIVE_TENANT_CONTEXT_KEY ||
        event.key === PARTNER_HOME_TENANT_ID_KEY
      ) {
        syncState();
      }
    };

    window.addEventListener('storage', handleStorage);
    window.addEventListener(PARTNER_TENANT_CONTEXT_EVENT, syncState as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener(PARTNER_TENANT_CONTEXT_EVENT, syncState as EventListener);
    };
  }, []);

  const activateTenant = useCallback((nextTenant: PartnerTenantContextInput) => {
    enterPartnerTenantContext(nextTenant);
    setState(getPartnerTenantStateFromStorage());
  }, []);

  const exitTenant = useCallback(() => {
    clearPartnerTenantContext();
    setState(getPartnerTenantStateFromStorage());
  }, []);

  return {
    ...state,
    enterTenantContext: activateTenant,
    clearTenantContext: exitTenant,
  };
}
