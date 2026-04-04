import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  doc,
  getDoc,
  setDoc,
  updateDoc
} from 'firebase/firestore';
import { auth, db } from '../services/firebase';
import { useAuth } from './AuthContext';

const PolicyContext = createContext();

export const usePolicy = () => {
  const context = useContext(PolicyContext);
  if (!context) {
    throw new Error('usePolicy must be used within a PolicyProvider');
  }
  return context;
};

export const PolicyProvider = ({ children }) => {
  const { user } = useAuth();
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getUserPolicy = useCallback(async () => {
    try {
      if (!db || !auth?.currentUser) {
        console.log('getUserPolicy: No db or authenticated user');
        return null;
      }

      console.log('getUserPolicy: Getting policy for user:', auth.currentUser.uid);
      setLoading(true);

      const policyRef = doc(db, 'policies', auth.currentUser.uid);
      const policyDoc = await getDoc(policyRef);

      console.log('getUserPolicy: Policy exists:', policyDoc.exists());

      if (policyDoc.exists()) {
        const policyData = policyDoc.data();
        console.log('getUserPolicy: Setting existing policy:', policyData);
        setPolicy(policyData);
      } else {
        console.log('getUserPolicy: Creating new trial policy');
        const trialPolicy = {
          uid: auth.currentUser.uid,
          type: 'trial',
          status: 'active',
          startDate: new Date().toISOString(),
          endDate: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000).toISOString(),
          coverageAmount: 4000,
          coverageRemaining: 4000,
          premiumAmount: 100,
          createdAt: new Date().toISOString()
        };

        try {
          await setDoc(policyRef, trialPolicy);
          console.log('getUserPolicy: Trial policy saved to Firestore');
        } catch (firestoreError) {
          console.error('getUserPolicy: Firestore save error:', firestoreError);
        }
        setPolicy(trialPolicy);
      }
    } catch (err) {
      console.error('Get policy error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    console.log('PolicyContext useEffect triggered, user:', user?.uid);
    if (!db) {
      setPolicy(null);
      return;
    }
    if (user?.uid && auth?.currentUser) {
      console.log('Calling getUserPolicy for user:', user.uid);
      getUserPolicy();
    } else {
      console.log('No authenticated user found');
      setPolicy(null);
    }
  }, [user?.uid, getUserPolicy]);

  const updatePolicyState = async (updates) => {
    try {
      if (!db || !auth?.currentUser || !policy) return;

      setLoading(true);
      const updatedPolicy = { ...policy, ...updates };

      const policyRef = doc(db, 'policies', auth.currentUser.uid);
      await updateDoc(policyRef, updates);
      setPolicy(updatedPolicy);
    } catch (err) {
      console.error('Update policy error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const value = {
    policy,
    loading,
    error,
    getUserPolicy,
    updatePolicyState
  };

  return (
    <PolicyContext.Provider value={value}>
      {children}
    </PolicyContext.Provider>
  );
};
