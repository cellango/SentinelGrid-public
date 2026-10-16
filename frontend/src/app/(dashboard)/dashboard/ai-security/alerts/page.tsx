'use client';

import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function AIAlertsPage() {
  return (
    <LaunchBoundaryNotice
      eyebrow="AI Shield launch boundary"
      title="AI-originated alerts are handled in the main queue for launch"
      description="This dedicated AI alerts board previously showed mock findings, so it is replaced with the truthful launch path."
      bullets={[
        'Review AI-originated detections in Alert Queue and Incident Queue, where they share ownership and escalation with the rest of the platform.',
        'AI Governance remains the summarized reporting surface for AI activity and risk concentration.',
        'The standalone AI alerts board stays gated until it is backed by the same tenant-scoped alert APIs as the main queue.',
      ]}
      primaryAction={{ label: 'Open Alert Queue', href: '/dashboard/alerts' }}
      secondaryAction={{ label: 'Open AI Governance', href: '/dashboard/ai-governance' }}
    />
  );
}
