import React, { useState } from 'react';
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

const TransactionScreen = () => {
  const [activeTab, setActiveTab] = useState('summary');

  // Mock data
  const mockProfile = {
    name: 'Vansh Chugh',
    aadhaar: '****1234',
    pan: '****5678',
    plan: 'Trial Plan',
    expiry: 'April 16, 2026',
    totalReceived: 3200,
    coverageLeft: 800,
    weeklyCoverage: 4000,
    coverageUsed: 3200,
    coverageRemaining: 800
  };

  const mockTransactions = [
    {
      id: 1,
      event: 'Rain Alert',
      zone: 'Zone B',
      date: 'Today',
      amount: 800,
      balanceBefore: 4000,
      balanceAfter: 3200,
      icon: 'rainy'
    },
    {
      id: 2,
      event: 'AQI Spike',
      zone: 'Zone A',
      date: '3 days ago',
      amount: 600,
      balanceBefore: 4600,
      balanceAfter: 4000,
      icon: 'warning'
    },
    {
      id: 3,
      event: 'Flood Detected',
      zone: 'Zone C',
      date: '5 days ago',
      amount: 1200,
      balanceBefore: 5800,
      balanceAfter: 4600,
      icon: 'water'
    }
  ];

  const parametricTriggers = [
    {
      name: 'Heavy Rain',
      description: 'Automatic payout when rainfall exceeds threshold in your delivery zones',
      icon: 'rainy'
    },
    {
      name: 'Flood',
      description: 'Coverage activated when flood warnings are issued for your areas',
      icon: 'water'
    },
    {
      name: 'AQI Hazard',
      description: 'Payout for poor air quality affecting delivery operations',
      icon: 'warning'
    },
    {
      name: 'Cyclone',
      description: 'Coverage for cyclone warnings and severe weather events',
      icon: 'thunderstorm'
    }
  ];

  const coverageRules = [
    'Coverage applies to weather-related disruptions',
    'AQI must be above 200 for 4+ consecutive hours',
    'Flood warnings must be from official sources',
    'Rainfall threshold: 50mm in 24 hours',
    'Maximum weekly payout: ₹4,000'
  ];

  const getFormattedDate = (date) => {
    return new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const renderSummaryTab = () => (
    <View style={styles.tabContent}>
      {/* Summary Cards */}
      <View style={styles.summaryCards}>
        <Card style={styles.totalReceivedCard}>
          <Text style={styles.summaryCardLabel}>Total Received</Text>
          <Text style={styles.totalReceivedAmount}>₹{mockProfile.totalReceived.toLocaleString()}</Text>
        </Card>
        
        <Card style={styles.coverageLeftCard}>
          <Text style={styles.coverageLabel}>Coverage Left</Text>
          <Text style={styles.coverageLeftAmount}>₹{mockProfile.coverageRemaining.toLocaleString()}</Text>
          <Text style={styles.coverageSubtext}>of ₹{mockProfile.weeklyCoverage.toLocaleString()}</Text>
        </Card>
      </View>

      {/* Weekly Coverage Usage */}
      <Card style={styles.usageCard}>
        <Text style={styles.usageTitle}>Weekly Coverage Usage</Text>
        <View style={styles.progressContainer}>
          <View style={styles.progressBar}>
            <View 
              style={[
                styles.progressFill, 
                { width: `${(mockProfile.coverageUsed / mockProfile.weeklyCoverage) * 100}%` }
              ]} 
            />
          </View>
          <View style={styles.progressLabels}>
            <Text style={styles.progressLabel}>Used: ₹{mockProfile.coverageUsed.toLocaleString()}</Text>
            <Text style={styles.progressLabel}>Remaining: ₹{mockProfile.coverageRemaining.toLocaleString()}</Text>
          </View>
        </View>
      </Card>

      {/* Profile Section */}
      <Card style={styles.profileCard}>
        <Text style={styles.profileTitle}>Profile Information</Text>
        <View style={styles.profileRow}>
          <Text style={styles.profileLabel}>Name</Text>
          <Text style={styles.profileValue}>{mockProfile.name}</Text>
        </View>
        <View style={styles.profileDivider} />
        <View style={styles.profileRow}>
          <Text style={styles.profileLabel}>Aadhaar</Text>
          <Text style={styles.profileValue}>{mockProfile.aadhaar}</Text>
        </View>
        <View style={styles.profileDivider} />
        <View style={styles.profileRow}>
          <Text style={styles.profileLabel}>PAN</Text>
          <Text style={styles.profileValue}>{mockProfile.pan}</Text>
        </View>
        <View style={styles.profileDivider} />
        <View style={styles.profileRow}>
          <Text style={styles.profileLabel}>Plan</Text>
          <Text style={styles.profileValue}>{mockProfile.plan}</Text>
        </View>
        <View style={styles.profileDivider} />
        <View style={styles.profileRow}>
          <Text style={styles.profileLabel}>Expiry</Text>
          <Text style={styles.profileValue}>{mockProfile.expiry}</Text>
        </View>
      </Card>
    </View>
  );

  const renderKnowYourPlanTab = () => (
    <View style={styles.tabContent}>
      {/* Trial Explanation */}
      <Card style={styles.explanationCard}>
        <Text style={styles.explanationTitle}>Trial Plan Explanation</Text>
        <Text style={styles.explanationText}>
          Your trial plan provides comprehensive coverage for weather-related disruptions and air quality issues. 
          The plan automatically detects qualifying events in your delivery zones and processes payouts within 24 hours.
        </Text>
      </Card>

      {/* Coverage Rules */}
      <Card style={styles.rulesCard}>
        <Text style={styles.rulesTitle}>Coverage Rules</Text>
        {coverageRules.map((rule, index) => (
          <View key={index} style={styles.ruleItem}>
            <Text style={styles.ruleNumber}>{index + 1}.</Text>
            <Text style={styles.ruleText}>{rule}</Text>
          </View>
        ))}
      </Card>

      {/* Parametric Triggers */}
      <Card style={styles.triggersCard}>
        <Text style={styles.triggersTitle}>Parametric Triggers</Text>
        {parametricTriggers.map((trigger, index) => (
          <View key={index} style={styles.triggerItem}>
            <View style={styles.triggerIcon}>
              <Ionicons name={trigger.icon} size={20} color={COLORS.primary} />
            </View>
            <View style={styles.triggerInfo}>
              <Text style={styles.triggerName}>{trigger.name}</Text>
              <Text style={styles.triggerDescription}>{trigger.description}</Text>
            </View>
          </View>
        ))}
      </Card>

      {/* Auto Payout System */}
      <Card style={styles.payoutCard}>
        <Text style={styles.payoutTitle}>Auto Payout System</Text>
        <Text style={styles.payoutText}>
          Our automated system monitors weather conditions and air quality in your delivery zones. 
          When qualifying events occur, payouts are processed automatically and credited to your account within 24 hours.
        </Text>
      </Card>
    </View>
  );

  const renderTransactionsTab = () => (
    <View style={styles.tabContent}>
      {/* Transactions Header */}
      <View style={styles.transactionsHeader}>
        <Text style={styles.transactionsTitle}>All Transactions</Text>
        <View style={styles.eventsBadge}>
          <Text style={styles.eventsBadgeText}>{mockTransactions.length} events</Text>
        </View>
      </View>

      {/* Transaction List */}
      {mockTransactions.map(transaction => (
        <Card key={transaction.id} style={styles.transactionCard}>
          <View style={styles.transactionContent}>
            <View style={styles.transactionLeft}>
              <View style={styles.transactionIcon}>
                <Ionicons name={transaction.icon} size={20} color={COLORS.primary} />
              </View>
              <View style={styles.transactionInfo}>
                <Text style={styles.transactionEvent}>{transaction.event}</Text>
                <Text style={styles.transactionZone}>{transaction.zone}</Text>
                <Text style={styles.transactionDate}>{transaction.date}</Text>
              </View>
            </View>
            <View style={styles.transactionRight}>
              <Text style={styles.transactionAmount}>+₹{transaction.amount}</Text>
              <Text style={styles.balanceTransition}>
                ₹{transaction.balanceBefore} → ₹{transaction.balanceAfter}
              </Text>
            </View>
          </View>
        </Card>
      ))}
    </View>
  );

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Logo size="tiny" />
            <View style={styles.headerText}>
              <Text style={styles.headerTitle}>Transactions</Text>
              <Text style={styles.headerSubtitle}>Coverage & Payouts</Text>
            </View>
          </View>

          {/* Tab Navigation */}
          <View style={styles.tabContainer}>
            {['summary', 'knowYourPlan', 'transactions'].map((tab) => (
              <TouchableOpacity
                key={tab}
                style={[
                  styles.tab,
                  activeTab === tab && styles.activeTab
                ]}
                onPress={() => setActiveTab(tab)}
              >
                <Text style={[
                  styles.tabText,
                  activeTab === tab && styles.activeTabText
                ]}>
                  {tab === 'summary' ? 'Summary' : tab === 'knowYourPlan' ? 'Know Your Plan' : 'Transactions'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Tab Content */}
          {activeTab === 'summary' && renderSummaryTab()}
          {activeTab === 'knowYourPlan' && renderKnowYourPlanTab()}
          {activeTab === 'transactions' && renderTransactionsTab()}
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
  
  // Tab Navigation
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: `${COLORS.grey}20`,
    borderRadius: 24,
    padding: 4,
    marginBottom: 24,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 20,
    alignItems: 'center',
  },
  activeTab: {
    backgroundColor: COLORS.white,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  tabText: {
    fontSize: 12,
    fontWeight: '600',
    color: COLORS.grey,
  },
  activeTabText: {
    color: COLORS.black,
  },
  tabContent: {
    minHeight: 400,
  },
  
  // Summary Tab Styles
  summaryCards: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  totalReceivedCard: {
    flex: 1,
    backgroundColor: '#1B5E20',
    borderRadius: 24,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  coverageLeftCard: {
    flex: 1,
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  summaryCardLabel: {
    fontSize: 12,
    color: COLORS.white,
    marginBottom: 8,
  },
  totalReceivedAmount: {
    fontSize: 24,
    fontWeight: '700',
    color: COLORS.white,
  },
  coverageLeftAmount: {
    fontSize: 24,
    fontWeight: '700',
    color: COLORS.black,
  },
  coverageLabel: {
    fontSize: 12,
    color: COLORS.grey,
    marginBottom: 8,
  },
  coverageSubtext: {
    fontSize: 12,
    color: COLORS.grey,
    marginTop: 4,
  },
  usageCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  usageTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  progressContainer: {
    gap: 8,
  },
  progressBar: {
    height: 8,
    backgroundColor: `${COLORS.grey}20`,
    borderRadius: 4,
  },
  progressFill: {
    height: '100%',
    backgroundColor: COLORS.success,
    borderRadius: 4,
  },
  progressLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  progressLabel: {
    fontSize: 12,
    color: COLORS.grey,
  },
  profileCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  profileTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  profileRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  profileLabel: {
    fontSize: 14,
    color: COLORS.grey,
  },
  profileValue: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  profileDivider: {
    height: 1,
    backgroundColor: `${COLORS.grey}20`,
  },
  
  // Know Your Plan Tab Styles
  explanationCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  explanationTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 12,
  },
  explanationText: {
    fontSize: 14,
    color: COLORS.grey,
    lineHeight: 20,
  },
  rulesCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  rulesTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  ruleItem: {
    flexDirection: 'row',
    marginBottom: 12,
  },
  ruleNumber: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.primary,
    marginRight: 12,
    minWidth: 20,
  },
  ruleText: {
    fontSize: 14,
    color: COLORS.grey,
    flex: 1,
    lineHeight: 20,
  },
  triggersCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  triggersTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  triggerItem: {
    backgroundColor: `${COLORS.primary}20`,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  triggerIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.white,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  triggerInfo: {
    flex: 1,
  },
  triggerName: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 4,
  },
  triggerDescription: {
    fontSize: 12,
    color: COLORS.grey,
    lineHeight: 16,
  },
  payoutCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  payoutTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 12,
  },
  payoutText: {
    fontSize: 14,
    color: COLORS.grey,
    lineHeight: 20,
  },
  
  // Transactions Tab Styles
  transactionsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  transactionsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.black,
  },
  eventsBadge: {
    backgroundColor: COLORS.primary,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  eventsBadgeText: {
    color: COLORS.white,
    fontSize: 12,
    fontWeight: '600',
  },
  transactionCard: {
    backgroundColor: COLORS.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  transactionContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  transactionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  transactionIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: `${COLORS.primary}20`,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  transactionInfo: {
    flex: 1,
  },
  transactionEvent: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 2,
  },
  transactionZone: {
    fontSize: 12,
    color: COLORS.grey,
    marginBottom: 2,
  },
  transactionDate: {
    fontSize: 12,
    color: COLORS.grey,
  },
  transactionRight: {
    alignItems: 'flex-end',
  },
  transactionAmount: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.success,
    marginBottom: 4,
  },
  balanceTransition: {
    fontSize: 12,
    color: COLORS.grey,
  },
  summaryCard: {
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 12,
    color: COLORS.grey,
    marginBottom: 4,
  },
  summaryAmount: {
    fontSize: 16,
    fontWeight: '700',
    color: COLORS.black,
  },
  receivedAmount: {
    color: COLORS.green,
  },
  transactionsCard: {
    borderRadius: 16,
    padding: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  transactionsTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 16,
  },
  transactionItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.lightGrey,
  },
  transactionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  transactionIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  transactionInfo: {
    flex: 1,
  },
  transactionDescription: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 2,
  },
  transactionDate: {
    fontSize: 12,
    color: COLORS.grey,
  },
  transactionRight: {
    alignItems: 'flex-end',
  },
  transactionAmount: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 4,
  },
  premiumAmount: {
    color: COLORS.red,
  },
  payoutAmount: {
    color: COLORS.green,
  },
  statusBadge: {
    backgroundColor: `${COLORS.primary}20`,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
  },
  statusText: {
    fontSize: 10,
    color: COLORS.primary,
    fontWeight: '600',
  }
});

export default TransactionScreen;
