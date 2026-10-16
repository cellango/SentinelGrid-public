/**
 * React Query hooks for Compliance reporting
 */

import { useQuery } from '@tanstack/react-query';
import {
  complianceApi,
  type ComplianceReport,
  type AuditTrailResponse,
  type OrphanedEntitlementsResponse,
} from '../api/compliance';

// Query keys
export const complianceKeys = {
  all: ['compliance'] as const,
  report: (tenantId: string) => [...complianceKeys.all, 'report', tenantId] as const,
  auditTrail: (filters?: Record<string, any>) => [...complianceKeys.all, 'audit-trail', filters] as const,
  orphaned: (tenantId: string) => [...complianceKeys.all, 'orphaned', tenantId] as const,
};

/**
 * Hook to fetch compliance report
 */
export function useComplianceReport(tenantId: string) {
  return useQuery({
    queryKey: complianceKeys.report(tenantId),
    queryFn: () => complianceApi.getReport(tenantId),
    enabled: !!tenantId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch audit trail
 */
export function useAuditTrail(params: {
  tenant_id: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: complianceKeys.auditTrail(params),
    queryFn: () => complianceApi.getAuditTrail(params),
    enabled: !!params.tenant_id,
  });
}

/**
 * Hook to fetch orphaned entitlements
 */
export function useOrphanedEntitlements(tenantId: string) {
  return useQuery({
    queryKey: complianceKeys.orphaned(tenantId),
    queryFn: () => complianceApi.getOrphanedEntitlements(tenantId),
    enabled: !!tenantId,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

