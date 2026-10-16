'use client';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function IamDevicesPage() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-5xl">
        <Breadcrumbs />
      </div>
      <LaunchBoundaryNotice
        eyebrow="Launch boundary"
        title="IAM device inventory is not part of the narrowed launch workflow"
        description="This route previously mixed manual sample-device loading and placeholder security-posture responses, so it is removed from the default launch path until the device inventory contract is backed by real tenant telemetry."
        bullets={[
          'Sample-device seeding is not an acceptable production operator workflow.',
          'The previous device security posture refresh relied on placeholder recommendations instead of verified endpoint telemetry.',
          'The qualified launch endpoint story stays centered on the hardened endpoint coverage path, not a demo-style IAM inventory console.',
        ]}
        primaryAction={{ label: 'Open Endpoint Coverage', href: '/dashboard/endpoint-protection' }}
        secondaryAction={{ label: 'Return to IAM', href: '/dashboard/iam/people' }}
      />
    </div>
  );
}
