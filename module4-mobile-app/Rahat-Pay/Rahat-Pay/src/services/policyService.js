import { 
  doc, 
  setDoc, 
  getDoc, 
  updateDoc, 
  collection, 
  query, 
  where, 
  getDocs,
  onSnapshot 
} from 'firebase/firestore';
import { db } from './firebase';
import { TRIAL_CONFIG } from '../utils/constants';

function requireDb() {
  if (!db) {
    throw new Error('Firestore not initialized');
  }
  return db;
}

export const createPolicy = async (userId, policyType = 'trial') => {
  try {
    const startDate = new Date();
    const endDate = new Date();
    endDate.setDate(endDate.getDate() + TRIAL_CONFIG.DURATION_DAYS);

    const policyData = {
      userId,
      type: policyType,
      startDate: startDate.toISOString(),
      endDate: endDate.toISOString(),
      coverageTotal: policyType === 'trial' ? TRIAL_CONFIG.COVERAGE_WEEKLY : 0,
      coverageRemaining: policyType === 'trial' ? TRIAL_CONFIG.COVERAGE_WEEKLY : 0,
      premium: policyType === 'trial' ? TRIAL_CONFIG.PREMIUM : 0,
      status: 'active',
      createdAt: new Date().toISOString()
    };

    await setDoc(doc(requireDb(), 'policies', userId), policyData);
    return { success: true, data: policyData };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

export const getPolicy = async (userId) => {
  try {
    const policyDoc = await getDoc(doc(requireDb(), 'policies', userId));
    if (policyDoc.exists()) {
      return { success: true, data: policyDoc.data() };
    }
    return { success: false, error: 'Policy not found' };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

export const updatePolicy = async (userId, updates) => {
  try {
    await updateDoc(doc(requireDb(), 'policies', userId), updates);
    return { success: true };
  } catch (error) {
    return { success: false, error: error.message };
  }
};

export const subscribeToPolicy = (userId, callback) => {
  const policyRef = doc(requireDb(), 'policies', userId);
  return onSnapshot(policyRef, (snapshot) => {
    if (snapshot.exists()) {
      callback(snapshot.data());
    } else {
      callback(null);
    }
  });
};

export const deductCoverage = async (userId, amount) => {
  try {
    const policyResult = await getPolicy(userId);
    if (!policyResult.success) {
      return { success: false, error: 'Policy not found' };
    }

    const policy = policyResult.data;
    const newRemaining = policy.coverageRemaining - amount;

    if (newRemaining < 0) {
      return { success: false, error: 'Insufficient coverage' };
    }

    await updatePolicy(userId, { coverageRemaining: newRemaining });
    return { success: true, newRemaining };
  } catch (error) {
    return { success: false, error: error.message };
  }
};
