'use client';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function OperationsDashboard() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-5xl">
        <Breadcrumbs />
      </div>
      <LaunchBoundaryNotice
        eyebrow="Internal route"
        title="Platform operations is outside the customer-facing launch surface"
        description="This route previously showed placeholder SOC and platform metrics. It now stays intentionally out of the launch path until internal analytics are backed by audited production data sources."
        bullets={[
          'Tenant-facing navigation no longer points operators into placeholder internal metrics.',
          'Partner and revenue workflows remain qualified or internal-only instead of part of the default self-serve dashboard.',
          'A future internal operations dashboard should return only after the metrics contract, ownership model, and production data sources are hardened.',
        ]}
        primaryAction={{ label: 'Return to Now', href: '/dashboard/now' }}
        secondaryAction={{ label: 'Review Launch Scope', href: '/dashboard/welcome' }}
      />
    </div>
  );
}
