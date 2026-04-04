import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  onAuthStateChanged,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  updateProfile,
} from 'firebase/auth';
import { setDoc, doc } from 'firebase/firestore';
import { auth, db } from '../services/firebase';
import { BASE_URL, fetchWithTimeout } from '../services/apiService';

const AuthContext = createContext();
const AUTH_BOOTSTRAP_TIMEOUT = 3000; // Reduced to 3 seconds

const createMockUser = ({ email, displayName, phoneNumber = '' } = {}) => ({
  uid: `mock-user-${Date.now()}`,
  email: email || 'demo@rahatpay.app',
  displayName: displayName || 'Demo User',
  phoneNumber,
  aadhaar: '',
  isVerified: false,
  isDemoUser: true,
});

const FALLBACK_RIDER_ID = 2;
const DEMO_PASSWORD = '123456';
const DEMO_ACCOUNTS = {
  'imran@rahatpay.app': {
    uid: 'demo-imran-shaikh',
    email: 'imran@rahatpay.app',
    displayName: 'Imran Shaikh',
    phoneNumber: '+919101000008',
    platform: 'swiggy',
    city: 'Bangalore',
    tier: 'raksha',
    zone1_id: 14,
    zone2_id: 15,
    zone3_id: null,
  },
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isUsingMockAuth, setIsUsingMockAuth] = useState(false);
  const [authInitialized, setAuthInitialized] = useState(false);
  const [riderId, setRiderId] = useState(null);

  useEffect(() => {
    // Force timeout to prevent infinite loading
    const bootstrapTimer = setTimeout(() => {
      console.warn('Auth bootstrap timed out, using mock auth');
      const mockUser = createMockUser();
      setUser(mockUser);
      setIsUsingMockAuth(true);
      setLoading(false);
      setAuthInitialized(true);
    }, AUTH_BOOTSTRAP_TIMEOUT);

    // If Firebase auth is not available, use mock auth immediately
    if (!auth) {
      console.log('Firebase auth not available, using mock auth');
      clearTimeout(bootstrapTimer);
      const mockUser = createMockUser();
      setUser(mockUser);
      setIsUsingMockAuth(true);
      setLoading(false);
      setAuthInitialized(true);
      return;
    }

    let unsubscribe = null;
    try {
      unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
        try {
          console.log('Auth state changed:', firebaseUser ? 'User logged in' : 'User logged out');
          clearTimeout(bootstrapTimer);

          if (firebaseUser) {
            setIsUsingMockAuth(false);
            setUser({
              uid: firebaseUser.uid,
              email: firebaseUser.email,
              displayName: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'User',
              phoneNumber: firebaseUser.phoneNumber || '',
              aadhaar: '',
              isVerified: false
            });
          } else {
            setUser(null);
          }
          setAuthInitialized(true);
          setLoading(false);
        } catch (err) {
          console.error('Auth state change error:', err);
          setError(err.message);
          // Fallback to mock auth on error
          const mockUser = createMockUser();
          setUser(mockUser);
          setIsUsingMockAuth(true);
          setLoading(false);
          setAuthInitialized(true);
        }
      });
    } catch (err) {
      console.error('Failed to setup auth listener:', err);
      clearTimeout(bootstrapTimer);
      const mockUser = createMockUser();
      setUser(mockUser);
      setIsUsingMockAuth(true);
      setLoading(false);
      setAuthInitialized(true);
    }

    return () => {
      clearTimeout(bootstrapTimer);
      if (unsubscribe) {
        unsubscribe();
      }
    };
  }, []);

  const signUp = async (email, password, displayName, phoneNumber) => {
    try {
      setError(null);
      setLoading(true);

      if (!auth) {
        const mockUser = createMockUser({ email, displayName, phoneNumber });
        setUser(mockUser);
        setIsUsingMockAuth(true);

        // Sync to backend even in mock mode
        await syncUserToBackend(mockUser);

        return { success: true, user: mockUser };
      }

      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const firebaseUser = userCredential.user;

      await updateProfile(firebaseUser, { displayName });

      if (db) {
        await setDoc(doc(db, 'users', firebaseUser.uid), {
          uid: firebaseUser.uid,
          email,
          displayName,
          phoneNumber,
          createdAt: new Date().toISOString(),
          isVerified: false
        });
      }

      // Sync to PostgreSQL backend
      await syncUserToBackend({
        uid: firebaseUser.uid,
        email,
        displayName,
        phoneNumber
      });

      return { success: true, user: firebaseUser };
    } catch (err) {
      const shouldFallbackToMockAuth =
        err.message.includes('Firebase auth not initialized') ||
        err.message.includes('network-request-failed') ||
        err.message.includes('internal-error');

      if (shouldFallbackToMockAuth) {
        const mockUser = createMockUser({ email, displayName, phoneNumber });
        setUser(mockUser);
        setIsUsingMockAuth(true);
        setError(null);

        // Sync to backend
        await syncUserToBackend(mockUser);

        return { success: true, user: mockUser };
      }

      const errorMessage = err.message.includes('email-already-in-use')
        ? 'Email already exists'
        : err.message;
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Sync user to PostgreSQL backend
  const syncUserToBackend = async (userData) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/admin/sync-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer admin_token'
        },
        body: JSON.stringify({
          firebase_uid: userData.uid,
          email: userData.email,
          display_name: userData.displayName || 'User',
          phone: userData.phoneNumber || null,
          platform: userData.platform || 'swiggy',
          city: userData.city || 'chennai',
          tier: userData.tier || 'suraksha',
          zone1_id: userData.zone1_id || 1,
          zone2_id: userData.zone2_id ?? 2,
          zone3_id: userData.zone3_id ?? 3
        })
      });

      const data = await response.json();
      console.log('User sync result:', data);
      const resolvedRiderId = data?.rider_id || FALLBACK_RIDER_ID;
      setRiderId(resolvedRiderId);
      return data;
    } catch (err) {
      console.warn('User sync failed (non-critical):', err.message);
      setRiderId(FALLBACK_RIDER_ID);
      // Don't block signup if sync fails
      return { rider_id: FALLBACK_RIDER_ID, status: 'fallback' };
    }
  };

  // NOTE: seedUserData has been removed from the mobile app.
  // Data seeding is now exclusively an admin dashboard operation.
  // The mobile app detects seeded data via subscription-state polling.

  // Get user earnings history
  const getUserEarnings = async (rId, days = 15) => {
    try {
      const response = await fetchWithTimeout(`${BASE_URL}/admin/rider/${rId}/earnings?days=${days}`, {
        headers: {
          'Authorization': 'Bearer admin_token'
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch earnings');
      }

      const data = await response.json();
      return { success: true, data };
    } catch (err) {
      console.error('Get earnings error:', err);
      return { success: false, error: err.message };
    }
  };

  const signIn = async (email, password) => {
    try {
      setError(null);
      setLoading(true);

      const normalizedEmail = email?.trim().toLowerCase();
      const demoAccount = DEMO_ACCOUNTS[normalizedEmail];
      if (demoAccount && password === DEMO_PASSWORD) {
        const demoUser = {
          ...demoAccount,
          aadhaar: '',
          isVerified: true,
          isDemoUser: true,
        };
        setUser(demoUser);
        setIsUsingMockAuth(true);
        setError(null);
        await syncUserToBackend(demoUser);
        return { success: true, user: demoUser };
      }

      if (!auth) {
        const mockUser = createMockUser({ email, displayName: email?.split('@')[0] });
        setUser(mockUser);
        setIsUsingMockAuth(true);
        setRiderId(FALLBACK_RIDER_ID);
        return { success: true, user: mockUser };
      }

      const userCredential = await signInWithEmailAndPassword(auth, email, password);
      await syncUserToBackend({
        uid: userCredential.user.uid,
        email: userCredential.user.email || email,
        displayName: userCredential.user.displayName || email?.split('@')[0] || 'User',
        phoneNumber: userCredential.user.phoneNumber || null
      });
      return { success: true, user: userCredential.user };
    } catch (err) {
      const shouldFallbackToMockAuth =
        err.message.includes('Firebase auth not initialized') ||
        err.message.includes('network-request-failed') ||
        err.message.includes('internal-error');

      if (shouldFallbackToMockAuth) {
        const mockUser = createMockUser({ email, displayName: email?.split('@')[0] });
        setUser(mockUser);
        setIsUsingMockAuth(true);
        setError(null);
        setRiderId(FALLBACK_RIDER_ID);
        return { success: true, user: mockUser };
      }

      const errorMessage = err.message.includes('user-not-found') || err.message.includes('wrong-password')
        ? 'Invalid email or password'
        : err.message;
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      if (isUsingMockAuth) {
        setUser(null);
        setIsUsingMockAuth(false);
        setError(null);
        setRiderId(null);
        return;
      }

      if (!auth) {
        throw new Error('Firebase auth not initialized');
      }

      await firebaseSignOut(auth);
      setUser(null);
      setError(null);
      setRiderId(null);
    } catch (err) {
      console.error('Sign out error:', err);
      setError(err.message);
    }
  };

  const continueAsGuest = async () => {
    const mockUser = createMockUser();
    setUser(mockUser);
    setIsUsingMockAuth(true);
    setError(null);
    setRiderId(FALLBACK_RIDER_ID);
    return { success: true, user: mockUser };
  };

  const updateUserProfile = async (updates) => {
    try {
      if (!user || !auth?.currentUser) return { success: false, error: 'No user logged in' };

      await updateProfile(auth.currentUser, updates);

      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, error: err.message };
    }
  };

  const value = {
    user,
    loading,
    error,
    isUsingMockAuth,
    riderId, // Will be set after sync
    signUp,
    signIn,
    signOut,
    updateUserProfile,
    continueAsGuest,
    getUserEarnings
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
