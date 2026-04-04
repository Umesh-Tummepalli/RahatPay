import { validateAadhaar, validatePAN } from '../utils/validation';
import Constants from 'expo-constants';

/**
 * Resolves the correct backend base URL.
 *
 * • Web (browser / admin dashboard):  uses window.location.hostname so the
 *   Vite proxy handles routing automatically.
 * • Expo Go on a physical device:     uses the dev-server host IP extracted
 *   from Constants.expoConfig.hostUri (e.g. "192.168.1.12:8081" → "192.168.1.12")
 *   so the phone can reach the host machine on the LAN.
 * • Android emulator fallback:        10.0.2.2  (maps to host loopback)
 * • Everything else:                  localhost (works for web / iOS sim)
 */
const _getBaseUrl = () => {
  // Web environment (Vite dev server proxies all /rider, /admin, etc.)
  if (typeof window !== 'undefined' && window.location && window.location.hostname) {
    const { protocol, hostname } = window.location;
    return `${protocol}//${hostname}:8000`;
  }

  // Expo Go — extract host IP from the Metro bundler address
  try {
    const hostUri =
      Constants.expoConfig?.hostUri ||        // SDK 46+
      Constants.manifest2?.extra?.expoClient?.hostUri ||
      Constants.manifest?.debuggerHost;       // older SDKs
    if (hostUri) {
      const hostIp = hostUri.split(':')[0];   // strip port ("192.168.x.x:8081" → "192.168.x.x")
      if (hostIp && hostIp !== 'localhost' && hostIp !== '127.0.0.1') {
        return `http://${hostIp}:8000`;
      }
    }
  } catch (_) {
    // ignore — fall through to defaults
  }

  // Android emulator maps 10.0.2.2 → host loopback
  // (React Native's Platform is only available in RN context — safe to require lazily)
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const { Platform } = require('react-native');
    if (Platform.OS === 'android') {
      return 'http://10.0.2.2:8000';
    }
  } catch (_) { /* ignore */ }

  return 'http://localhost:8000';
};

export const BASE_URL = _getBaseUrl();
const REQUEST_TIMEOUT_MS = 15000; // increased to 15s — physical device LAN can be slower

