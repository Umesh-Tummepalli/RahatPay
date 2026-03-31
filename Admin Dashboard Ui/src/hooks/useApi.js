import { useState, useEffect } from "react";

/**
 * A boilerplate hook to handle real API calls later.
 * For now, you can keep the hardcoded UI or swap in this mock.
 *
 * Usage Example:
 * const { data, loading, error } = useApi('/api/dashboard');
 */
export function useApi(endpoint, initialData = null) {
  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    // TODO: Replace this timeout mockup with a real fetch call
    // fetch(`https://your-rahatpay-backend.com${endpoint}`, { headers: { ... } })
    //   .then(res => res.json())
    //   .then(json => { if (isMounted) setData(json) })
    //   .catch(err => { if (isMounted) setError(err) })
    //   .finally(() => { if (isMounted) setLoading(false) });

    const timer = setTimeout(() => {
      if (isMounted) {
        setLoading(false);
      }
    }, 500);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [endpoint]);

  return { data, loading, error };
}
