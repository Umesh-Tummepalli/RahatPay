import { useState, useEffect, useCallback, useRef } from "react";

// Service base URLs
const SERVICE_URLS = {
  module1: "http://localhost:8001",
  module2: "http://localhost:8002",
  module3: "http://localhost:8003",
};

const ADMIN_HEADERS = {
  "Authorization": "Bearer admin_token",
  "Content-Type": "application/json",
};

/**
 * Resolve base URL from service key or full URL.
 * 
 * @param {string|undefined} baseUrlOrService – service key (module1/2/3) or full URL
 * @returns {string} resolved base URL
 */
function resolveBaseUrl(baseUrlOrService) {
  if (!baseUrlOrService) return SERVICE_URLS.module1; // Default to module1
  if (baseUrlOrService.startsWith("http://") || baseUrlOrService.startsWith("https://")) {
    return baseUrlOrService;
  }
  return SERVICE_URLS[baseUrlOrService] || SERVICE_URLS.module1;
}

/**
 * Generic fetch wrapper for admin API calls with multi-backend support.
 *
 * @param {string} endpoint – path relative to base URL
 * @param {object} initialData – default value before first fetch
 * @param {object} opts
 * @param {number} [opts.pollingInterval] – ms between automatic re-fetches (0 = disabled)
 * @param {string} [opts.baseUrl] – service key (module1/2/3) or full URL (default: module1)
 */
export function useApi(endpoint, initialData = null, { pollingInterval = 0, baseUrl = undefined } = {}) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const resolvedBaseUrl = resolveBaseUrl(baseUrl);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${resolvedBaseUrl}${endpoint}`, { headers: ADMIN_HEADERS });
      if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
      const json = await res.json();
      if (mountedRef.current) {
        setData(json);
        setError(null);
      }
    } catch (err) {
      console.error(`API Fetch Error [${resolvedBaseUrl}${endpoint}]:`, err);
      if (mountedRef.current) setError(err);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [endpoint, resolvedBaseUrl]);

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
 * Fire-and-forget POST / PATCH / PUT helper with multi-backend support.
 * Returns a callable `execute(body?)` and tracks loading + error.
 * 
 * @param {string} endpoint – path relative to base URL
 * @param {string} method – HTTP method (POST, PATCH, PUT, etc.)
 * @param {object} opts
 * @param {string} [opts.baseUrl] – service key (module1/2/3) or full URL (default: module1)
 */
export function useApiMutation(endpoint, method = "POST", { baseUrl = undefined } = {}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const resolvedBaseUrl = resolveBaseUrl(baseUrl);

  const execute = useCallback(async (body = {}) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${resolvedBaseUrl}${endpoint}`, {
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
  }, [endpoint, method, resolvedBaseUrl]);

  return { execute, loading, error, data };
}
