'use client';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function MarketingFunnelPage() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-5xl">
        <Breadcrumbs />
      </div>
      <LaunchBoundaryNotice
        eyebrow="Internal route"
        title="Revenue and activation analytics stay outside the customer launch surface"
        description="This internal funnel dashboard is not part of the product a customer buys at launch, so it should not appear as a normal destination inside the tenant-facing console."
        bullets={[
          'Revenue and activation analytics remain internal-only operating data, not a customer workflow.',
          'The default launch path should return buyers to Now, onboarding, and the supported governance surfaces instead of internal revenue dashboards.',
          'Internal commercial analytics can return later only if they are clearly separated from the shipped customer product.',
        ]}
        primaryAction={{ label: 'Return to Now', href: '/dashboard/now' }}
        secondaryAction={{ label: 'Review Launch Scope', href: '/dashboard/welcome' }}
      />
    </div>
  );
}