export const fetchWithTimeout = async (url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal,
    });
  } catch (err) {
    // Give the user a meaningful message instead of the raw "Aborted" or "Network request failed"
    if (err.name === 'AbortError') {
      const friendlyErr = new Error(
        `Backend unreachable at ${url.replace(/^(https?:\/\/[^/]+).*/, '$1')} — ` +
        'make sure the server is running and your phone is on the same WiFi network.'
      );
      friendlyErr.name = 'AbortError';
      throw friendlyErr;
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
};

// Mock API responses for fallback
export const mockApi = {
  getUser: async (userId) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/rider/${userId}/dashboard`);
      if (!response.ok) throw new Error("Backend unavailable");
      const payload = await response.json();

      return {
        success: true,
        data: {
          userId,
          name: payload.rider.name,
          email: `${payload.rider.platform.toLowerCase()}@rahatpay.demo`,
          phone: payload.rider.phone,
          kycVerified: payload.rider.kyc_verified,
          createdAt: payload.active_policy ? payload.active_policy.cycle_start_date : '2026-03-15T10:30:00Z',
          city: payload.rider.city,
        }
      };
    } catch (err) {
      console.warn("Using mock for getUser due to", err);
      return {
        success: true,
        data: {
          userId, name: 'Priya Sharma', email: 'priya@example.com',
          phone: '+919123456789', kycVerified: true, createdAt: '2026-03-15T10:30:00Z'
        }
      };
    }
  },

  getIncomeProfile: async (userId) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/rider/${userId}/income-profile`);
      if (!response.ok) throw new Error("Backend unavailable");
      const payload = await response.json();
      return { success: true, data: payload };
    } catch (err) {
      console.warn("Using mock for getIncomeProfile due to", err);
      const fallbackHistory = Array.from({length: 15}, (_, i) => ({day: 15-i, amount: Math.floor(Math.random() * 800) + 400}));
      const avg = fallbackHistory.reduce((acc, curr) => acc + curr.amount, 0) / 15;
      return {
        success: true,
        data: {
          baseline_weekly_income: avg * 7,
          daily_income_history: fallbackHistory,
          zone_ids: [1]
        }
      };
    }
  },

  updateUser: async (userId, userData) => {
    await new Promise(resolve => setTimeout(resolve, 300));
    return { success: true };
  },

  getPolicy: async (userId) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/rider/${userId}/dashboard`);
      if (!response.ok) throw new Error("Backend unavailable");
      const payload = await response.json();
      const policy = payload.active_policy;

      if (!policy) throw new Error("No policy");

      return {
        success: true,
        data: {
          userId,
          type: policy.tier,
          startDate: policy.cycle_start_date + 'T00:00:00Z',
          endDate: policy.cycle_end_date + 'T23:59:59Z',
          coverageTotal: policy.weekly_payout_cap,
          coverageRemaining: policy.weekly_payout_cap,
          premium: policy.weekly_premium,
          status: policy.status
        }
      };
    } catch (err) {
      return {
        success: true,
        data: {
          userId, type: 'trial', startDate: '2026-03-30T00:00:00Z', endDate: '2026-04-14T23:59:59Z',
          coverageTotal: 4000, coverageRemaining: 4000, premium: 100, status: 'active'
        }
      };
    }
  },

  createPolicy: async (policyData) => {
    await new Promise(resolve => setTimeout(resolve, 600));
    return {
      success: true,
      data: {
        ...policyData, id: 'POL_' + Date.now(), createdAt: new Date().toISOString()
      }
    };
  },

  updatePolicy: async (policyId, updates) => {
    await new Promise(resolve => setTimeout(resolve, 300));
    return { success: true };
  },

  getTransactions: async (userId, limit = 50) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/rider/${userId}/payouts`);
      if (!response.ok) throw new Error("Backend unavailable");
      const payload = await response.json();

      const transactions = payload.map((p, idx) => ({
        id: 'TXN_' + (p.id || idx),
        userId,
        type: 'payout',
        amount: p.amount,
        eventType: p.trigger_type,
        description: `Disaster Engine: ${p.trigger_type.charAt(0).toUpperCase() + p.trigger_type.slice(1)} Payout`,
        status: p.status === 'paid' ? 'completed' : 'pending',
        createdAt: p.processed_at || new Date().toISOString()
      }));

      // If backend has no payouts yet, append a fake premium payment so UI isn't totally empty
      if (transactions.length === 0) {
        transactions.push({
          id: 'TXN_PR_001',
          userId,
          type: 'premium',
          amount: -88.20,
          description: 'Weekly premium payment',
          status: 'completed',
          createdAt: new Date(Date.now() - 86400000).toISOString()
        });
      }

      return { success: true, data: transactions.slice(0, limit) };
    } catch (err) {
      return {
        success: true,
        data: [
          { id: 'TXN_002', userId, type: 'payout', amount: 500, eventType: 'Flood', description: 'Flood detected', status: 'completed', createdAt: '2026-03-31T14:15:00Z', remainingBalance: 3500 },
          { id: 'TXN_001', userId, type: 'premium', amount: -100, description: 'Trial premium payment', status: 'completed', createdAt: '2026-03-30T10:30:00Z' }
        ]
      };
    }
  },

  createTransaction: async (transactionData) => {
    await new Promise(resolve => setTimeout(resolve, 300));
    return { success: true, data: { ...transactionData, id: 'TXN_' + Date.now(), createdAt: new Date().toISOString() } };
  },

  submitKYC: async (kycData) => {
    await new Promise(resolve => setTimeout(resolve, 800));
    if (!validateAadhaar(kycData.aadhaar)) return { success: false, error: 'Invalid Aadhaar number' };
    if (!validatePAN(kycData.pan)) return { success: false, error: 'Invalid PAN number' };
    return {
      success: true,
      data: {
        aadhaarMasked: kycData.aadhaar.replace(/(\d{4})\d{4}(\d{4})/, '$1XXXX$2'),
        panMasked: kycData.pan.replace(/([A-Z]{5})\d{4}([A-Z])/, '$1****$2'),
        verified: false,
        submittedAt: new Date().toISOString()
      }
    };
  },

  verifyKYC: async (userId) => {
    await new Promise(resolve => setTimeout(resolve, 2000));
    return { success: true };
  },

  getEvents: async (userId) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/rider/${userId}/active-events`);
      if (!response.ok) throw new Error("Backend unavailable");
      const payload = await response.json();

      const events = payload.map((e, idx) => ({
        id: 'EVT_' + (e.id || idx),
        type: e.event_type,
        severity: e.severity || 'medium',
        location: 'Mumbai, Maharashtra',
        detectedAt: e.event_start || new Date().toISOString(),
        payoutAmount: 0,
        status: 'active'
      }));

      if (events.length === 0) {
        throw new Error("No events, fall back to mock to show some UI");
      }
      return { success: true, data: events };
    } catch (err) {
      return {
        success: true,
        data: [
          { id: 'EVT_001', type: 'flood', severity: 'high', location: 'Mumbai, Maharashtra', detectedAt: '2026-03-31T14:00:00Z', payoutAmount: 500, status: 'processed' }
        ]
      };
    }
  },

  getRecentEvents: async (zoneId = null, limit = 20) => {
    try {
      let url = `${BASE_URL}/admin/events/recent?limit=${limit}`;
      if (zoneId) {
        url += `&zone_id=${zoneId}`;
      }
      const response = await fetchWithTimeout(url);
      if (!response.ok) throw new Error("Backend unavailable");
      const payload = await response.json();

      const events = payload.map((e, idx) => ({
        id: 'EVT_' + (e.id || idx),
        type: e.event_type,
        severity: e.severity || 'medium',
        affectedZone: e.affected_zone,
        detectedAt: e.event_start || new Date().toISOString(),
        payoutRate: e.payout_rate || 0,
        status: 'active'
      }));

      return { success: true, data: events };
    } catch (err) {
      console.warn("Using mock for getRecentEvents due to", err);
      return {
        success: true,
        data: [
          { id: 'EVT_001', type: 'flood', severity: 'high', affectedZone: 9, detectedAt: '2026-03-31T14:00:00Z', payoutRate: 0.8, status: 'active' }
        ]
      };
    }
  },

  triggerEvent: async (eventType, userId) => {
    // This connects frontend event triggers logically to backend payouts (simulate)
    await new Promise(resolve => setTimeout(resolve, 500));
    return {
      success: true,
      data: {
        id: 'EVT_' + Date.now(), type: eventType, severity: 'high',
        location: 'Mumbai, Maharashtra', detectedAt: new Date().toISOString(),
        payoutAmount: 500, status: 'processed'
      }
    };
  },

  triggerRealDisasterEvent: async (eventType, severity, affectedZone, lostHours, severityRate) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/admin/simulate-disaster`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer admin_token'
        },
        body: JSON.stringify({
          event_type: eventType,
          severity: severity,
          affected_zone: affectedZone,
          lost_hours: lostHours,
          severity_rate: severityRate
        })
      });

      if (!response.ok) throw new Error("Backend unavailable");
      const result = await response.json();

      return {
        success: true,
        data: {
          eventId: result.event_id,
          claimsCreated: result.claims_created,
          totalPayout: result.total_payout_estimated,
          message: result.message
        }
      };
    } catch (err) {
      console.error("Failed to trigger real disaster event:", err);
      return {
        success: false,
        error: err.message
      };
    }
  },

  createPaymentOrder: async (amount, currency = 'INR') => {
    await new Promise(resolve => setTimeout(resolve, 400));
    return { success: true, data: { orderId: 'ORDER_' + Date.now(), amount, currency, receipt: 'RCPT_' + Date.now(), status: 'created' } };
  },

  verifyPayment: async (paymentId, orderId) => {
    await new Promise(resolve => setTimeout(resolve, 600));
    return { success: true, data: { paymentId, orderId, status: 'captured', amount: 118, method: 'upi', capturedAt: new Date().toISOString() } };
  }
};

export const apiClient = {
  useMock: true,

  get: async (endpoint, params = {}) => {
    return mockApi[endpoint.replace('/', '')](params);
  },

  post: async (endpoint, data = {}) => {
    return mockApi[endpoint.replace('/', '')](data);
  },

  put: async (endpoint, data = {}) => {
    return mockApi[endpoint.replace('/', '')](data);
  }
};
