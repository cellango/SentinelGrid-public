import { apiClient } from './client';

export interface AIFeedbackInput {
  tenantId: string;
  actorUserId?: string | null;
  actorEmail?: string | null;
  actorRoles?: string[];
  action: string;
  resourceType: string;
  resourceId: string;
  resourceName?: string | null;
  metadata?: Record<string, unknown>;
  success?: boolean;
}

function resolveRealmName(): string {
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_KEYCLOAK_REALM || 'sentinelgrid';
  }

  return (
    window.localStorage.getItem('realm') ||
    process.env.NEXT_PUBLIC_KEYCLOAK_REALM ||
    'sentinelgrid'
  );
}

export async function recordAIFeedback(input: AIFeedbackInput): Promise<void> {
  await apiClient.post('/audit/ai-activity', {
    tenant_id: input.tenantId,
    realm_name: resolveRealmName(),
    action: input.action,
    action_category: 'ai_feedback',
    actor_user_id: input.actorUserId || undefined,
    actor_email: input.actorEmail || undefined,
    actor_roles: input.actorRoles?.length ? input.actorRoles : undefined,
    resource_type: input.resourceType,
    resource_id: input.resourceId,
    resource_name: input.resourceName || undefined,
    success: input.success ?? true,
    metadata: input.metadata || undefined,
  });
}
