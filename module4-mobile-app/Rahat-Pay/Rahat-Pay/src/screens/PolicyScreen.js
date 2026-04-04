import React from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  StatusBar, 
  ScrollView,
  TouchableOpacity
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Card from '../components/Card';

const PolicyScreen = ({ navigation }) => {
  const handleExplorePlans = () => {
    navigation.navigate('Plans');
  };

  // Mock policy data
  const mockPolicy = {
    type: 'trial',
    status: 'active',
    startDate: new Date(),
    endDate: new Date(Date.now() + 15 * 24 * 60 * 60 * 1000),
    coverage: 4000,
    coverageRemaining: 4000,
    premium: 100,
    policyNumber: 'RP-2026-0330-123',
    weeklyPremium: 142,
    autoRenewal: true,
    paymentMethod: 'UPI',
    nextBillingDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
  };

  const getDaysRemaining = () => {
    const expiryDate = new Date(mockPolicy.endDate);
    const currentDate = new Date();
    const diffTime = expiryDate - currentDate;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays);
  };

  const getFormattedDate = (date) => {
    return date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const parametricTriggers = [
    { type: 'Heavy Rain', amount: 800, icon: 'rainy' },
    { type: 'Flood Alert', amount: 1200, icon: 'water' },
    { type: 'AQI Hazard', amount: 600, icon: 'warning' },
    { type: 'Cyclone Warning', amount: 1500, icon: 'thunderstorm' }
  ];

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Logo size="tiny" />
            <View style={styles.headerText}>
              <Text style={styles.headerTitle}>My Coverage</Text>
              <Text style={styles.headerSubtitle}>Policy</Text>
            </View>
          </View>

          {/* Policy Status Card */}
          <Card style={styles.policyStatusCard}>
            <View style={styles.policyStatusHeader}>
              <Text style={styles.policyStatusTitle}>RAHATPAY INSURANCE</Text>
              <View style={styles.trialBadge}>
                <Text style={styles.trialBadgeText}>Trial Active</Text>
              </View>
            </View>
            
            <View style={styles.daysRemaining}>
              <Text style={styles.daysNumber}>{getDaysRemaining()}</Text>
              <Text style={styles.daysText}>Days Left</Text>
            </View>
          </Card>

          {/* Renewals Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Renewals</Text>
            <Card style={styles.renewalsCard}>
              <View style={styles.renewalRow}>
                <Text style={styles.renewalLabel}>Next Renewal Date</Text>
                <Text style={styles.renewalDate}>{getFormattedDate(mockPolicy.endDate)}</Text>
              </View>
              
              <View style={styles.renewalRow}>
                <Text style={styles.renewalLabel}>Weekly Premium</Text>
                <Text style={styles.renewalAmount}>₹{mockPolicy.weeklyPremium}</Text>
              </View>
              
              <View style={styles.renewalRow}>
                <Text style={styles.renewalLabel}>Auto-renewal Status</Text>
                <Text style={styles.renewalStatus}>Enabled</Text>
              </View>
              
              <View style={styles.infoCard}>
                <Text style={styles.infoText}>
                  After trial period, your policy will auto-calculate premium based on your delivery zones and risk profile
                </Text>
              </View>
            </Card>
          </View>

          {/* Current Plan Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Current Plan</Text>
            <Card style={styles.currentPlanCard}>
              <View style={styles.planTypeCard}>
                <View style={styles.planTypeHeader}>
                  <View style={styles.planBadge}>
                    <Text style={styles.planBadgeText}>TRIAL</Text>
                  </View>
                  <Text style={styles.planType}>Standard Period</Text>
                </View>
                <Text style={styles.planDescription}>
                  Basic coverage for weather-related disruptions and air quality issues
                </Text>
              </View>
              
              <View style={styles.planDetails}>
                <View style={styles.planRow}>
                  <Text style={styles.planLabel}>Coverage</Text>
                  <Text style={styles.planValue}>₹{mockPolicy.coverage.toLocaleString()}/week</Text>
                </View>
                
                <View style={styles.planRow}>
                  <Text style={styles.planLabel}>Duration</Text>
                  <Text style={styles.planValue}>15 days</Text>
                </View>
                
                <View style={styles.planRow}>
                  <Text style={styles.planLabel}>Premium Paid</Text>
                  <Text style={styles.planValue}>₹{mockPolicy.premium}</Text>
                </View>
                
                <View style={styles.planRow}>
                  <Text style={styles.planLabel}>Coverage Remaining</Text>
                  <Text style={styles.planValueHighlight}>₹{mockPolicy.coverageRemaining.toLocaleString()}</Text>
                </View>
                
                <View style={styles.planRow}>
                  <Text style={styles.planLabel}>Expiry</Text>
                  <Text style={styles.planValue}>{getFormattedDate(mockPolicy.endDate)}</Text>
                </View>
                
                <View style={styles.planRow}>
                  <Text style={styles.planLabel}>Auto-upgrade</Text>
                  <Text style={styles.planValue}>Yes</Text>
                </View>
              </View>
              
              <TouchableOpacity style={styles.ctaButton} onPress={handleExplorePlans}>
                <Text style={styles.ctaButtonText}>Explore Post-Trial Plans</Text>
              </TouchableOpacity>
            </Card>
          </View>

          {/* Parametric Triggers Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Parametric Triggers</Text>
            <Card style={styles.triggersCard}>
              {parametricTriggers.map((trigger, index) => (
                <View key={index} style={styles.triggerItem}>
                  <View style={styles.triggerInfo}>
                    <Ionicons name={trigger.icon} size={20} color={COLORS.primary} />
                    <Text style={styles.triggerName}>{trigger.type}</Text>
                  </View>
                  <Text style={styles.triggerAmount}>Up to ₹{trigger.amount}</Text>
                </View>
              ))}
            </Card>
          </View>

          {/* Payment Info Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Payment Info</Text>
            <Card style={styles.paymentCard}>
              <View style={styles.paymentRow}>
                <Text style={styles.paymentLabel}>Upcoming Deduction</Text>
                <Text style={styles.paymentDate}>{getFormattedDate(mockPolicy.nextBillingDate)}</Text>
              </View>
              
              <View style={styles.paymentRow}>
                <Text style={styles.paymentLabel}>Estimated Amount</Text>
                <Text style={styles.paymentAmount}>₹{mockPolicy.weeklyPremium}</Text>
              </View>
              
              <View style={styles.paymentRow}>
                <Text style={styles.paymentLabel}>Payment Method</Text>
                <Text style={styles.paymentMethod}>{mockPolicy.paymentMethod}</Text>
              </View>
              
              <View style={styles.paymentRow}>
                <Text style={styles.paymentLabel}>Next Billing</Text>
                <Text style={styles.paymentStatus}>Auto-debit</Text>
              </View>
            </Card>
          </View>
        </View>
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
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  headerText: {
    marginLeft: 12,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.black,
  },
  headerSubtitle: {
    fontSize: 14,
    color: COLORS.grey,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  
  // Policy Status Card
  policyStatusCard: {
    backgroundColor: '#1B5E20',
    borderRadius: 24,
    padding: 24,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 6,
  },
  policyStatusHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  policyStatusTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.white,
  },
  trialBadge: {
    backgroundColor: `${COLORS.white}30`,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  trialBadgeText: {
    color: COLORS.white,
    fontSize: 12,
    fontWeight: '600',
  },
  daysRemaining: {
    alignItems: 'center',
  },
  daysNumber: {
    fontSize: 32,
    fontWeight: '700',
    color: COLORS.white,
  },
  daysText: {
    fontSize: 14,
    color: `${COLORS.white}80`,
  },
  
  // Renewals Card
  renewalsCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  renewalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  renewalLabel: {
    fontSize: 14,
    color: COLORS.grey,
  },
  renewalDate: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.success,
  },
  renewalAmount: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  renewalStatus: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.success,
  },
  infoCard: {
    backgroundColor: `${COLORS.primary}20`,
    borderRadius: 12,
    padding: 12,
    marginTop: 12,
  },
  infoText: {
    fontSize: 12,
    color: COLORS.grey,
    lineHeight: 16,
  },
  
  // Current Plan Card
  currentPlanCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  planTypeCard: {
    backgroundColor: `${COLORS.primary}20`,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 0,
  },
  planTypeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  planBadge: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    marginRight: 8,
  },
  planBadgeText: {
    color: COLORS.white,
    fontSize: 10,
    fontWeight: '600',
  },
  planType: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  planDescription: {
    fontSize: 12,
    color: COLORS.grey,
    lineHeight: 16,
  },
  planDetails: {
    marginBottom: 20,
  },
  planRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  planLabel: {
    fontSize: 14,
    color: COLORS.grey,
  },
  planValue: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  planValueHighlight: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.success,
  },
  ctaButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  ctaButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
  },
  
  // Parametric Triggers Card
  triggersCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  triggerItem: {
    backgroundColor: `${COLORS.primary}20`,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 0,
  },
  triggerInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  triggerName: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
    marginLeft: 8,
  },
  triggerAmount: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.success,
  },
  
  // Payment Info Card
  paymentCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  paymentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
  },
  paymentLabel: {
    fontSize: 14,
    color: COLORS.grey,
  },
  paymentDate: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  paymentAmount: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  paymentMethod: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  paymentStatus: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.success,
  },
});

export default PolicyScreen;
