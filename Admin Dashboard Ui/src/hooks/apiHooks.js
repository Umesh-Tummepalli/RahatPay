import { useState, useEffect, useCallback, useRef } from "react";

/**
 * usePolling — polls a URL at a fixed interval and returns { data, loading, error, isMock }
 *
 * @param {Function} fetchFn       – async function returning data (may throw)
 * @param {*}        fallbackData  – value to use when fetchFn throws
 * @param {number}   interval      – polling interval in ms (default 10 000)
 *
 * Usage:
 *   const { data, loading, error, isMock } = usePolling(
 *     () => api.getPollingLog(),
 *     { entries: [] },
 *     10_000,
 *   );
 */
export function usePolling(fetchFn, fallbackData, interval = 10_000) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [isMock, setIsMock]   = useState(false);
  const mountedRef            = useRef(true);

  const poll = useCallback(async () => {
    try {
      const result = await fetchFn();
      if (!mountedRef.current) return;
      setData(result);
      setError(null);
      setIsMock(false);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err);
      setIsMock(true);
      if (data === null) {
        // Only set fallback on first failure (don't clobber stale-but-good data)
        setData(fallbackData);
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchFn]);

  useEffect(() => {
    mountedRef.current = true;
    poll();
    const id = setInterval(poll, interval);
    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, [poll, interval]);

  return { data, loading, error, isMock, refetch: poll };
}

/**
 * useSafeApi — one-shot fetch with fallback (no polling).
 * Never lets a failure propagate to the UI; always resolves to either
 * real data or fallbackData.
 *
 * @param {Function} fetchFn      – async function returning data
 * @param {*}        fallbackData – value to return on failure
 */
export function useSafeApi(fetchFn, fallbackData = null) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [isMock, setIsMock]   = useState(false);
  const mountedRef            = useRef(true);

  const execute = useCallback(async () => {
    setLoading(true);
    try {
      const result = await fetchFn();
      if (!mountedRef.current) return;
      setData(result);
      setError(null);
      setIsMock(false);
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err);
      setData(fallbackData);
      setIsMock(true);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchFn]);

  useEffect(() => {
    mountedRef.current = true;
    execute();
    return () => { mountedRef.current = false; };
  }, [execute]);

  return { data, loading, error, isMock, refetch: execute };
}

/**
 * useApiMutation — fire-and-forget POST / PATCH wrapper.
 * Returns { execute(body), loading, error, data }.
 */
export function useApiMutation(fetchFn) {
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [data, setData]       = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchFn(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchFn]);

  return { execute, loading, error, data };
}
