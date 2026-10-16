'use client';

import { useEffect } from 'react';
import RouteErrorState from '@/components/errors/RouteErrorState';

export default function AlertsRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Alerts route error', error);
  }, [error]);

  return (
    <RouteErrorState
      title="Alerts are temporarily unavailable"
      description="The alert queue hit an unexpected error. Retry the route or go back to the Now queue while the issue clears."
      reset={reset}
      backHref="/dashboard/now"
      backLabel="Open Now queue"
    />
  );
}
