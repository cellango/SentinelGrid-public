'use client';

import { useEffect, useRef, useState } from 'react';

export type EventSourceStatus =
  | 'idle'
  | 'unsupported'
  | 'connecting'
  | 'open'
  | 'error';

interface UseEventSourceStreamOptions<T> {
  url: string | null;
  enabled?: boolean;
  onSnapshot?: (payload: T) => void;
}

export function useEventSourceStream<T>({
  url,
  enabled = true,
  onSnapshot,
}: UseEventSourceStreamOptions<T>) {
  const onSnapshotRef = useRef(onSnapshot);
  const [status, setStatus] = useState<EventSourceStatus>('idle');

  useEffect(() => {
    onSnapshotRef.current = onSnapshot;
  }, [onSnapshot]);

  useEffect(() => {
    if (!enabled || !url) {
      setStatus('idle');
      return;
    }

    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      setStatus('unsupported');
      return;
    }

    const source = new window.EventSource(url, { withCredentials: true });
    let closed = false;

    setStatus('connecting');

    const handleSnapshot = (event: MessageEvent<string>) => {
      try {
        const payload = JSON.parse(event.data) as T;
        onSnapshotRef.current?.(payload);
      } catch {
        setStatus('error');
      }
    };

    source.onopen = () => {
      if (!closed) {
        setStatus('open');
      }
    };

    source.addEventListener('snapshot', handleSnapshot as EventListener);
    source.onmessage = handleSnapshot;
    source.onerror = () => {
      if (!closed) {
        setStatus('error');
      }
    };

    return () => {
      closed = true;
      source.removeEventListener('snapshot', handleSnapshot as EventListener);
      source.close();
    };
  }, [enabled, url]);

  return {
    status,
    isLive: status === 'open',
  };
}
