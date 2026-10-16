'use client';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function IamReportsPage() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-5xl">
        <Breadcrumbs />
      </div>
      <LaunchBoundaryNotice
        eyebrow="Launch boundary"
        title="Legacy IAM report downloads are outside the narrowed launch path"
        description="This route previously generated placeholder IAM report exports, so it is removed from the default production workflow until those reports are backed by audited tenant activity data."
        bullets={[
          'The old login-history and access-log downloads were placeholder CSV outputs rather than evidence-backed exports.',
          'The launch-scoped reporting surface is the compliance reporting path that is explicitly bounded and evidence-backed.',
          'IAM-specific report exports can return after the underlying audit-data contract and report generation path are hardened.',
        ]}
        primaryAction={{ label: 'Open Compliance Reports', href: '/dashboard/compliance/reports' }}
        secondaryAction={{ label: 'Return to IAM', href: '/dashboard/iam/people' }}
      />
    </div>
  );
}
