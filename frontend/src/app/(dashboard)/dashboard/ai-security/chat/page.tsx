'use client';

import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function AIAssistantPage() {
  return (
    <LaunchBoundaryNotice
      eyebrow="AI Shield launch boundary"
      title="The AI security assistant is gated until it is tenant-aware and production-backed"
      description="This assistant previously returned stubbed answers, so it is removed from the launch workflow until it is connected to real AI activity, approvals, and audit history."
      bullets={[
        'Use AI Governance and the main queue to investigate AI findings in the current launch scope.',
        'Do not rely on this route for operational decisions until it is backed by real tenant data and observable execution.',
      ]}
      primaryAction={{ label: 'Open AI Governance', href: '/dashboard/ai-governance' }}
      secondaryAction={{ label: 'Open Now', href: '/dashboard/now' }}
    />
  );
}
