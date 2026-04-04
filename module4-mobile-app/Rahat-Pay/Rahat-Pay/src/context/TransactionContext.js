import React, { createContext, useContext, useState } from 'react';
import {
  collection,
  addDoc,
  getDocs,
  query,
  where,
  orderBy
} from 'firebase/firestore';
import { auth, db } from '../services/firebase';

const hasFirestore = () => auth && db;

const TransactionContext = createContext();

export const useTransactions = () => {
  const context = useContext(TransactionContext);
  if (!context) {
    throw new Error('useTransactions must be used within a TransactionProvider');
  }
  return context;
};

export const TransactionProvider = ({ children }) => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Add transaction
  const addTransaction = async (transactionData) => {
    try {
      if (!hasFirestore() || !auth.currentUser) return { success: false, error: 'No user logged in' };

      setLoading(true);
      const transaction = {
        uid: auth.currentUser.uid,
        ...transactionData,
        createdAt: new Date().toISOString(),
        status: 'completed'
      };

      const transactionsRef = collection(db, 'transactions');
      await addDoc(transactionsRef, transaction);

      // Update local state
      setTransactions(prev => [transaction, ...prev]);

      return { success: true, transaction };
    } catch (err) {
      console.error('Add transaction error:', err);
      setError(err.message);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  // Add premium transaction
  const addPremiumTransaction = async (amount) => {
    return addTransaction({
      type: 'premium',
      amount,
      description: 'Trial Premium Payment',
      category: 'payment'
    });
  };

  // Add payout transaction
  const addPayoutTransaction = async (eventType, amount, description) => {
    return addTransaction({
      type: 'payout',
      amount,
      description,
      category: 'payout',
      eventType
    });
  };

  // Get user transactions
  const getUserTransactions = async () => {
    try {
      if (!hasFirestore() || !auth.currentUser) return;

      setLoading(true);
      const transactionsRef = collection(db, 'transactions');
      const q = query(
        transactionsRef,
        where('uid', '==', auth.currentUser.uid),
        orderBy('createdAt', 'desc')
      );

      const querySnapshot = await getDocs(q);

      const userTransactions = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));

      setTransactions(userTransactions);
    } catch (err) {
      console.error('Get transactions error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const value = {
    transactions,
    loading,
    error,
    addTransaction,
    addPremiumTransaction,
    addPayoutTransaction,
    getUserTransactions
  };

  return (
    <TransactionContext.Provider value={value}>
      {children}
    </TransactionContext.Provider>
  );
};
