'use client';

import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function AIEventsPage() {
  return (
    <LaunchBoundaryNotice
      eyebrow="AI Shield launch boundary"
      title="The dedicated AI event log is not a standalone launch surface"
      description="AI runtime evidence should be reviewed through AI Governance and the main operator queues until the event-log APIs are exposed through the production product path."
      bullets={[
        'The previous AI event table was backed by a stub client, so it is intentionally removed from the launch workflow.',
        'Use AI Governance for summarized AI activity and the main alert or incident queues for operational follow-through.',
        'Keep AI Shield onboarding healthy so runtime events can enter the shared platform views.',
      ]}
      primaryAction={{ label: 'Open AI Governance', href: '/dashboard/ai-governance' }}
      secondaryAction={{ label: 'Open Alert Queue', href: '/dashboard/alerts' }}
    />
  );
}
