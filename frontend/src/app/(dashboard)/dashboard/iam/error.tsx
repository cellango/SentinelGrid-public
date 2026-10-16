'use client';

import { useEffect } from 'react';
import RouteErrorState from '@/components/errors/RouteErrorState';

export default function IAMRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('IAM route error', error);
  }, [error]);

  return (
    <RouteErrorState
      title="Identity operations are temporarily unavailable"
      description="The IAM workspace failed to load. Retry this route or return to the people and access workspace."
      reset={reset}
      backHref="/dashboard/iam/people"
      backLabel="Open People & Access"
    />
  );
}
