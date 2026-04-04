import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  StatusBar,
  ScrollView
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, TRIAL_CONFIG } from '../utils/constants';
import Logo from '../components/Logo';
import Button from '../components/Button';
import Card from '../components/Card';

const PaymentSuccessScreen = ({ navigation, route }) => {
  const selectedPlan = route?.params?.selectedPlan || null;
  const totalAmount = route?.params?.totalAmount || Math.round(TRIAL_CONFIG.PREMIUM * (1 + TRIAL_CONFIG.GST_RATE));
  const coverageAmount = route?.params?.coverageAmount || TRIAL_CONFIG.COVERAGE_WEEKLY;

  const handleGoToDashboard = () => {
    navigation.navigate('Main');
  };

  const generatePolicyId = () => {
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    return `RP-${year}-${month}${day}-${random}`;
  };

  const expiryDate = new Date();
  expiryDate.setDate(expiryDate.getDate() + 30);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Logo size="medium" />

        <Card style={styles.successCard}>
          <View style={styles.successIconContainer}>
            <View style={styles.successIcon}>
              <Ionicons name="checkmark" size={48} color={COLORS.white} />
            </View>
          </View>

          <Text style={styles.successTitle}>Payment Successful!</Text>
          <Text style={styles.successSubtitle}>
            Your {selectedPlan?.name || 'coverage'} plan is now active.
          </Text>

          <View style={styles.coverageHighlight}>
            <Text style={styles.coverageText}>₹{coverageAmount.toLocaleString()}/week covered</Text>
          </View>

          <View style={styles.detailsCard}>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Policy ID</Text>
              <Text style={styles.detailValue}>{generatePolicyId()}</Text>
            </View>

            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Plan</Text>
              <Text style={styles.detailValue}>{selectedPlan?.name || 'Trial'}</Text>
            </View>

            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Amount Paid</Text>
              <Text style={styles.detailValue}>₹{totalAmount}</Text>
            </View>

            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Expiry Date</Text>
              <Text style={styles.expiryValue}>
                {expiryDate.toLocaleDateString('en-IN', {
                  day: 'numeric',
                  month: 'short',
                  year: 'numeric'
                })}
              </Text>
            </View>
          </View>

          <Button
            title="Go to Dashboard"
            onPress={handleGoToDashboard}
            style={styles.dashboardButton}
          />
        </Card>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingTop: 40,
    paddingBottom: 20,
    justifyContent: 'center',
  },
  successCard: {
    borderRadius: 24,
    padding: 32,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 8,
  },
  successIconContainer: {
    marginBottom: 24,
  },
  successIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  successTitle: {
    fontSize: 28,
    fontWeight: '700',
    color: COLORS.black,
    textAlign: 'center',
    marginBottom: 8,
  },
  successSubtitle: {
    fontSize: 16,
    color: COLORS.grey,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 22,
  },
  coverageHighlight: {
    backgroundColor: `${COLORS.primary}15`,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 20,
    marginBottom: 32,
  },
  coverageText: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.primary,
    textAlign: 'center',
  },
  detailsCard: {
    backgroundColor: COLORS.lightGrey,
    borderRadius: 20,
    padding: 20,
    width: '100%',
    marginBottom: 32,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  detailLabel: {
    fontSize: 14,
    color: COLORS.grey,
    fontWeight: '500',
  },
  detailValue: {
    fontSize: 14,
    color: COLORS.black,
    fontWeight: '600',
  },
  expiryValue: {
    fontSize: 14,
    color: COLORS.primary,
    fontWeight: '600',
  },
  dashboardButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 25,
    paddingVertical: 16,
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  }
});

export default PaymentSuccessScreen;
