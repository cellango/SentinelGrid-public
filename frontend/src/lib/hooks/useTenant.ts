/**
 * Lightweight tenant hook for client components.
 * Reads tenant_id and incident management mode from localStorage.
 */

'use client';

import { useEffect, useState } from 'react';
import {
  getEffectiveTenantIdFromStorage,
  PARTNER_ACTIVE_TENANT_CONTEXT_KEY,
  PARTNER_HOME_TENANT_ID_KEY,
  PARTNER_TENANT_CONTEXT_EVENT,
} from '@/lib/partner/tenantContext';

export interface TenantInfo {
  id: string | null;
  incident_management_mode?: string | null;
}

const DEMO_TENANT_ID = 'b210c499-ea35-4e15-8b93-cd2446361d27';

export function useTenant(): { tenant: TenantInfo | null; loading: boolean } {
  const [tenant, setTenant] = useState<TenantInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const syncTenant = () => {
      const stored = getEffectiveTenantIdFromStorage();
      const mode = typeof window !== 'undefined' ? localStorage.getItem('incident_management_mode') : null;
      // Default demo tenant to customer-managed so approvals/clone UX works there
      const resolvedMode = mode || (stored === DEMO_TENANT_ID ? 'customer_managed' : null);
      setTenant({ id: stored, incident_management_mode: resolvedMode });
      setLoading(false);
    };

    const handleStorage = (event: StorageEvent) => {
      if (
        !event.key ||
        event.key === 'tenant_id' ||
        event.key === PARTNER_ACTIVE_TENANT_CONTEXT_KEY ||
        event.key === PARTNER_HOME_TENANT_ID_KEY
      ) {
        syncTenant();
      }
    };

    syncTenant();
    window.addEventListener('storage', handleStorage);
    window.addEventListener(PARTNER_TENANT_CONTEXT_EVENT, syncTenant as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorage);
      window.removeEventListener(PARTNER_TENANT_CONTEXT_EVENT, syncTenant as EventListener);
    };
  }, []);

  return { tenant, loading };
}
