import React, { useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  StatusBar, 
  ScrollView,
  TouchableOpacity,
  Linking,
  Alert
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';

const HelpDeskScreen = ({ navigation }) => {
  const [expandedFaq, setExpandedFaq] = useState(null);
  const { signOut, isUsingMockAuth } = useAuth();

  const handleCallNow = () => {
    Linking.openURL('tel:+919876543210');
  };

  const handleChat = () => {
    // Open chat functionality
  };

  const handleExitPolicy = () => {
    Alert.alert(
      'Exit Policy',
      'Are you sure you want to exit your current policy? This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Exit', style: 'destructive', onPress: () => console.log('Exit policy') }
      ]
    );
  };

  const handleLogOut = () => {
    Alert.alert(
      isUsingMockAuth ? 'Exit Demo Mode' : 'Log Out',
      isUsingMockAuth
        ? 'Do you want to leave the demo user and go back to the login screen?'
        : 'Do you want to log out and return to the login screen?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: isUsingMockAuth ? 'Exit Demo' : 'Log Out',
          onPress: async () => {
            await signOut();
            navigation.reset({
              index: 0,
              routes: [{ name: 'Auth' }],
            });
          }
        }
      ]
    );
  };

  const toggleFaq = (index) => {
    setExpandedFaq(expandedFaq === index ? null : index);
  };

  const faqs = [
    {
      question: 'How does parametric insurance work?',
      answer: 'Parametric insurance automatically detects qualifying weather events in your delivery zones and processes payouts within 24 hours.'
    },
    {
      question: 'When will I receive my payout?',
      answer: 'Payouts are processed automatically within 24 hours of a qualifying event being detected in your delivery zones.'
    },
    {
      question: 'What events are covered?',
      answer: 'Heavy rainfall, flood alerts, AQI spikes, and cyclone warnings are all covered under your policy.'
    },
    {
      question: 'How is coverage calculated?',
      answer: 'Coverage is based on your delivery zones, income level, and seasonal factors. Maximum weekly coverage is ₹4,000.'
    },
    {
      question: 'Can I change my delivery zones?',
      answer: 'Yes, you can update your delivery zones in your profile settings. Coverage calculations will adjust accordingly.'
    }
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
              <Text style={styles.headerTitle}>Help Center</Text>
              <Text style={styles.headerSubtitle}>SUPPORT</Text>
            </View>
          </View>

          {/* Relationship Manager */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Relationship Manager</Text>
            <Card style={styles.relationshipCard}>
              <View style={styles.relationshipContent}>
                <View style={styles.relationshipLeft}>
                  <View style={styles.avatar}>
                    <Text style={styles.avatarText}>PS</Text>
                  </View>
                  <View style={styles.relationshipInfo}>
                    <Text style={styles.relationshipName}>Priya Sharma</Text>
                    <Text style={styles.relationshipId}>Employee ID: EMP789456</Text>
                    <Text style={styles.relationshipAvailability}>Mon–Sat, 9AM–6PM</Text>
                  </View>
                </View>
                <View style={styles.relationshipActions}>
                  <TouchableOpacity style={styles.callButton} onPress={handleCallNow}>
                    <Ionicons name="call" size={16} color={COLORS.white} />
                    <Text style={styles.callButtonText}>Call Now</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.chatButton} onPress={handleChat}>
                    <Ionicons name="chatbubble" size={16} color={COLORS.primary} />
                    <Text style={styles.chatButtonText}>Chat</Text>
                  </TouchableOpacity>
                </View>
              </View>
            </Card>
          </View>

          {/* FAQ Section */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Frequently Asked Questions</Text>
            <Card style={styles.faqCard}>
              {faqs.map((faq, index) => (
                <View key={index} style={styles.faqItem}>
                  <TouchableOpacity 
                    style={styles.faqQuestion} 
                    onPress={() => toggleFaq(index)}
                  >
                    <Text style={styles.faqQuestionText}>{faq.question}</Text>
                    <Ionicons 
                      name={expandedFaq === index ? 'chevron-down' : 'chevron-forward'} 
                      size={16} 
                      color={COLORS.grey} 
                    />
                  </TouchableOpacity>
                  {expandedFaq === index && (
                    <Text style={styles.faqAnswer}>{faq.answer}</Text>
                  )}
                  {index < faqs.length - 1 && <View style={styles.faqDivider} />}
                </View>
              ))}
            </Card>
          </View>

          {/* Policy Actions */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Policy Actions</Text>
            
            {/* Exit Policy */}
            <Card style={styles.exitPolicyCard}>
              <View style={styles.exitPolicyContent}>
                <Ionicons name="warning" size={24} color={COLORS.red} />
                <View style={styles.exitPolicyText}>
                  <Text style={styles.exitPolicyTitle}>Exit Policy</Text>
                  <Text style={styles.exitPolicyDescription}>
                    Once you exit your current policy, you will not be eligible for refunds or pro-rated coverage.
                  </Text>
                </View>
              </View>
              <TouchableOpacity style={styles.exitPolicyButton} onPress={handleExitPolicy}>
                <Text style={styles.exitPolicyButtonText}>Exit Current Policy</Text>
              </TouchableOpacity>
            </Card>

            {/* Buy New Policy */}
            <Card style={[styles.policyActionCard, styles.disabledCard]}>
              <View style={styles.policyActionContent}>
                <Ionicons name="lock-closed" size={24} color={COLORS.grey} />
                <View style={styles.policyActionText}>
                  <Text style={styles.policyActionTitle}>Buy New Policy</Text>
                  <Text style={styles.policyActionDescription}>
                    Available after current policy expires
                  </Text>
                </View>
              </View>
              <TouchableOpacity 
                style={[styles.policyActionButton, styles.disabledButton]} 
                disabled={true}
              >
                <Text style={styles.disabledButtonText}>Locked</Text>
              </TouchableOpacity>
            </Card>

            <Card style={styles.logoutCard}>
              <View style={styles.policyActionContent}>
                <Ionicons name="log-out-outline" size={24} color={COLORS.primary} />
                <View style={styles.policyActionText}>
                  <Text style={styles.logoutTitle}>{isUsingMockAuth ? 'Exit Demo User' : 'Log Out'}</Text>
                  <Text style={styles.policyActionDescription}>
                    Return to the login screen and switch accounts.
                  </Text>
                </View>
              </View>
              <TouchableOpacity style={styles.logoutButton} onPress={handleLogOut}>
                <Text style={styles.logoutButtonText}>{isUsingMockAuth ? 'Exit Demo' : 'Log Out'}</Text>
              </TouchableOpacity>
            </Card>
          </View>

          {/* Other Contacts */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Other Ways to Reach Us</Text>
            <Card style={styles.contactsCard}>
              <View style={styles.contactItem}>
                <Text style={styles.contactLabel}>Email</Text>
                <Text style={styles.contactValue}>support@rahatpay.com</Text>
              </View>
              <View style={styles.contactDivider} />
              <View style={styles.contactItem}>
                <Text style={styles.contactLabel}>Helpline</Text>
                <Text style={styles.contactValue}>1800-123-4567</Text>
              </View>
              <View style={styles.contactDivider} />
              <View style={styles.contactItem}>
                <Text style={styles.contactLabel}>WhatsApp</Text>
                <Text style={styles.contactValue}>+91-98765-43210</Text>
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
  
  // Relationship Manager Styles
  relationshipCard: {
    backgroundColor: '#1B5E20',
    borderRadius: 20,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 6,
  },
  relationshipContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  relationshipLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.white,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
  },
  avatarText: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.primary,
  },
  relationshipInfo: {
    flex: 1,
  },
  relationshipName: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.white,
    marginBottom: 4,
  },
  relationshipId: {
    fontSize: 12,
    color: `${COLORS.white}80`,
    marginBottom: 4,
  },
  relationshipAvailability: {
    fontSize: 12,
    color: `${COLORS.white}80`,
  },
  relationshipActions: {
    flexDirection: 'column',
    gap: 8,
  },
  callButton: {
    backgroundColor: COLORS.white,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  callButtonText: {
    color: COLORS.primary,
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 8,
  },
  chatButton: {
    backgroundColor: 'transparent',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: COLORS.white,
  },
  chatButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
    marginLeft: 8,
  },
  // FAQ Styles
  faqCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  faqItem: {
    marginBottom: 20,
  },
  faqQuestion: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  faqQuestionText: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
    flex: 1,
  },
  faqAnswer: {
    fontSize: 13,
    color: COLORS.grey,
    lineHeight: 18,
    marginTop: 12,
    marginBottom: 20,
    paddingLeft: 8,
  },
  faqDivider: {
    height: 1,
    backgroundColor: `${COLORS.grey}20`,
    marginVertical: 16,
  },
  optionIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  optionContent: {
    flex: 1,
  },
  optionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 4,
  },
  optionDescription: {
    fontSize: 14,
    color: COLORS.grey,
  },
  contactCard: {
    borderRadius: 16,
    padding: 20,
    marginTop: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  contactTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  contactItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  contactText: {
    fontSize: 14,
    color: COLORS.black,
    marginLeft: 12,
  },
  faqDivider: {
    height: 1,
    backgroundColor: `${COLORS.grey}20`,
    marginVertical: 16,
  },
  
  // Policy Actions Styles
  exitPolicyCard: {
    backgroundColor: '#FFF5F5',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
    borderWidth: 1,
    borderColor: '#FFEBEE',
  },
  exitPolicyContent: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  exitPolicyText: {
    flex: 1,
    marginLeft: 16,
  },
  exitPolicyTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.red,
    marginBottom: 4,
  },
  exitPolicyDescription: {
    fontSize: 12,
    color: COLORS.grey,
    lineHeight: 16,
  },
  exitPolicyButton: {
    backgroundColor: 'transparent',
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderWidth: 2,
    borderColor: COLORS.red,
  },
  exitPolicyButtonText: {
    color: COLORS.red,
    fontSize: 14,
    fontWeight: '600',
  },
  policyActionCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  disabledCard: {
    opacity: 0.6,
    backgroundColor: `${COLORS.grey}10`,
  },
  policyActionContent: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  policyActionText: {
    flex: 1,
    marginLeft: 16,
  },
  policyActionTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.grey,
    marginBottom: 4,
  },
  policyActionDescription: {
    fontSize: 12,
    color: COLORS.grey,
    lineHeight: 16,
  },
  policyActionButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  disabledButton: {
    backgroundColor: COLORS.grey,
    opacity: 0.5,
  },
  disabledButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
  },
  logoutCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  logoutTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
    marginBottom: 4,
  },
  logoutButton: {
    backgroundColor: COLORS.primary,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  logoutButtonText: {
    color: COLORS.white,
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
});

export default HelpDeskScreen;
