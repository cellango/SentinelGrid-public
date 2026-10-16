'use client';

import { useEffect } from 'react';
import RouteErrorState from '@/components/errors/RouteErrorState';

export default function IncidentsRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Incidents route error', error);
  }, [error]);

  return (
    <RouteErrorState
      title="Incidents are temporarily unavailable"
      description="The incident queue failed to render. Retry here or return to the prioritized Now queue."
      reset={reset}
      backHref="/dashboard/now"
      backLabel="Open Now queue"
    />
  );
}
