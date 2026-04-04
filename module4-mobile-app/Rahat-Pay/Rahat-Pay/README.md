# RahatPay - Delivery Rider Insurance App

A complete React Native mobile application for delivery riders that implements AI-powered parametric insurance with Firebase integration.

## Features

### 🔐 Authentication
- Email/Password login
- Phone OTP authentication
- Google Sign-In integration
- Firebase Authentication backend

### 🧾 KYC Verification
- Aadhaar number validation
- PAN card verification
- Masked data storage
- DigiLocker integration ready

### 📊 Trial System
- 15-day free trial period
- ₹4,000 weekly coverage
- ₹100 one-time premium
- Automatic policy activation

### 💳 Payment Integration
- Razorpay payment gateway
- Multiple payment methods (UPI, Net Banking, Cards)
- GST calculation
- Real-time payment verification

### 🏠 Home Dashboard
- Active policy status
- Coverage remaining indicator
- Premium breakdown visualization
- Trust score display
- Recent transactions
- DEV MODE for testing

### 📄 Policy Management
- Trial/Paid plan status
- Days remaining counter
- Auto-renewal settings
- Coverage details
- Policy terms

### 💸 Transaction Tracking
- Summary view with totals
- Coverage usage analytics
- Transaction history
- Plan details
- Event-based payouts

### 🆘 Help & Support
- Relationship manager contact
- 24/7 support availability
- FAQ section
- Quick actions
- Policy management options

### 📦 Post-Trial Plans
- Kavach (80% coverage, 1.0% premium)
- Suraksha (90% coverage, 1.8% premium)  
- Raksha (100% coverage, 2.5% premium)
- Personalized pricing based on data

### 🔔 Push Notifications
- Firebase Cloud Messaging
- Event detection alerts
- Payout notifications
- Policy updates

### ⚙️ DEV MODE Features
- Skip trial option
- Mock event triggers (Flood, Rain)
- Coverage deduction simulation
- Instant transaction updates

## Tech Stack

### Frontend
- **React Native** with Expo
- **React Navigation** (Stack + Bottom Tabs)
- **Context API** for state management
- **Firebase SDK** for backend services

### Backend Services
- **Firebase Authentication** - User management
- **Firebase Firestore** - Database
- **Firebase Cloud Messaging** - Push notifications
- **Razorpay** - Payment processing

### Development Tools
- **Expo CLI** - Development and building
- **Babel** - JavaScript transpilation
- **ESLint** - Code linting

## Design System

### Colors
- Background: `#E3EED4` (whitish)
- Primary: `#6B9071` (Green)
- Text: Black, White, Grey only
- Apple-style minimal UI

### Typography
- Clean, medium-bold headings
- Subtle secondary text
- Consistent font hierarchy

### UI Components
- Large cards with 20px+ rounded corners
- Minimal, clean design
- Smooth transitions

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── Button.js
│   ├── Card.js
│   ├── Input.js
│   ├── Header.js
│   ├── Logo.js
│   └── TabIcon.js
├── context/             # Global state management
│   ├── AuthContext.js
│   ├── PolicyContext.js
│   └── TransactionContext.js
├── screens/             # App screens
│   ├── SplashScreen.js
│   ├── AuthScreen.js
│   ├── KYCVerificationScreen.js
│   ├── TrialIntroScreen.js
│   ├── PaymentScreen.js
│   ├── PaymentSuccessScreen.js
│   ├── HomeDashboard.js
│   ├── PolicyScreen.js
│   ├── TransactionScreen.js
│   ├── HelpDeskScreen.js
│   └── PlanSelectionScreen.js
├── services/            # API and Firebase services
│   ├── firebase.js
│   ├── authService.js
│   ├── policyService.js
│   ├── transactionService.js
│   ├── kycService.js
│   └── apiService.js
├── hooks/               # Custom React hooks
│   └── useNotifications.js
├── utils/               # Utility functions
│   ├── constants.js
│   └── validation.js
└── assets/              # Static assets
```

## Getting Started

### Prerequisites
- Node.js 16+
- Expo CLI
- Firebase project
- Razorpay test account

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd RahatPay
```

2. Install dependencies
```bash
npm install
```

3. Set up Firebase
   - Create a new Firebase project
   - Enable Authentication, Firestore, and Cloud Messaging
   - Download configuration and update `src/utils/constants.js`

4. Set up Razorpay
   - Create a Razorpay test account
   - Get test API keys
   - Update `src/utils/constants.js`

5. Start the development server
```bash
npm start
```

6. Run the app
```bash
# For Android
npm run android

# For iOS
npm run ios

# For Web
npm run web
```

## Configuration

### Firebase Setup
1. Enable Authentication providers (Email, Phone, Google)
2. Set up Firestore database
3. Configure Cloud Messaging
4. Update `firebaseConfig` in `src/utils/constants.js`

### Razorpay Setup
1. Get test API keys from Razorpay dashboard
2. Update `PAYMENT_CONFIG` in `src/utils/constants.js`

### Environment Variables
Create a `.env` file for sensitive configuration:
```env
FIREBASE_API_KEY=your_api_key
FIREBASE_AUTH_DOMAIN=your_domain
FIREBASE_PROJECT_ID=your_project_id
RAZORPAY_KEY_ID=your_razorpay_key
```

## App Flow

1. **Splash Screen** → Show logo and navigation
2. **Authentication** → Login/Signup with Firebase
3. **KYC Verification** → Document submission and verification
4. **Trial Introduction** → Plan overview and terms
5. **Payment** → Razorpay integration for premium payment
6. **Dashboard** → Main app interface with real-time updates
7. **Policy Management** → View and manage insurance policies
8. **Transactions** → Track payouts and premiums
9. **Help Desk** → Support and quick actions
10. **Plan Selection** → Post-trial plan upgrade

## DEV MODE

Enable DEV MODE for testing features:
- Tap the top-right corner of the dashboard
- Trigger mock events (Flood, Rain)
- Skip trial period
- Simulate payouts

## API Integration

The app uses a mock API structure that can be easily replaced with a real backend:
- Toggle `useMock` in `src/services/apiService.js`
- Implement real endpoints in your backend
- The app structure is ready for FastAPI integration

## Security Features

- Firebase Authentication for secure user management
- Encrypted data storage in Firestore
- Masked sensitive information (Aadhaar, PAN)
- Secure payment processing with Razorpay
- Push notification encryption

## Testing

### Manual Testing
1. Complete full user flow from signup to dashboard
2. Test payment integration with Razorpay test mode
3. Verify push notifications
4. Test DEV MODE features

### Automated Testing
```bash
# Run tests
npm test

# Run linting
npm run lint
```

## Deployment

### Expo Build
```bash
# Build for Android
expo build:android

# Build for iOS
expo build:ios
```

### Store Submission
- Prepare app screenshots and descriptions
- Configure app store listings
- Submit to Google Play Store and Apple App Store

## Contributing

1. Follow the existing code style
2. Use TypeScript for new components
3. Add proper error handling
4. Update documentation
5. Test thoroughly

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Email: support@rahatpay.com
- Phone: 1800-123-4567
- In-app help desk

---

**RahatPay** - Deliver with Confidence 🛡️
