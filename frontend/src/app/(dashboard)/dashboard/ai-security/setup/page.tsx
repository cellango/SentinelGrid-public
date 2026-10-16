'use client';

import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function AISetupPage() {
  return (
    <LaunchBoundaryNotice
      eyebrow="AI Shield controlled add-on"
      title="AI Shield setup is implementation-led for launch"
      description="The default launch does not present AI Shield as a broad self-serve console. Use onboarding for the approved provider path and review resulting evidence in the shared queue and governance surfaces."
      bullets={[
        'The dedicated AI setup route stays visibly gated so the product does not imply broad self-serve AI provider coverage.',
        'Launch support is limited to the approved provider path and truthful runtime ingestion into the main operator workflow.',
        'Self-serve AI app registry, guardrail authoring, assistant workflows, and unsupported providers remain outside the default launch promise.',
      ]}
      primaryAction={{ label: 'Open Onboarding', href: '/onboarding' }}
      secondaryAction={{ label: 'Open AI Governance', href: '/dashboard/ai-governance' }}
    />
  );
}
