import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  StatusBar,
  TouchableOpacity,
  Alert,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, TRIAL_CONFIG } from '../utils/constants';
import Logo from '../components/Logo';
import Button from '../components/Button';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';

const PaymentScreen = ({ navigation, route }) => {
  const [paymentMethod, setPaymentMethod] = useState('upi');
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();

  const selectedPlan = route?.params?.selectedPlan || null;
  const premiumSummary = route?.params?.premiumSummary || null;

  const baselineIncome = Math.round(premiumSummary?.baselineIncome || 4000);
  const basePremium = Math.round(premiumSummary?.weeklyEstimate || TRIAL_CONFIG.PREMIUM);
  const gstAmount = Math.round(basePremium * TRIAL_CONFIG.GST_RATE);
  const totalAmount = basePremium + gstAmount;
  const coverageAmount = selectedPlan
    ? Math.round(baselineIncome * ((premiumSummary?.coveragePercent || selectedPlan.coverage || 35) / 100))
    : TRIAL_CONFIG.COVERAGE_WEEKLY;
  const planTitle = selectedPlan ? selectedPlan.name : 'Trial';

  const handlePayment = async () => {
    if (!user) {
      Alert.alert('Error', 'User not authenticated');
      return;
    }

    setLoading(true);

    setTimeout(() => {
      navigation.navigate('PaymentSuccess', {
        selectedPlan,
        totalAmount,
        coverageAmount,
      });
      setLoading(false);
    }, 1200);
  };

  const paymentMethods = [
    { id: 'upi', name: 'UPI / GPay', icon: 'phone-portrait-outline' },
    { id: 'netbanking', name: 'Net Banking', icon: 'card-outline' },
    { id: 'card', name: 'Debit / Credit Card', icon: 'card-outline' }
  ];

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        <View style={styles.content}>
          <Logo size="medium" />

          <Card style={styles.card}>
            <View style={styles.progressContainer}>
              <View style={[styles.progressDot, styles.activeDot]} />
              <View style={[styles.progressDot, styles.activeDot]} />
              <View style={[styles.progressDot, styles.activeDot]} />
            </View>

            <View style={styles.headerContainer}>
              <View style={styles.iconContainer}>
                <Ionicons name="card-outline" size={24} color={COLORS.primary} />
              </View>
              <Text style={styles.headerTitle}>PAYMENT</Text>
            </View>

            <Text style={styles.title}>Pay For Your {planTitle} Plan</Text>
            <Text style={styles.subtitle}>
              Your premium is now calculated from your income profile and selected insurance tier.
            </Text>

            <View style={styles.planSummaryCard}>
              <View style={styles.planSummaryRow}>
                <Text style={styles.planSummaryLabel}>Selected Tier</Text>
                <Text style={styles.planSummaryValue}>{planTitle}</Text>
              </View>
              <View style={styles.planSummaryRow}>
                <Text style={styles.planSummaryLabel}>Baseline Weekly Income</Text>
                <Text style={styles.planSummaryValue}>₹{baselineIncome.toLocaleString()}</Text>
              </View>
              <View style={styles.planSummaryRow}>
                <Text style={styles.planSummaryLabel}>Weekly Coverage</Text>
                <Text style={styles.planSummaryValue}>₹{coverageAmount.toLocaleString()}</Text>
              </View>
              {selectedPlan && (
                <View style={styles.planSummaryRow}>
                  <Text style={styles.planSummaryLabel}>Premium Rate</Text>
                  <Text style={styles.planSummaryValue}>{selectedPlan.premiumRate}</Text>
                </View>
              )}
            </View>

            <View style={styles.pricingContainer}>
              <View style={styles.pricingRow}>
                <Text style={styles.pricingLabel}>Dynamic Premium</Text>
                <Text style={styles.pricingValue}>₹{basePremium}</Text>
              </View>
              <View style={styles.pricingRow}>
                <Text style={styles.pricingLabel}>GST</Text>
                <Text style={styles.pricingValue}>₹{gstAmount}</Text>
              </View>
              <View style={[styles.pricingRow, styles.totalRow]}>
                <Text style={styles.totalLabel}>Total</Text>
                <Text style={styles.totalValue}>₹{totalAmount}</Text>
              </View>
            </View>

            <View style={styles.paymentMethodsContainer}>
              <Text style={styles.sectionTitle}>Select Payment Method</Text>
              {paymentMethods.map((method) => (
                <TouchableOpacity
                  key={method.id}
                  style={[styles.paymentMethod, paymentMethod === method.id && styles.selectedMethod]}
                  onPress={() => setPaymentMethod(method.id)}
                >
                  <View style={styles.paymentMethodLeft}>
                    <View style={[styles.radioButton, paymentMethod === method.id && styles.radioButtonSelected]}>
                      {paymentMethod === method.id && <View style={styles.radioButtonInner} />}
                    </View>
                    <Ionicons name={method.icon} size={20} color={COLORS.primary} />
                  </View>
                  <Text style={styles.paymentMethodText}>{method.name}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </Card>

          <Button
            title={`Pay ₹${totalAmount}`}
            onPress={handlePayment}
            loading={loading}
            style={styles.payButton}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollContent: {
    paddingBottom: 32,
  },
  content: {
    paddingHorizontal: 24,
    paddingTop: 20,
    paddingBottom: 20,
  },
  card: {
    marginTop: 16,
    marginBottom: 16,
  },
  progressContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 16,
  },
  progressDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.lightGrey,
    marginHorizontal: 4,
  },
  activeDot: {
    backgroundColor: COLORS.primary,
  },
  headerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: `${COLORS.primary}20`,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  headerTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: COLORS.black,
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 16,
    color: COLORS.grey,
    marginBottom: 20,
    lineHeight: 22,
  },
  planSummaryCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
  planSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  planSummaryLabel: {
    fontSize: 14,
    color: COLORS.grey,
    fontWeight: '500',
  },
  planSummaryValue: {
    fontSize: 14,
    color: COLORS.black,
    fontWeight: '600',
  },
  pricingContainer: {
    backgroundColor: COLORS.background,
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  pricingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 6,
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: COLORS.lightGrey,
    paddingTop: 12,
    marginTop: 6,
  },
  pricingLabel: {
    fontSize: 16,
    color: COLORS.grey,
    fontWeight: '500',
  },
  pricingValue: {
    fontSize: 16,
    color: COLORS.black,
    fontWeight: '600',
  },
  totalLabel: {
    fontSize: 18,
    color: COLORS.black,
    fontWeight: '700',
  },
  totalValue: {
    fontSize: 18,
    color: COLORS.primary,
    fontWeight: '700',
  },
  paymentMethodsContainer: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 12,
  },
  paymentMethod: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: COLORS.lightGrey,
    marginBottom: 8,
    backgroundColor: COLORS.white,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 1,
  },
  selectedMethod: {
    borderColor: COLORS.primary,
    borderWidth: 2,
    backgroundColor: `${COLORS.primary}10`,
    shadowColor: COLORS.primary,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  paymentMethodLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  radioButton: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: COLORS.lightGrey,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  radioButtonSelected: {
    borderColor: COLORS.primary,
  },
  radioButtonInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: COLORS.primary,
  },
  paymentMethodText: {
    fontSize: 14,
    color: COLORS.black,
    marginLeft: 12,
  },
  payButton: {
    marginTop: 8,
    marginBottom: 12,
    backgroundColor: COLORS.primary,
  },
});

export default PaymentScreen;
