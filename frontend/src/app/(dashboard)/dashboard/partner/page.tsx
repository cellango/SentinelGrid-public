'use client';

import Breadcrumbs from '@/components/ui/Breadcrumbs';
import LaunchBoundaryNotice from '@/components/product/LaunchBoundaryNotice';

export default function PartnerConsolePage() {
  return (
    <div className="p-6">
      <div className="mx-auto max-w-5xl">
        <Breadcrumbs />
      </div>
      <LaunchBoundaryNotice
        eyebrow="Qualified sales-assisted scope"
        title="Partner workflows are not part of the default self-serve launch"
        description="Managed-tenant operations stay behind explicit qualification until the partner operating model, support contract, and delivery controls are proven as a bounded launch motion."
        bullets={[
          'The previous partner console used demo-backed cross-tenant portfolio data, so it is removed from the default launch workflow.',
          'Partner and MSP delivery remain available only through explicit qualification and delivery review, not as a website-led or self-serve dashboard path.',
          'The narrowed launch stays focused on the canonical operator plane for a single tenant scope.',
        ]}
        primaryAction={{ label: 'Return to Now', href: '/dashboard/now' }}
        secondaryAction={{ label: 'Review Launch Scope', href: '/dashboard/welcome' }}
      />
    </div>
  );
}
