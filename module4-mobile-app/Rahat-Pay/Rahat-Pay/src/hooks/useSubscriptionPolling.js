/**
 * useSubscriptionPolling.js
 * -------------------------
 * Polls the backend's /rider/{id}/subscription-state endpoint every `intervalMs`
 * milliseconds and exposes the full subscription lifecycle state.
 *
 * Returns only server-driven data — the mobile app is a pure display layer.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { AppState } from 'react-native';
import { BASE_URL, fetchWithTimeout } from '../services/apiService';

const DEFAULT_INTERVAL = 5000; // 5 seconds

export function useSubscriptionPolling(riderId, intervalMs = DEFAULT_INTERVAL) {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);
  const appState = useRef(AppState.currentState);

  const fetchState = useCallback(async () => {
    if (!riderId) return;
    try {
      const response = await fetchWithTimeout(
        `${BASE_URL}/rider/${riderId}/subscription-state`,
        { headers: { 'Authorization': 'Bearer admin_token' } },
        6000
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (mountedRef.current) {
        setState(data);
        setError(null);
      }
    } catch (err) {
      console.warn('Subscription poll error:', err.message);
      if (mountedRef.current) setError(err.message);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [riderId]);

  // Initial fetch + polling interval
  useEffect(() => {
    mountedRef.current = true;
    setLoading(true);
    fetchState();

    const interval = setInterval(() => {
      // Only poll when app is in foreground
      if (appState.current === 'active') {
        fetchState();
      }
    }, intervalMs);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [fetchState, intervalMs]);

  // Pause polling when app is backgrounded
  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState) => {
      appState.current = nextState;
    });
    return () => subscription?.remove();
  }, []);

  // Acknowledge notification
  const acknowledgeNotification = useCallback(async () => {
    if (!riderId) return;
    try {
      await fetchWithTimeout(
        `${BASE_URL}/rider/${riderId}/subscription-state/ack-notification`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer admin_token',
          },
        },
        6000
      );
      // Re-fetch immediately after ack
      await fetchState();
    } catch (err) {
      console.warn('Ack notification error:', err.message);
    }
  }, [riderId, fetchState]);

  // Derived convenience values
  const phase = state?.phase || 'trial_active';
  const notification = state?.notification || null;
  const notificationUnread = state?.notification_unread || false;
  const banner = state?.banner || null;
  const trial = state?.trial || {};
  const premiumQuotes = state?.premium_quotes || {};
  const planOptions = state?.plan_options || [];
  const quoteSummary = state?.quote_summary || {};
  const currentPlan = state?.current_plan || null;
  const hasSeededHistory = state?.has_seeded_history || false;

  return {
    // Raw state from server
    state,
    loading,
    error,
    refetch: fetchState,
    acknowledgeNotification,

    // Derived for convenience
    phase,
    notification,
    notificationUnread,
    banner,
    trial,
    premiumQuotes,
    planOptions,
    quoteSummary,
    currentPlan,
    hasSeededHistory,
  };
}
