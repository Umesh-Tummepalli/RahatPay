# RahatPay Mobile App - Setup Instructions

## Issues Fixed
1. ✅ **Expo Go Version Incompatibility** - Downgraded from Expo SDK 51 to SDK 50
2. ✅ **Infinite Loading Screen** - Fixed AuthContext timeout and added fallback to mock auth

## Quick Start

### Step 1: Install Dependencies
```bash
cd c:\Users\umesh\Documents\RahatPay\module4-mobile-app\Rahat-Pay\Rahat-Pay
npm install
```

### Step 2: Start the App
```bash
npm start
```

### Step 3: Run on Your Phone
- **Option A:** Scan the QR code with Expo Go app
- **Option B:** Press `a` for Android emulator
- **Option C:** Press `i` for iOS simulator

## Important Notes

### Expo Go App Version
- The app now uses **Expo SDK 50** which is compatible with older Expo Go versions
- If you still see version incompatibility, update Expo Go from Play Store

### Firebase Configuration
- The app will work in **demo mode** even without Firebase
- To use real Firebase auth, update `src/utils/constants.js` with your Firebase config

### Backend Connection
- The app works standalone with mock data
- To connect to real backend, ensure Module 1 (port 8001) and Module 3 (port 8003) are running

## Troubleshooting

### Still seeing infinite loading?
1. Clear app cache: `npm start -- --clear`
2. Delete `node_modules` and reinstall: `rm -rf node_modules && npm install`
3. Check Metro bundler logs for errors

### Expo Go version error?
1. Update Expo Go from Play Store/App Store
2. Or use development build: `npx expo run:android`

### Firebase connection issues?
- App automatically falls back to mock auth if Firebase is unavailable
- Check `src/services/firebase.js` for initialization errors in console
