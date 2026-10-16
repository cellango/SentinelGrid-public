/**
 * Performance Utilities
 * Code splitting helpers, memoization, and performance monitoring.
 */

import { useCallback, useRef, useEffect } from 'react';

/**
 * Debounce hook — prevents rapid-fire function calls.
 * Useful for search inputs, resize handlers, scroll events.
 */
export function useDebounce<T extends (...args: any[]) => void>(
  callback: T,
  delay: number
): T {
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => callback(...args), delay);
    },
    [callback, delay]
  ) as T;
}

/**
 * Throttle hook — limits function execution to once per interval.
 * Useful for scroll handlers, resize events, real-time updates.
 */
export function useThrottle<T extends (...args: any[]) => void>(
  callback: T,
  limit: number
): T {
  const lastCallRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return useCallback(
    (...args: Parameters<T>) => {
      const now = Date.now();
      const timeSinceLastCall = now - lastCallRef.current;

      if (timeSinceLastCall >= limit) {
        lastCallRef.current = now;
        callback(...args);
      } else {
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        timeoutRef.current = setTimeout(() => {
          lastCallRef.current = Date.now();
          callback(...args);
        }, limit - timeSinceLastCall);
      }
    },
    [callback, limit]
  ) as T;
}

/**
 * Intersection Observer hook — detect when elements enter viewport.
 * Useful for lazy loading, infinite scroll, analytics.
 */
export function useInView(
  options?: IntersectionObserverInit
): [React.RefObject<HTMLDivElement | null>, boolean] {
  const ref = useRef<HTMLDivElement | null>(null);
  const inViewRef = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new IntersectionObserver(([entry]) => {
      inViewRef.current = entry.isIntersecting;
    }, options);

    observer.observe(element);
    return () => observer.disconnect();
  }, [options]);

  return [ref, inViewRef.current];
}

/**
 * Memoize a function with a simple cache.
 * For expensive computations that are called with the same arguments.
 */
export function memoize<T extends (...args: any[]) => any>(
  fn: T,
  maxSize = 50
): T {
  const cache = new Map<string, ReturnType<T>>();

  return ((...args: Parameters<T>) => {
    const key = JSON.stringify(args);
    if (cache.has(key)) return cache.get(key)!;

    const result = fn(...args);

    // Evict oldest if cache is full
    if (cache.size >= maxSize) {
      const firstKey = cache.keys().next().value;
      if (firstKey !== undefined) cache.delete(firstKey);
    }

    cache.set(key, result);
    return result;
  }) as T;
}

/**
 * Measure component render performance.
 * Only logs in development mode.
 */
export function useRenderCount(componentName: string): void {
  const countRef = useRef(0);

  useEffect(() => {
    if (process.env.NODE_ENV !== 'development') return;
    countRef.current += 1;
    if (countRef.current > 10) {
      console.warn(
        `[Performance] ${componentName} has rendered ${countRef.current} times. Consider memoization.`
      );
    }
  });
}

/**
 * Preload a route for faster navigation.
 * Triggers Next.js prefetch without navigating.
 */
export function preloadRoute(href: string): void {
  if (typeof window === 'undefined') return;
  const link = document.createElement('link');
  link.rel = 'prefetch';
  link.href = href;
  link.as = 'document';
  document.head.appendChild(link);
}
