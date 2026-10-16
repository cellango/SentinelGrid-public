'use client';

import { useEffect } from 'react';
import RouteErrorState from '@/components/errors/RouteErrorState';

export default function ComplianceRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Compliance route error', error);
  }, [error]);

  return (
    <RouteErrorState
      title="Compliance content failed to load"
      description="The governance surface hit an unexpected error. Retry the route or go back to the main compliance workspace."
      reset={reset}
      backHref="/dashboard/compliance"
      backLabel="Open Compliance"
    />
  );
}
