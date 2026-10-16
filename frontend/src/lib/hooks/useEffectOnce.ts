import { useEffect, useRef } from "react";

/**
 * Run an effect only once (on mount), ignoring subsequent renders.
 */
export function useEffectOnce(effect: () => void | (() => void)) {
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) {
      return;
    }
    hasRun.current = true;
    return effect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
