import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  StatusBar,
  ActivityIndicator
} from 'react-native';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import { useAuth } from '../context/AuthContext';

const SplashScreen = ({ navigation }) => {
  const { user } = useAuth();
  const hasNavigated = useRef(false);
  const timerRef = useRef(null);

  useEffect(() => {
    // Only run once on mount
    if (hasNavigated.current || timerRef.current) return;

    // Fixed 2-second splash screen - ALWAYS navigates after 2 seconds
    timerRef.current = setTimeout(() => {
      hasNavigated.current = true;
      timerRef.current = null;

      // Navigate based on current user state
      if (user) {
        navigation.replace('Main');
      } else {
        navigation.replace('Auth');
      }
    }, 2000);

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []); // Empty dependency array - runs only once on mount

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />

      <View style={styles.content}>
        <View style={styles.logoContainer}>
          <Logo size="large" />
        </View>

        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color={COLORS.primary} />
          <Text style={styles.loadingText}>
            Loading RahatPay...
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  logoContainer: {
    marginBottom: 40,
  },
  textContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: COLORS.primary,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.grey,
    textAlign: 'center',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loadingText: {
    marginLeft: 10,
    color: COLORS.grey,
    fontSize: 14,
  }
});

export default SplashScreen;
