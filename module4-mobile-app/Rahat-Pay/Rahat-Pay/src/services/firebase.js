import { initializeApp, getApps, getApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { firebaseConfig } from '../utils/constants';

let app;
let auth;
let db;

try {
  app = getApps().length ? getApp() : initializeApp(firebaseConfig);
  auth = getAuth(app);
  db = getFirestore(app);
  console.log('Firebase initialized successfully');
} catch (error) {
  console.warn('Firebase initialization warning:', error?.message || error);
  app = null;
  auth = null;
  db = null;
}

export { auth, db };
export default app;
