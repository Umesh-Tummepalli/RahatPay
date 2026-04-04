import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  SafeAreaView, 
  StatusBar, 
  ScrollView,
  Modal,
  TouchableOpacity
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Button from '../components/Button';
import Card from '../components/Card';
import { TRIAL_CONFIG } from '../utils/constants';

const TrialIntroScreen = ({ navigation }) => {
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  const features = [
    {
      icon: 'location-outline',
      color: '#FF6B6B',
      title: 'We collect location & work data',
      description: 'to understand your delivery patterns'
    },
    {
      icon: 'wallet-outline',
      color: '#FFD93D',
      title: 'You get ₹4,000 weekly protection',
      description: 'during the trial'
    },
    {
      icon: 'target-outline',
      color: '#FF6B9D',
      title: 'Fixed premium of ₹100',
      description: 'for the full 15-day period'
    },
    {
      icon: 'bar-chart-outline',
      color: '#4ECDC4',
      title: 'Data used only for personalized pricing',
      description: 'accuracy'
    },
    {
      icon: 'rocket-outline',
      color: '#FF4757',
      title: 'After trial → personalized plans',
      description: 'unlocked just for you'
    }
  ];

  const PolicyTermsModal = () => (
    <Modal
      visible={showPolicyModal}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={() => setShowPolicyModal(false)}
    >
      <SafeAreaView style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Policy Terms</Text>
          <TouchableOpacity onPress={() => setShowPolicyModal(false)}>
            <Ionicons name="close" size={24} color={COLORS.black} />
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.modalContent} showsVerticalScrollIndicator={false}>
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>Coverage</Text>
            <Text style={styles.termsText}>
              ₹4,000 per week during the 15-day trial period.
            </Text>
          </View>
          
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>Premium</Text>
            <Text style={styles.termsText}>
              ₹100 one-time payment for the standard period.
            </Text>
          </View>
          
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>Data Usage</Text>
            <Text style={styles.termsText}>
              Location, work hours, and zone data collected to personalize future premiums.
            </Text>
          </View>
          
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>Parametric Triggers</Text>
            <Text style={styles.termsText}>
              Automatic payouts triggered by heavy rain, floods, AQI spikes, and cyclone alerts.
            </Text>
          </View>
          
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>Auto-Upgrade</Text>
            <Text style={styles.termsText}>
              Personalized plans unlocked after the trial ends, based on delivery data.
            </Text>
          </View>
          
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>No Refund Policy</Text>
            <Text style={styles.termsText}>
              Trial premium of ₹100 is non-refundable once paid.
            </Text>
          </View>
          
          <View style={styles.termsSection}>
            <Text style={styles.termsTitle}>Privacy</Text>
            <Text style={styles.termsText}>
              All data encrypted and used only for pricing accuracy, never shared with third parties.
            </Text>
          </View>
        </ScrollView>
        
        <View style={styles.modalFooter}>
          <Button
            title="Got It"
            onPress={() => setShowPolicyModal(false)}
            style={styles.modalButton}
          />
        </View>
      </SafeAreaView>
    </Modal>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          <Logo size="medium" />
          
          <Card style={styles.card}>
            <View style={styles.progressContainer}>
              <View style={[styles.progressDot, styles.activeDot]} />
              <View style={[styles.progressDot, styles.activeDot]} />
              <View style={styles.progressDot} />
            </View>
            
            <View style={styles.headerContainer}>
              <View style={styles.iconContainer}>
                <Ionicons name="shield-checkmark" size={24} color={COLORS.primary} />
              </View>
              <Text style={styles.headerTitle}>TRIAL PERIOD</Text>
            </View>
            
            <Text style={styles.title}>Start Your 15-Day Standard Period</Text>
            <Text style={styles.subtitle}>Here's what happens during your trial:</Text>
            
            <View style={styles.featuresContainer}>
              {features.map((feature, index) => (
                <View key={index} style={styles.featureCard}>
                  <View style={[styles.featureIcon, { backgroundColor: `${feature.color}20` }]}>
                    <Ionicons name={feature.icon} size={24} color={feature.color} />
                  </View>
                  <View style={styles.featureContent}>
                    <Text style={styles.featureTitle}>{feature.title}</Text>
                    <Text style={styles.featureDescription}>{feature.description}</Text>
                  </View>
                </View>
              ))}
            </View>
          </Card>
          
          <View style={styles.summaryBar}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Weekly Coverage</Text>
              <Text style={styles.summaryValue}>₹{TRIAL_CONFIG.COVERAGE_WEEKLY.toLocaleString()}</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Trial Premium</Text>
              <Text style={styles.summaryValue}>₹{TRIAL_CONFIG.PREMIUM}</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>Duration</Text>
              <Text style={styles.summaryValue}>{TRIAL_CONFIG.DURATION_DAYS}d</Text>
            </View>
          </View>
          
          <View style={styles.termsContainer}>
            <TouchableOpacity 
              style={styles.checkboxContainer}
              onPress={() => setAgreedToTerms(!agreedToTerms)}
            >
              <View style={[styles.checkbox, agreedToTerms && styles.checkboxChecked]}>
                {agreedToTerms && <Ionicons name="checkmark" size={12} color={COLORS.white} />}
              </View>
              <Text style={styles.termsText}>I agree to terms & data usage</Text>
            </TouchableOpacity>
          </View>
          
          <View style={styles.buttonContainer}>
            <Button
              title="View Policy"
              onPress={() => setShowPolicyModal(true)}
              variant="outline"
              style={styles.policyButton}
            />
            
            <Button
              title="Analyze My Income"
              onPress={() => agreedToTerms && navigation.navigate('IncomeProfiler')}
              disabled={!agreedToTerms}
              style={styles.payButton}
            />
          </View>
        </View>
      </ScrollView>
      
      <PolicyTermsModal />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
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
  },
  featuresContainer: {
    marginBottom: 20,
  },
  featureCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    backgroundColor: COLORS.lightGrey,
    padding: 12,
    borderRadius: 12,
  },
  featureIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  featureContent: {
    flex: 1,
  },
  featureTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 4,
  },
  featureDescription: {
    fontSize: 14,
    color: COLORS.grey,
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  policyButton: {
    flex: 1, // Take up half the space
    marginBottom: 0, // Remove bottom margin since they're in a row
  },
  payButton: {
    flex: 1, // Take up half the space
    marginBottom: 0, // Remove bottom margin since they're in a row
  },
  summaryBar: {
    flexDirection: 'row',
    backgroundColor: '#6B9071', // Green background like Version 1
    borderRadius: 20,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 5,
    marginBottom: 20,
  },
  summaryItem: {
    flex: 1,
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#FFFFFF', // White text for green background
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF', // White text for green background
  },
  termsContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    marginBottom: 20,
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkbox: {
    width: 20,
    height: 20,
    borderWidth: 2,
    borderColor: COLORS.grey,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  checkboxChecked: {
    backgroundColor: COLORS.primary,
    borderColor: COLORS.primary,
  },
  termsText: {
    fontSize: 14,
    color: COLORS.grey,
    flex: 1,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: COLORS.white,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGrey,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: COLORS.black,
  },
  modalContent: {
    flex: 1,
    padding: 20,
  },
  termsSection: {
    marginBottom: 24,
  },
  termsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 8,
  },
  termsText: {
    fontSize: 16,
    color: COLORS.grey,
    lineHeight: 24,
  },
  modalFooter: {
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: COLORS.lightGrey,
  },
  modalButton: {
    marginBottom: 20,
  },
});

export default TrialIntroScreen;
