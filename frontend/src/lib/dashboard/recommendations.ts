import type { Recommendation } from '@/lib/api/dashboard';

type RecommendationAction = Recommendation['actions'][number];

export function getRecommendationActionHref(action: RecommendationAction): string | null {
  if (action.playbook_id) {
    return `/dashboard/playbooks?playbook_id=${encodeURIComponent(action.playbook_id)}`;
  }
  if (action.endpoint) {
    return action.endpoint;
  }
  return null;
}

export function getPrimaryRecommendationAction(
  recommendation: Recommendation
): RecommendationAction | null {
  const actionable = recommendation.actions.filter((action) => getRecommendationActionHref(action));
  return (
    actionable.find((action) => action.type === 'fix_now') ||
    actionable.find((action) => action.type === 'open_ticket') ||
    actionable.find((action) => action.type === 'view_details') ||
    actionable[0] ||
    null
  );
}

export function getRecommendationHref(recommendation: Recommendation): string {
  const action = recommendation.actions.find((item) => getRecommendationActionHref(item));
  if (action) {
    return getRecommendationActionHref(action)!;
  }

  switch ((recommendation.category || '').toLowerCase()) {
    case 'identity':
      return '/dashboard/iam/people';
    case 'cloud':
    case 'cloud_security':
      return '/dashboard/posture';
    case 'endpoint':
      return '/dashboard/endpoint-protection';
    case 'app':
      return '/dashboard/posture';
    case 'ai':
      return '/dashboard/compliance/ai-activity';
    case 'activation':
    case 'collaboration':
      return '/dashboard/welcome';
    default:
      return '/dashboard/incidents';
  }
}

export function formatRecommendationClass(findingClass?: string): string | null {
  if (!findingClass) return null;
  return findingClass.replace(/[._]/g, ' / ');
}
