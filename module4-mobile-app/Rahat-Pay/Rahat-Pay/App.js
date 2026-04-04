import 'react-native-gesture-handler';
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { AuthProvider } from './src/context/AuthContext';
import { PolicyProvider } from './src/context/PolicyContext';
import { TransactionProvider } from './src/context/TransactionContext';

// Screens
import SplashScreen from './src/screens/SplashScreen';
import AuthScreen from './src/screens/AuthScreen';
import KYCVerificationScreen from './src/screens/KYCVerificationScreen';
import TrialIntroScreen from './src/screens/TrialIntroScreen';
import PaymentScreen from './src/screens/PaymentScreen';
import PaymentSuccessScreen from './src/screens/PaymentSuccessScreen';
import HomeDashboard from './src/screens/HomeDashboard';
import PolicyScreen from './src/screens/PolicyScreen';
import TransactionScreen from './src/screens/TransactionScreen';
import HelpDeskScreen from './src/screens/HelpDeskScreen';
import PlansScreen from './src/screens/PlansScreen';
import IncomeProfilerScreen from './src/screens/IncomeProfilerScreen';
import EarningsHistoryScreen from './src/screens/EarningsHistoryScreen';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

const MainTabs = () => (
  <Tab.Navigator
    screenOptions={{
      tabBarActiveTintColor: '#6B9071',
      tabBarInactiveTintColor: '#666',
      tabBarStyle: { backgroundColor: '#fff', borderTopWidth: 0, elevation: 10 },
      headerShown: false,
    }}
  >
    <Tab.Screen
      name="Home"
      component={HomeDashboard}
      options={{
        tabBarLabel: 'Home',
        tabBarIcon: ({ color, size }) => (
          <Ionicons name="home" size={size} color={color} />
        ),
      }}
    />
    <Tab.Screen
      name="Policy"
      component={PolicyScreen}
      options={{
        tabBarLabel: 'Policy',
        tabBarIcon: ({ color, size }) => (
          <Ionicons name="shield-checkmark" size={size} color={color} />
        ),
      }}
    />
    <Tab.Screen
      name="Transactions"
      component={TransactionScreen}
      options={{
        tabBarLabel: 'Transactions',
        tabBarIcon: ({ color, size }) => (
          <Ionicons name="receipt" size={size} color={color} />
        ),
      }}
    />
    <Tab.Screen
      name="HelpDesk"
      component={HelpDeskScreen}
      options={{
        tabBarLabel: 'Help Desk',
        tabBarIcon: ({ color, size }) => (
          <Ionicons name="help-circle" size={size} color={color} />
        ),
      }}
    />
  </Tab.Navigator>
);

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <PolicyProvider>
          <TransactionProvider>
            <NavigationContainer>
              <Stack.Navigator initialRouteName="Splash">
                <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false }} />
                <Stack.Screen name="Auth" component={AuthScreen} options={{ headerShown: false }} />
                <Stack.Screen name="KYC" component={KYCVerificationScreen} options={{ headerShown: false }} />
                <Stack.Screen name="TrialIntro" component={TrialIntroScreen} options={{ headerShown: false }} />
                <Stack.Screen name="Payment" component={PaymentScreen} options={{ headerShown: false }} />
                <Stack.Screen name="PaymentSuccess" component={PaymentSuccessScreen} options={{ headerShown: false }} />
                <Stack.Screen name="IncomeProfiler" component={IncomeProfilerScreen} options={{ headerShown: false }} />
                <Stack.Screen name="Plans" component={PlansScreen} options={{ headerShown: false }} />
                <Stack.Screen name="EarningsHistory" component={EarningsHistoryScreen} options={{ headerShown: false }} />
                <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
              </Stack.Navigator>
            </NavigationContainer>
          </TransactionProvider>
        </PolicyProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
