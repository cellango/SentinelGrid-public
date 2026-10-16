'use client';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function PenetrationTestingPage() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-5xl">
        <Breadcrumbs />
      </div>
      <LaunchBoundaryNotice
        eyebrow="Services-led offering"
        title="Penetration testing is not part of the day-one self-serve SaaS"
        description="SentinelGrid keeps penetration testing outside the core launch surface until scope intake, delivery controls, payment, evidence handling, and follow-up remediation are fully productized."
        bullets={[
          'The previous self-serve checkout and questionnaire flow was removed from the launch console because it overstated production readiness.',
          'Production launch focuses on the canonical operator plane, detections, incidents, posture, IAM, and baseline compliance workflows.',
          'Penetration testing remains a services-led engagement until a fresh audit can validate the full delivery and security model.',
        ]}
        primaryAction={{ label: 'Return to Now', href: '/dashboard/now' }}
        secondaryAction={{ label: 'Review Launch Scope', href: '/dashboard/welcome' }}
      />
    </div>
  );
}
