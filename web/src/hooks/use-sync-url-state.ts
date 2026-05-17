"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

interface UseSyncUrlStateOptions<T extends Record<string, string>> {
  /** Default values when params are absent. */
  defaults: T;
}

/**
 * Syncs React state to URL query params bidirectionally.
 *
 * Every filter, tab, selection syncs to URL.
 * Share URL → recipient sees exact same view.
 */
export function useSyncUrlState<T extends Record<string, string>>({
  defaults,
}: UseSyncUrlStateOptions<T>) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Build state from URL params (or defaults)
  const getStateFromUrl = useCallback((): T => {
    const state = { ...defaults } as T;
    for (const key of Object.keys(defaults)) {
      const val = searchParams.get(key);
      if (val != null) {
        (state as Record<string, string>)[key] = val;
      }
    }
    return state;
  }, [searchParams, defaults]);

  const [state, setState] = useState<T>(getStateFromUrl);

  // Update state when URL changes (back/forward nav)
  useEffect(() => {
    setState(getStateFromUrl());
  }, [getStateFromUrl]);

  // Sync state changes back to URL (replace, not push — avoids history clutter)
  const setUrlState = useCallback(
    (next: Partial<T>) => {
      const newState = { ...state, ...next };
      const params = new URLSearchParams(searchParams.toString());

      for (const [key, val] of Object.entries(newState)) {
        if (val === defaults[key as keyof T]) {
          params.delete(key);
        } else {
          params.set(key, val);
        }
      }

      const query = params.toString();
      const url = `${window.location.pathname}${query ? `?${query}` : ""}`;
      router.replace(url, { scroll: false });
      setState(newState);
    },
    [state, searchParams, defaults, router],
  );

  return { state, setUrlState };
}
