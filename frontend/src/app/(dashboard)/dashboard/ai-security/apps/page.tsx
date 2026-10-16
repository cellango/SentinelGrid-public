'use client';

import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function AIAppsPage() {
  return (
    <LaunchBoundaryNotice
      eyebrow="AI Shield launch boundary"
      title="AI app registry stays implementation-led for launch"
      description="The self-serve AI app inventory and API key issuance flow is not exposed as a tenant-ready workflow in the main product path yet."
      bullets={[
        'Runtime AI findings should flow into Now, Alert Queue, Incident Queue, and AI Governance instead of a separate app registry screen.',
        'Per-app provisioning and key issuance remain owned by onboarding and implementation until tenant-scoped APIs are hardened behind the main platform.',
        'Use AI Governance to review AI activity that is already reaching the platform today.',
      ]}
      primaryAction={{ label: 'Open AI Governance', href: '/dashboard/ai-governance' }}
      secondaryAction={{ label: 'Open Onboarding', href: '/onboarding' }}
    />
  );
}
