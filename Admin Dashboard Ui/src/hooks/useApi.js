import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = "http://localhost:8001";
const ADMIN_HEADERS = {
  "Authorization": "Bearer admin_token",
  "Content-Type": "application/json",
};

/**
 * Generic fetch wrapper for admin API calls.
 *
 * @param {string} endpoint   – path relative to API_BASE
 * @param {object} initialData – default value before first fetch
 * @param {object} opts
 * @param {number} [opts.pollingInterval] – ms between automatic re-fetches (0 = disabled)
 */
export function useApi(endpoint, initialData = null, { pollingInterval = 0 } = {}) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { headers: ADMIN_HEADERS });
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      const json = await res.json();
      if (mountedRef.current) {
        setData(json);
        setError(null);
      }
    } catch (err) {
      console.error(`API Fetch Error [${endpoint}]:`, err);
      if (mountedRef.current) setError(err);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [endpoint]);

  // Initial fetch
  useEffect(() => {
    mountedRef.current = true;
    setLoading(true);
    fetchData();
    return () => { mountedRef.current = false; };
  }, [fetchData]);

  // Optional polling
  useEffect(() => {
    if (!pollingInterval || pollingInterval <= 0) return;
    const id = setInterval(fetchData, pollingInterval);
    return () => clearInterval(id);
  }, [fetchData, pollingInterval]);

  return { data, loading, error, refetch: fetchData };
}

/**
 * Fire-and-forget POST / PATCH / PUT helper.
 * Returns a callable `execute(body?)` and tracks loading + error.
 */
export function useApiMutation(endpoint, method = "POST") {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (body = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method,
        headers: ADMIN_HEADERS,
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      setData(json);
      return json;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [endpoint, method]);

  return { execute, loading, error, data };
}
