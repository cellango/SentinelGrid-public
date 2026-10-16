'use client';

import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function AIPoliciesPage() {
  return (
    <LaunchBoundaryNotice
      eyebrow="AI Shield launch boundary"
      title="AI guardrail authoring is not a self-serve launch workflow"
      description="This dedicated AI policy surface stays gated until guardrail storage, approval history, and runtime enforcement are unified behind the main tenant-aware product path."
      bullets={[
        'AI Shield launch support is focused on truthful runtime ingestion into the main queue and governance reporting.',
        'Per-app guardrail authoring and tenant-default AI policy editing are still implementation-led capabilities.',
        'Use AI Governance and the main onboarding flow to review what is connected and what evidence is already arriving.',
      ]}
      primaryAction={{ label: 'Open AI Governance', href: '/dashboard/ai-governance' }}
      secondaryAction={{ label: 'Open Onboarding', href: '/onboarding' }}
    />
  );
}
