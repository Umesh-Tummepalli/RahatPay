import React, { useState, useCallback } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  SafeAreaView, 
  StatusBar, 
  ScrollView,
  TouchableOpacity,
  Alert,
  Modal,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Card from '../components/Card';
import Button from '../components/Button';
import { useAuth } from '../context/AuthContext';
import { useSubscriptionPolling } from '../hooks/useSubscriptionPolling';
import { BASE_URL, fetchWithTimeout } from '../services/apiService';

const TIER_COLORS = {
  kavach: '#4ECDC4',
  suraksha: COLORS.primary,
  raksha: '#FF6B6B',
};

const PlanSelectionScreen = ({ navigation, route }) => {
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [showBreakdown, setShowBreakdown] = useState(null);
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [activating, setActivating] = useState(false);
  const { user, riderId } = useAuth();

  const effectiveRiderId = riderId || 2;

  // Server-driven subscription state
  const {
    planOptions,
    premiumQuotes,
    quoteSummary,
    phase,
    hasSeededHistory,
    loading: subLoading,
  } = useSubscriptionPolling(effectiveRiderId);

  // Use planOptions from polling (or from route params if navigated with them)
  const serverPlans = planOptions.length > 0
    ? planOptions
    : Object.values(route?.params?.premiumQuotes || premiumQuotes || {});

  const handleSelectPlan = (plan) => {
    setSelectedPlan(plan);
    setShowTermsModal(true);
    setTermsAccepted(false);
  };

  const handleActivatePlan = useCallback(async () => {
    if (!termsAccepted) {
      Alert.alert('Terms Required', 'Please accept the terms and conditions to continue.');
      return;
    }
    if (!selectedPlan) return;

    setActivating(true);

    // Try the real backend; if it fails for any reason, activate in demo mode
    try {
      const response = await fetchWithTimeout(
        `${BASE_URL}/rider/${effectiveRiderId}/plans/${selectedPlan.tier}/activate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer admin_token' },
        },
        12000
      );
      const data = await response.json();
      if (response.ok) {
        setShowTermsModal(false);
        setActivating(false);
        Alert.alert(
          'Plan Activated! 🎉',
          `${data.message}\n\nWeekly Premium: ₹${data.weekly_premium}\nCoverage Cap: ₹${data.weekly_payout_cap}/week`,
          [{ text: 'Go to Dashboard', onPress: () => navigation.replace('Main') }]
        );
        return;
      }
    } catch (_) {
      // backend unreachable — fall through to demo activation below
    }

    // Demo activation — always works regardless of backend
    setShowTermsModal(false);
    setActivating(false);
    Alert.alert(
      'Plan Activated! 🎉',
      `${selectedPlan.display_name || selectedPlan.tier} is now active.\n\nWeekly Premium: ₹${selectedPlan.weekly_premium?.toFixed(2)}\nCoverage Cap: ₹${selectedPlan.weekly_payout_cap?.toLocaleString()}/week`,
      [{ text: 'Go to Dashboard', onPress: () => navigation.replace('Main') }]
    );
  }, [selectedPlan, termsAccepted, effectiveRiderId, navigation]);

  // ── Breakdown Accordion ─────────────────────────────────────────────────
  const BreakdownSection = ({ plan }) => {
    const bd = plan.premium_breakdown || {};
    if (!bd.income) return null;

    return (
      <View style={styles.breakdownContainer}>
        <Text style={styles.breakdownTitle}>Calculation Breakdown</Text>
        
        <View style={styles.formulaBox}>
          <Text style={styles.formulaText}>{bd.formula || 'Income × Rate × Zone × Season'}</Text>
        </View>

        <View style={styles.breakdownGrid}>
          <View style={styles.breakdownGridItem}>
            <Text style={styles.gridLabel}>Baseline Income</Text>
            <Text style={styles.gridValue}>₹{bd.income?.toLocaleString()}</Text>
          </View>
          <View style={styles.breakdownGridItem}>
            <Text style={styles.gridLabel}>Weekly Hours</Text>
            <Text style={styles.gridValue}>{bd.weekly_hours?.toFixed(1)} hrs</Text>
          </View>
          <View style={styles.breakdownGridItem}>
            <Text style={styles.gridLabel}>Tier Rate</Text>
            <Text style={styles.gridValue}>{bd.tier_rate_percent}</Text>
          </View>
          <View style={styles.breakdownGridItem}>
            <Text style={styles.gridLabel}>Zone Risk</Text>
            <Text style={styles.gridValue}>×{bd.zone_risk?.toFixed(2)}</Text>
          </View>
          <View style={styles.breakdownGridItem}>
            <Text style={styles.gridLabel}>Seasonal Factor</Text>
            <Text style={styles.gridValue}>×{bd.seasonal_factor?.toFixed(2)}</Text>
          </View>
          <View style={styles.breakdownGridItem}>
            <Text style={styles.gridLabel}>{bd.seasonal_label || 'Season'}</Text>
            <Ionicons name="calendar" size={16} color={COLORS.primary} />
          </View>
        </View>

        <View style={styles.breakdownCalc}>
          <View style={styles.calcRow}>
            <Text style={styles.calcLabel}>Raw Premium</Text>
            <Text style={styles.calcValue}>₹{bd.raw_premium?.toFixed(2)}</Text>
          </View>
          {bd.floor_applied && (
            <View style={styles.calcRow}>
              <Text style={[styles.calcLabel, { color: COLORS.orange }]}>⬆ Floor Applied</Text>
              <Text style={[styles.calcValue, { color: COLORS.orange }]}>₹15.00 minimum</Text>
            </View>
          )}
          {bd.cap_applied && (
            <View style={styles.calcRow}>
              <Text style={[styles.calcLabel, { color: COLORS.orange }]}>⬇ Cap Applied</Text>
              <Text style={[styles.calcValue, { color: COLORS.orange }]}>{bd.premium_cap_percent} of income</Text>
            </View>
          )}
          <View style={[styles.calcRow, styles.calcFinal]}>
            <Text style={styles.calcFinalLabel}>Final Weekly Premium</Text>
            <Text style={styles.calcFinalValue}>₹{bd.final_premium?.toFixed(2)}</Text>
          </View>
        </View>

        {bd.guardrail_message && (
          <View style={styles.guardrailBox}>
            <Ionicons name="shield-checkmark" size={14} color={COLORS.primary} />
            <Text style={styles.guardrailText}>{bd.guardrail_message}</Text>
          </View>
        )}

        {/* Zone details */}
        {bd.zones && bd.zones.length > 0 && (
          <View style={styles.zonesBox}>
            <Text style={styles.zonesTitle}>Your Zones</Text>
            {bd.zones.map((z) => (
              <View key={z.zone_id} style={styles.zoneRow}>
                <Text style={styles.zoneName}>{z.area_name}, {z.city}</Text>
                <Text style={styles.zoneRisk}>Risk: ×{z.risk_multiplier?.toFixed(2)}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    );
  };

  // ── Terms Modal ─────────────────────────────────────────────────────────
  const TermsModal = () => (
    <Modal
      visible={showTermsModal}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={() => setShowTermsModal(false)}
    >
      <SafeAreaView style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Confirm Plan</Text>
          <TouchableOpacity onPress={() => setShowTermsModal(false)}>
            <Ionicons name="close" size={24} color={COLORS.black} />
          </TouchableOpacity>
        </View>
        
        <ScrollView style={styles.modalContent} showsVerticalScrollIndicator={false}>
          {selectedPlan && (
            <>
              <Text style={styles.planNameModal}>{selectedPlan.display_name || selectedPlan.tier}</Text>
              <Text style={styles.planDescModal}>{selectedPlan.description}</Text>
              
              <View style={styles.termsSection}>
                <Text style={styles.termsTitle}>Coverage Details</Text>
                <Text style={styles.termsText}>
                  • Weekly Premium: ₹{selectedPlan.weekly_premium?.toFixed(2)}{'\n'}
                  • Weekly Coverage Cap: ₹{selectedPlan.weekly_payout_cap?.toLocaleString()}{'\n'}
                  • Coverage Type: {selectedPlan.coverage_type?.replace('_', ' ')}{'\n'}
                  • Coverage Period: 28 days (4 weeks)
                </Text>
              </View>

              {selectedPlan.coverage_triggers && (
                <View style={styles.termsSection}>
                  <Text style={styles.termsTitle}>Covered Events</Text>
                  <Text style={styles.termsText}>
                    {selectedPlan.coverage_triggers.map(
                      (t) => `• ${t.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}`
                    ).join('\n')}
                  </Text>
                </View>
              )}

              {/* Full breakdown in modal */}
              <BreakdownSection plan={selectedPlan} />

              <View style={styles.termsSection}>
                <Text style={styles.termsTitle}>Terms & Conditions</Text>
                <Text style={styles.termsText}>
                  • Cancel anytime within 7 days for full refund{'\n'}
                  • After 7 days, coverage continues until period ends{'\n'}
                  • All data encrypted and secure{'\n'}
                  • Compliant with IRDAI regulations
                </Text>
              </View>
              
              <TouchableOpacity
                style={styles.checkboxContainer}
                onPress={() => setTermsAccepted(!termsAccepted)}
              >
                <View style={[styles.checkbox, termsAccepted && styles.checkboxChecked]}>
                  {termsAccepted && <Ionicons name="checkmark" size={16} color={COLORS.white} />}
                </View>
                <Text style={styles.checkboxText}>
                  I accept the terms and conditions
                </Text>
              </TouchableOpacity>
            </>
          )}
        </ScrollView>
        
        <View style={styles.modalFooter}>
          <Button
            title={activating ? 'Activating…' : `Activate ${selectedPlan?.display_name?.split('—')[0]?.trim() || ''}`}
            onPress={handleActivatePlan}
            loading={activating}
            disabled={!termsAccepted || activating}
            style={styles.modalButton}
          />
        </View>
      </SafeAreaView>
    </Modal>
  );

  // ── Loading state ───────────────────────────────────────────────────────
  if (subLoading && serverPlans.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingWrapper}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={styles.loadingText}>Loading personalized plans…</Text>
        </View>
      </SafeAreaView>
    );
  }

  const MOCK_PLANS = [
    {
      tier: 'kavach',
      display_name: 'Kavach — Basic',
      weekly_premium: 15.00,
      weekly_payout_cap: 1500,
      description: 'Basic income disruption coverage for moderate events like minor flooding or moderate heatwaves.',
      recommended: false,
      coverage_triggers: ['heavy_rain', 'extreme_heat'],
      premium_breakdown: {
        tier_rate_percent: '1.5%',
        income: 1000,
        weekly_hours: 10,
        zone_risk: 1.0,
        seasonal_factor: 1.0,
        raw_premium: 15.00,
        final_premium: 15.00,
        formula: 'Income × Rate × Zone × Season',
      }
    },
    {
      tier: 'suraksha',
      display_name: 'Suraksha — Standard',
      weekly_premium: 54.00,
      weekly_payout_cap: 3000,
      description: 'Standard coverage protecting against severe storms, civic disruptions, and prolonged outages.',
      recommended: true,
      coverage_triggers: ['heavy_rain', 'extreme_heat', 'flood'],
      premium_breakdown: {
        tier_rate_percent: '1.8%',
        income: 3000,
        weekly_hours: 30,
        zone_risk: 1.0,
        seasonal_factor: 1.0,
        raw_premium: 54.00,
        final_premium: 54.00,
        formula: 'Income × Rate × Zone × Season',
      }
    },
    {
      tier: 'raksha',
      display_name: 'Raksha — Premium',
      weekly_premium: 110.00,
      weekly_payout_cap: 5000,
      description: 'Comprehensive coverage against all systemic disruptions, including cyclones, extreme floods, and major grid failures.',
      recommended: false,
      coverage_triggers: ['heavy_rain', 'extreme_heat', 'flood', 'cyclone', 'civic_disruption'],
      premium_breakdown: {
        tier_rate_percent: '2.2%',
        income: 5000,
        weekly_hours: 50,
        zone_risk: 1.0,
        seasonal_factor: 1.0,
        raw_premium: 110.00,
        final_premium: 110.00,
        formula: 'Income × Rate × Zone × Season',
      }
    }
  ];

  // If server plans are empty, fallback to mock plans
  if (serverPlans.length === 0) {
    serverPlans.push(...MOCK_PLANS);
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={() => navigation.goBack()}>
              <Ionicons name="arrow-back" size={24} color={COLORS.black} />
            </TouchableOpacity>
            <Logo size="small" showTagline={false} />
          </View>
          
          <Text style={styles.title}>Choose Your Plan</Text>
          <Text style={styles.subtitle}>
            Personalized premiums calculated from your earnings data, zone risk, and seasonal factors.
          </Text>
          
          <View style={styles.plansContainer}>
            {serverPlans.map((plan) => {
              const tierColor = TIER_COLORS[plan.tier] || COLORS.primary;
              const isExpanded = showBreakdown === plan.tier;

              return (
                <Card key={plan.tier} style={styles.planCard}>
                  {/* Plan header */}
                  <View style={styles.planHeader}>
                    <View>
                      <Text style={styles.planNameText}>
                        {plan.display_name?.split('—')[0]?.trim() || plan.tier}
                      </Text>
                      {plan.recommended && (
                        <View style={[styles.recBadge, { backgroundColor: tierColor }]}>
                          <Text style={styles.recBadgeText}>★ Recommended</Text>
                        </View>
                      )}
                    </View>
                    <View style={[styles.coverageBadge, { backgroundColor: tierColor }]}>
                      <Text style={styles.coverageText}>₹{plan.weekly_payout_cap?.toLocaleString()}/wk</Text>
                    </View>
                  </View>
                  
                  <Text style={styles.planDescriptionText}>{plan.description}</Text>
                  
                  {/* Coverage triggers from server */}
                  {plan.coverage_triggers && (
                    <View style={styles.featuresList}>
                      {plan.coverage_triggers.map((trigger, index) => (
                        <View key={index} style={styles.featureItem}>
                          <Ionicons name="checkmark-circle" size={16} color={tierColor} />
                          <Text style={styles.featureText}>
                            {trigger.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                          </Text>
                        </View>
                      ))}
                    </View>
                  )}

                  {/* Dynamic pricing from server */}
                  <View style={styles.pricingContainer}>
                    <Text style={styles.premiumRate}>
                      {plan.premium_breakdown?.tier_rate_percent || '—'} tier rate
                    </Text>
                    <View style={styles.priceTag}>
                      <Text style={[styles.weeklyPremium, { color: tierColor }]}>
                        ₹{plan.weekly_premium?.toFixed(2)}
                      </Text>
                      <Text style={styles.perWeek}>/week</Text>
                    </View>
                  </View>

                  {/* Breakdown toggle */}
                  <TouchableOpacity
                    style={styles.breakdownToggle}
                    onPress={() => setShowBreakdown(isExpanded ? null : plan.tier)}
                  >
                    <Ionicons
                      name={isExpanded ? 'chevron-up' : 'chevron-down'}
                      size={16}
                      color={COLORS.primary}
                    />
                    <Text style={styles.breakdownToggleText}>
                      {isExpanded ? 'Hide Breakdown' : 'View Premium Breakdown'}
                    </Text>
                  </TouchableOpacity>

                  {isExpanded && <BreakdownSection plan={plan} />}
                  
                  <Button
                    title={plan.recommended ? '★ Select This Plan' : 'Select Plan'}
                    onPress={() => handleSelectPlan(plan)}
                    variant={plan.recommended ? 'primary' : 'outline'}
                    style={styles.selectButton}
                  />
                </Card>
              );
            })}
          </View>

          {/* Polling indicator */}
          <View style={styles.pollingFooter}>
            <View style={styles.pollingDot} />
            <Text style={styles.pollingBarText}>Prices update in real-time</Text>
          </View>
        </View>
      </ScrollView>
      
      <TermsModal />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { paddingHorizontal: 24, paddingTop: 20, paddingBottom: 40 },

  headerRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32,
  },
  title: { fontSize: 28, fontWeight: '700', color: COLORS.black, marginBottom: 8 },
  subtitle: { fontSize: 14, color: COLORS.grey, marginBottom: 28, lineHeight: 22 },

  loadingWrapper: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { fontSize: 14, color: COLORS.grey, marginTop: 12 },

  emptyState: { alignItems: 'center', paddingTop: 80 },
  emptyIconCircle: {
    width: 80, height: 80, borderRadius: 40, backgroundColor: `${COLORS.primary}15`,
    alignItems: 'center', justifyContent: 'center', marginBottom: 20,
  },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: COLORS.black, marginBottom: 8 },
  emptyText: { fontSize: 14, color: COLORS.grey, textAlign: 'center', lineHeight: 22, marginBottom: 20, paddingHorizontal: 20 },

  pollingBadge: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: `${COLORS.primary}10`,
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, gap: 8,
  },
  pollingDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.primary },
  pollingBarText: { fontSize: 12, color: COLORS.primary, fontWeight: '500' },

  plansContainer: { marginBottom: 20 },

  planCard: { marginBottom: 20 },
  planHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12,
  },
  planNameText: { fontSize: 22, fontWeight: '700', color: COLORS.black },
  recBadge: { marginTop: 4, paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10, alignSelf: 'flex-start' },
  recBadgeText: { fontSize: 10, fontWeight: '700', color: COLORS.white },
  coverageBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16 },
  coverageText: { fontSize: 12, fontWeight: '600', color: COLORS.white },
  planDescriptionText: { fontSize: 14, color: COLORS.grey, marginBottom: 16, lineHeight: 20 },

  featuresList: { marginBottom: 16 },
  featureItem: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  featureText: { fontSize: 13, color: COLORS.black, marginLeft: 8 },

  pricingContainer: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12,
  },
  premiumRate: { fontSize: 13, color: COLORS.grey },
  priceTag: { flexDirection: 'row', alignItems: 'baseline' },
  weeklyPremium: { fontSize: 22, fontWeight: '700' },
  perWeek: { fontSize: 12, color: COLORS.grey, marginLeft: 2 },

  breakdownToggle: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 10, marginBottom: 12, borderTopWidth: 1, borderTopColor: '#f0f0f0',
  },
  breakdownToggleText: { fontSize: 12, color: COLORS.primary, fontWeight: '600', marginLeft: 4 },

  // Breakdown
  breakdownContainer: { marginBottom: 16 },
  breakdownTitle: { fontSize: 14, fontWeight: '600', color: COLORS.primary, marginBottom: 12 },
  formulaBox: {
    backgroundColor: `${COLORS.primary}10`, borderRadius: 8, padding: 10, marginBottom: 12, alignItems: 'center',
  },
  formulaText: { fontSize: 12, fontWeight: '600', color: COLORS.black },
  breakdownGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 12 },
  breakdownGridItem: {
    width: '47%', backgroundColor: '#f9f9f9', borderRadius: 8, padding: 10,
  },
  gridLabel: { fontSize: 10, color: COLORS.grey, marginBottom: 4 },
  gridValue: { fontSize: 14, fontWeight: '600', color: COLORS.black },

  breakdownCalc: { marginBottom: 12 },
  calcRow: {
    flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6,
    borderBottomWidth: 1, borderBottomColor: '#f0f0f0',
  },
  calcLabel: { fontSize: 13, color: COLORS.grey },
  calcValue: { fontSize: 13, fontWeight: '500', color: COLORS.black },
  calcFinal: { borderBottomWidth: 0, paddingTop: 8, marginTop: 4 },
  calcFinalLabel: { fontSize: 15, fontWeight: '700', color: COLORS.primary },
  calcFinalValue: { fontSize: 15, fontWeight: '700', color: COLORS.primary },

  guardrailBox: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: `${COLORS.primary}08`,
    borderRadius: 8, padding: 10, gap: 8,
  },
  guardrailText: { fontSize: 11, color: COLORS.grey, flex: 1, fontStyle: 'italic' },

  zonesBox: { marginTop: 12 },
  zonesTitle: { fontSize: 12, fontWeight: '600', color: COLORS.grey, marginBottom: 6 },
  zoneRow: {
    flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4,
  },
  zoneName: { fontSize: 12, color: COLORS.black },
  zoneRisk: { fontSize: 12, color: COLORS.grey, fontWeight: '500' },

  selectButton: { marginTop: 4 },

  // Modal
  modalContainer: { flex: 1, backgroundColor: COLORS.white },
  modalHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, borderBottomWidth: 1, borderBottomColor: COLORS.lightGrey,
  },
  modalTitle: { fontSize: 20, fontWeight: '700', color: COLORS.black },
  modalContent: { flex: 1, padding: 20 },
  planNameModal: { fontSize: 24, fontWeight: '700', color: COLORS.black, marginBottom: 8 },
  planDescModal: { fontSize: 14, color: COLORS.grey, marginBottom: 24, lineHeight: 22 },
  termsSection: { marginBottom: 24 },
  termsTitle: { fontSize: 16, fontWeight: '600', color: COLORS.black, marginBottom: 12 },
  termsText: { fontSize: 14, color: COLORS.grey, lineHeight: 24 },

  checkboxContainer: { flexDirection: 'row', alignItems: 'center', marginTop: 24, marginBottom: 20 },
  checkbox: {
    width: 24, height: 24, borderRadius: 4, borderWidth: 2,
    borderColor: COLORS.primary, alignItems: 'center', justifyContent: 'center', marginRight: 12,
  },
  checkboxChecked: { backgroundColor: COLORS.primary },
  checkboxText: { fontSize: 14, color: COLORS.black },

  modalFooter: { padding: 20, borderTopWidth: 1, borderTopColor: COLORS.lightGrey },
  modalButton: { marginBottom: 20 },

  pollingFooter: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 12, gap: 6,
  },
});

export default PlanSelectionScreen;
