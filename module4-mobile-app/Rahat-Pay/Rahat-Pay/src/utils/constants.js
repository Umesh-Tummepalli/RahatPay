// Firebase configuration (Replace with your real credentials from Firebase console)
export const firebaseConfig = {
  apiKey: "AIzaSyBS_qARaAfZcuKbsnHZrerO7J2FnA6A9QI",
  authDomain: "rahatpay-app.firebaseapp.com",
  projectId: "rahatpay-app",
  storageBucket: "rahatpay-app.firebasestorage.app",
  appId: "1:98319350787:web:3b1d81a88706adbeb1a236"
};

// Design System Colors
export const COLORS = {
  background: '#E3EED4',
  primary: '#6B9071',
  white: '#FFFFFF',
  black: '#000000',
  grey: '#666666',
  lightGrey: '#F5F5F5',
  green: '#4CAF50',
  red: '#F44336',
  orange: '#FF9800',
  success: '#4CAF50',
  error: '#F44336'
};

// Screen Dimensions
export const SCREEN_WIDTH = 375;
export const SCREEN_HEIGHT = 812;

// API Endpoints (Mock)
export const API_ENDPOINTS = {
  USER: '/user',
  POLICY: '/policy',
  TRANSACTIONS: '/transactions',
  EVENTS: '/events'
};

// Trial Configuration
export const TRIAL_CONFIG = {
  DURATION_DAYS: 15,
  COVERAGE_WEEKLY: 4000,
  PREMIUM: 100,
  GST_RATE: 0.18
};

// Payment Configuration
export const PAYMENT_CONFIG = {
  RAZORPAY_KEY: 'rzp_test_1234567890',
  CURRENCY: 'INR'
};
