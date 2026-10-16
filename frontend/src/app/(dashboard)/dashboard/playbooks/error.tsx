'use client';

import { useEffect } from 'react';
import RouteErrorState from '@/components/errors/RouteErrorState';

export default function PlaybooksRouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Playbooks route error', error);
  }, [error]);

  return (
    <RouteErrorState
      title="Playbooks are temporarily unavailable"
      description="The response playbook workspace hit an unexpected error. Retry the route or return to the playbook catalog."
      reset={reset}
      backHref="/dashboard/playbooks"
      backLabel="Open Playbooks"
    />
  );
}
