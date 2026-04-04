import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  StatusBar,
  ScrollView,
  TouchableOpacity,
  Alert,
  Dimensions,
  RefreshControl,
  AppState,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Card from '../components/Card';
import { useAuth } from '../context/AuthContext';
import { useSubscriptionPolling } from '../hooks/useSubscriptionPolling';
import { BASE_URL, fetchWithTimeout } from '../services/apiService';

const { width: screenWidth } = Dimensions.get('window');
const EVENT_POLL_INTERVAL = 5000;

const HomeDashboard = ({ navigation }) => {
  const { user, riderId } = useAuth();
  const effectiveRiderId = riderId || 2;

  // ── Server-driven subscription state (polls every 5s) ───────────────────
  const {
    phase,
    banner,
    notification,
    notificationUnread,
    premiumQuotes,
    quoteSummary,
    currentPlan,
    hasSeededHistory,
    trial,
    acknowledgeNotification,
    loading: subLoading,
  } = useSubscriptionPolling(effectiveRiderId);

  // ── Server-driven events (polls every 5s) ───────────────────────────────
  const [activeEvents, setActiveEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const appStateRef = useRef(AppState.currentState);
  const mountedRef = useRef(true);

  // ── Server-driven rider profile ─────────────────────────────────────────
  const [riderProfile, setRiderProfile] = useState(null);
  const [policyData, setPolicyData] = useState(null);

  const fetchRiderDashboard = useCallback(async () => {
    try {
      const response = await fetchWithTimeout(
        `${BASE_URL}/rider/${effectiveRiderId}/dashboard`,
        { headers: { 'Authorization': 'Bearer admin_token' } },
        6000
      );
      if (!response.ok) return;
      const data = await response.json();
      if (mountedRef.current) {
        setRiderProfile(data.rider || null);
        setPolicyData(data.active_policy || null);
      }
    } catch (err) {
      console.warn('Dashboard fetch error:', err.message);
    }
  }, [effectiveRiderId]);

  const fetchActiveEvents = useCallback(async () => {
    try {
      const response = await fetchWithTimeout(
        `${BASE_URL}/admin/rider/${effectiveRiderId}/active-events`,
        { headers: { 'Authorization': 'Bearer admin_token' } },
        6000
      );
      if (!response.ok) return;
      const data = await response.json();
      if (mountedRef.current) setActiveEvents(data || []);
    } catch (err) {
      console.warn('Events fetch error:', err.message);
    } finally {
      if (mountedRef.current) setEventsLoading(false);
    }
  }, [effectiveRiderId]);

  // Initial fetch + polling
  useEffect(() => {
    mountedRef.current = true;
    setEventsLoading(true);
    fetchActiveEvents();
    fetchRiderDashboard();

    const interval = setInterval(() => {
      if (appStateRef.current === 'active') {
        fetchActiveEvents();
        fetchRiderDashboard();
      }
    }, EVENT_POLL_INTERVAL);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [fetchActiveEvents, fetchRiderDashboard]);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (next) => {
      appStateRef.current = next;
    });
    return () => sub?.remove();
  }, []);

  // ── Handle notification tap ─────────────────────────────────────────────
  const handleNotificationTap = useCallback(async () => {
    await acknowledgeNotification();
    navigation.navigate('Plans', { premiumQuotes, quoteSummary });
  }, [acknowledgeNotification, navigation, premiumQuotes, quoteSummary]);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([fetchActiveEvents(), fetchRiderDashboard()]);
    setRefreshing(false);
  }, [fetchActiveEvents, fetchRiderDashboard]);

  // ── Helpers ─────────────────────────────────────────────────────────────
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const getEventIcon = (type) => {
    const icons = {
      flood: 'water',
      heavy_rain: 'rainy',
      cyclone: 'thunderstorm',
      extreme_heat: 'sunny',
      poor_aqi: 'warning',
      civic_disruption: 'megaphone',
    };
    return icons[type] || 'alert-circle';
  };

  const getEventColor = (severity) => {
    if (severity?.includes('severe')) return '#F44336';
    if (severity === 'moderate') return '#FF9800';
    return '#FFC107';
  };

  const formatEventType = (type) =>
    (type || 'event').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const formatRelativeTime = (dateStr) => {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const hrs = Math.floor(diff / 3600000);
    if (hrs < 1) return 'Just now';
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  // ── Derived display values (all from server) ───────────────────────────
  const displayPolicy = currentPlan || policyData;
  const isTrialActive = phase === 'trial_active';
  const isPlanSelection = phase === 'plan_selection';
  const isPaidActive = phase === 'paid_active';

  const coverageAmount = displayPolicy
    ? Number(displayPolicy.weekly_payout_cap || 0)
    : (trial?.weekly_coverage || 0);
  const premiumAmount = displayPolicy
    ? Number(displayPolicy.weekly_premium || 0)
    : (trial?.premium_paid || 0);
  const tierName = displayPolicy
    ? (displayPolicy.display_name || displayPolicy.tier || 'Trial')
    : 'Trial';

  // Pick the recommended quote for breakdown display
  const recommendedTier = Object.values(premiumQuotes).find((q) => q.recommended);
  const breakdownData = recommendedTier?.premium_breakdown || null;

  // ── Loading state ──────────────────────────────────────────────────────
  if (subLoading && !riderProfile) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={COLORS.primary} />
        <Text style={styles.loadingText}>Loading dashboard…</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />

      {/* ── Header ─────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Logo size="tiny" />
          <View style={styles.greetingContainer}>
            <Text style={styles.greeting}>{getGreeting()}</Text>
            <Text style={styles.userName}>
              {riderProfile?.name || user?.displayName || 'User'} {'\u{1F44B}'}
            </Text>
          </View>
        </View>
        <TouchableOpacity
          style={[styles.notificationButton, notificationUnread && styles.notificationActive]}
          onPress={notificationUnread ? handleNotificationTap : undefined}
        >
          <Ionicons
            name={notificationUnread ? 'notifications' : 'notifications-outline'}
            size={24}
            color={notificationUnread ? COLORS.white : COLORS.black}
          />
          {notificationUnread && <View style={styles.notificationDot} />}
        </TouchableOpacity>
      </View>

      {/* ── Notification Banner (server-driven) ────────────────────── */}
      {notificationUnread && notification && (
        <TouchableOpacity style={styles.notificationBanner} onPress={handleNotificationTap}>
          <View style={styles.notificationBannerContent}>
            <Ionicons name="megaphone" size={20} color="#fff" />
            <View style={{ flex: 1, marginLeft: 10 }}>
              <Text style={styles.notificationTitle}>{notification.title}</Text>
              <Text style={styles.notificationBody}>{notification.body}</Text>
            </View>
            <Ionicons name="chevron-forward" size={20} color="#fff" />
          </View>
        </TouchableOpacity>
      )}

      {/* ── Trial / Status Banner (server-driven) ──────────────────── */}
      {banner && !notificationUnread && (
        <View style={[
          styles.bannerContainer,
          banner.variant === 'warning' && styles.bannerWarning,
          banner.variant === 'info' && styles.bannerInfo,
          banner.variant === 'success' && styles.bannerSuccess,
        ]}>
          <Ionicons
            name={banner.variant === 'success' ? 'checkmark-circle' : banner.variant === 'warning' ? 'warning' : 'information-circle'}
            size={18}
            color="#fff"
          />
          <View style={{ flex: 1, marginLeft: 8 }}>
            <Text style={styles.bannerTitle}>{banner.title}</Text>
            <Text style={styles.bannerBody}>{banner.body}</Text>
          </View>
          {isPlanSelection && (
            <TouchableOpacity onPress={() => navigation.navigate('Plans', { premiumQuotes, quoteSummary })}>
              <Text style={styles.bannerCTA}>View Plans →</Text>
            </TouchableOpacity>
          )}
        </View>
      )}

      {/* ── Active Disruption Events (server-driven) ───────────────── */}
      {activeEvents.length > 0 && (
        <View style={styles.eventsBanner}>
          <View style={styles.eventsBannerHeader}>
            <Ionicons name="warning" size={18} color={COLORS.white} />
            <Text style={styles.eventsBannerTitle}>
              Active Disruptions ({activeEvents.length})
            </Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.eventsScroll}>
            {activeEvents.map((event) => (
              <View
                key={event.id}
                style={[styles.eventChip, { borderLeftColor: getEventColor(event.severity) }]}
              >
                <Ionicons name={getEventIcon(event.event_type)} size={14} color={getEventColor(event.severity)} />
                <View style={{ marginLeft: 6 }}>
                  <Text style={styles.eventChipType}>{formatEventType(event.event_type)}</Text>
                  <Text style={styles.eventChipMeta}>
                    Zone {event.affected_zone} · {formatRelativeTime(event.event_start)}
                  </Text>
                </View>
              </View>
            ))}
          </ScrollView>
        </View>
      )}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} colors={[COLORS.primary]} />
        }
      >
        {/* ── Insurance Card (server-driven) ────────────────────────── */}
        <View style={styles.insuranceCardContainer}>
          <View style={styles.backgroundShape1} />
          <View style={styles.backgroundShape2} />

          <Card style={styles.insuranceCard}>
            <View style={styles.cardHeader}>
              <View style={[
                styles.phaseBadge,
                isPaidActive && styles.phaseBadgePaid,
                isPlanSelection && styles.phaseBadgeSelection,
              ]}>
                <Text style={styles.phaseBadgeText}>
                  {isPaidActive ? tierName : isTrialActive ? 'Trial Active' : 'Select a Plan'}
                </Text>
              </View>
              <Text style={styles.cardTitle}>Insurance Coverage</Text>
            </View>

            <View style={styles.coverageRow}>
              <View style={styles.coverageItem}>
                <Text style={styles.coverageLabel}>Weekly Coverage</Text>
                <Text style={styles.coverageAmount}>₹{coverageAmount.toLocaleString()}</Text>
              </View>
              <View style={styles.coverageItem}>
                <Text style={styles.coverageLabel}>
                  {isPaidActive ? 'Weekly Premium' : 'Trial Premium'}
                </Text>
                <Text style={styles.premiumAmountText}>₹{premiumAmount.toLocaleString()}</Text>
              </View>
            </View>

            {trial?.days_remaining != null && isTrialActive && (
              <View style={styles.progressContainer}>
                <Text style={styles.progressLabel}>Trial Remaining</Text>
                <View style={styles.progressBar}>
                  <View style={[styles.progressFill, { width: `${Math.min(100, (trial.days_remaining / 15) * 100)}%` }]} />
                </View>
                <Text style={styles.progressPercentage}>{trial.days_remaining} days left</Text>
              </View>
            )}

            <View style={styles.cardDetails}>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Phase</Text>
                <Text style={styles.detailValue}>
                  {isPaidActive ? 'Active' : isTrialActive ? 'Trial' : 'Action Required'}
                </Text>
              </View>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>City</Text>
                <Text style={styles.detailValue}>{riderProfile?.city || '—'}</Text>
              </View>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Platform</Text>
                <Text style={styles.detailValue} numberOfLines={1}>
                  {(riderProfile?.platform || '—').charAt(0).toUpperCase() + (riderProfile?.platform || '').slice(1)}
                </Text>
              </View>
            </View>
          </Card>
        </View>

        {/* ── Premium Breakdown (server-driven) ────────────────────── */}
        {breakdownData && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Premium Breakdown</Text>
            <Card style={styles.premiumCard}>
              <View style={styles.premiumInnerCard}>
                <Text style={styles.premiumFormula}>{breakdownData.formula || 'Income × Rate × Zone × Season'}</Text>
                <View style={styles.premiumValues}>
                  <View style={styles.valueBox}>
                    <Text style={styles.valueLabel}>Baseline Income</Text>
                    <Text style={styles.valueAmount}>₹{breakdownData.income?.toLocaleString() || '—'}</Text>
                  </View>
                  <View style={styles.valueBox}>
                    <Text style={styles.valueLabel}>Tier Rate</Text>
                    <Text style={styles.valueAmount}>{breakdownData.tier_rate_percent || '—'}</Text>
                  </View>
                  <View style={styles.valueBox}>
                    <Text style={styles.valueLabel}>Zone Risk</Text>
                    <Text style={styles.valueAmount}>×{breakdownData.zone_risk?.toFixed(2) || '—'}</Text>
                  </View>
                  <View style={styles.valueBox}>
                    <Text style={styles.valueLabel}>Seasonal</Text>
                    <Text style={styles.valueAmount}>×{breakdownData.seasonal_factor?.toFixed(2) || '—'}</Text>
                  </View>
                </View>
              </View>

              <View style={styles.breakdownResult}>
                <View style={styles.breakdownRow}>
                  <Text style={styles.breakdownLabel}>Raw Premium</Text>
                  <Text style={styles.breakdownValue}>₹{breakdownData.raw_premium?.toFixed(2) || '—'}</Text>
                </View>
                {breakdownData.floor_applied && (
                  <View style={styles.breakdownRow}>
                    <Text style={[styles.breakdownLabel, { color: COLORS.orange }]}>Floor Applied</Text>
                    <Text style={[styles.breakdownValue, { color: COLORS.orange }]}>₹15 minimum</Text>
                  </View>
                )}
                {breakdownData.cap_applied && (
                  <View style={styles.breakdownRow}>
                    <Text style={[styles.breakdownLabel, { color: COLORS.orange }]}>Cap Applied</Text>
                    <Text style={[styles.breakdownValue, { color: COLORS.orange }]}>{breakdownData.premium_cap_percent}</Text>
                  </View>
                )}
                <View style={[styles.breakdownRow, styles.breakdownFinal]}>
                  <Text style={styles.breakdownFinalLabel}>Final Weekly Premium</Text>
                  <Text style={styles.breakdownFinalValue}>₹{breakdownData.final_premium?.toFixed(2) || '—'}</Text>
                </View>
                {breakdownData.guardrail_message && (
                  <Text style={styles.guardrailText}>{breakdownData.guardrail_message}</Text>
                )}
              </View>
            </Card>
          </View>
        )}

        {/* ── Quick Quotes Summary (when in plan_selection) ────────── */}
        {isPlanSelection && Object.keys(quoteSummary).length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>Your Dynamic Premiums</Text>
              <TouchableOpacity onPress={() => navigation.navigate('Plans', { premiumQuotes, quoteSummary })}>
                <Text style={styles.viewAllText}>Compare Plans →</Text>
              </TouchableOpacity>
            </View>
            <View style={styles.quotesRow}>
              {Object.entries(quoteSummary).map(([tier, amount]) => (
                <TouchableOpacity
                  key={tier}
                  style={[styles.quoteCard, tier === 'suraksha' && styles.quoteCardRecommended]}
                  onPress={() => navigation.navigate('Plans', { premiumQuotes, quoteSummary })}
                >
                  {tier === 'suraksha' && <Text style={styles.recBadge}>★ Recommended</Text>}
                  <Text style={styles.quoteTierName}>{tier.charAt(0).toUpperCase() + tier.slice(1)}</Text>
                  <Text style={styles.quoteAmount}>₹{Number(amount).toFixed(0)}</Text>
                  <Text style={styles.quotePerWeek}>per week</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* ── Recent Transactions (navigate to full list) ──────────── */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Activity</Text>
            <TouchableOpacity
              style={styles.earningsButton}
              onPress={() => navigation.navigate('EarningsHistory')}
            >
              <Ionicons name="stats-chart" size={16} color={COLORS.primary} />
              <Text style={styles.earningsButtonText}>Earnings</Text>
            </TouchableOpacity>
          </View>

          {activeEvents.length > 0 ? (
            <Card style={styles.transactionsCard}>
              {activeEvents.slice(0, 5).map((event) => (
                <View key={event.id} style={styles.transactionItem}>
                  <View style={[styles.transactionIcon, { backgroundColor: `${getEventColor(event.severity)}15` }]}>
                    <Ionicons name={getEventIcon(event.event_type)} size={20} color={getEventColor(event.severity)} />
                  </View>
                  <View style={styles.transactionInfo}>
                    <Text style={styles.transactionTitle}>{formatEventType(event.event_type)}</Text>
                    <Text style={styles.transactionDate}>
                      Zone {event.affected_zone} · {event.severity?.replace('_', ' ')} · {formatRelativeTime(event.event_start)}
                    </Text>
                  </View>
                  <Text style={styles.transactionPayout}>
                    {event.payout_rate ? `${(event.payout_rate * 100).toFixed(0)}%` : '—'}
                  </Text>
                </View>
              ))}
            </Card>
          ) : (
            <Card style={styles.transactionsCard}>
              <View style={styles.noEventsContainer}>
                <Ionicons name="shield-checkmark" size={32} color={COLORS.primary} />
                <Text style={styles.noEventsText}>No active disruptions</Text>
                <Text style={styles.noEventsSubtext}>Your areas are clear</Text>
              </View>
            </Card>
          )}
        </View>

        {/* ── Polling indicator ────────────────────────────────────── */}
        <View style={styles.pollingFooter}>
          <View style={styles.pollingDot} />
          <Text style={styles.pollingFooterText}>Live · Updates every 5s</Text>
        </View>

        <View style={styles.bottomSpacer} />
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: COLORS.background },
  loadingText: { fontSize: 14, color: COLORS.grey, marginTop: 12 },

  // Header
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 60, paddingBottom: 16,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', flex: 1 },
  greetingContainer: { marginLeft: 8, flex: 1 },
  greeting: { fontSize: 12, color: COLORS.grey },
  userName: { fontSize: 14, fontWeight: '600', color: COLORS.black },

  notificationButton: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: COLORS.white,
    justifyContent: 'center', alignItems: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3,
  },
  notificationActive: { backgroundColor: COLORS.primary },
  notificationDot: {
    position: 'absolute', top: 8, right: 8, width: 10, height: 10,
    borderRadius: 5, backgroundColor: '#F44336', borderWidth: 2, borderColor: COLORS.primary,
  },

  // Notification banner
  notificationBanner: {
    marginHorizontal: 20, marginBottom: 8, backgroundColor: COLORS.primary,
    borderRadius: 12, padding: 14,
  },
  notificationBannerContent: { flexDirection: 'row', alignItems: 'center' },
  notificationTitle: { color: '#fff', fontSize: 14, fontWeight: '700' },
  notificationBody: { color: '#ffffffcc', fontSize: 12, marginTop: 2 },

  // Status banner
  bannerContainer: {
    marginHorizontal: 20, marginBottom: 8, borderRadius: 10, padding: 12,
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#2196F3',
  },
  bannerWarning: { backgroundColor: '#FF9800' },
  bannerInfo: { backgroundColor: '#2196F3' },
  bannerSuccess: { backgroundColor: '#4CAF50' },
  bannerTitle: { color: '#fff', fontSize: 13, fontWeight: '700' },
  bannerBody: { color: '#ffffffcc', fontSize: 11, marginTop: 1 },
  bannerCTA: { color: '#fff', fontSize: 12, fontWeight: '700', textDecorationLine: 'underline' },

  // Events banner
  eventsBanner: {
    backgroundColor: '#D32F2F', marginHorizontal: 20, marginBottom: 8,
    borderRadius: 12, padding: 12,
  },
  eventsBannerHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  eventsBannerTitle: { color: COLORS.white, fontSize: 13, fontWeight: '700', marginLeft: 6 },
  eventsScroll: { marginTop: 4 },
  eventChip: {
    backgroundColor: '#fff', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8,
    marginRight: 8, flexDirection: 'row', alignItems: 'center',
    borderLeftWidth: 3,
  },
  eventChipType: { fontSize: 11, fontWeight: '600', color: COLORS.black },
  eventChipMeta: { fontSize: 9, color: COLORS.grey, marginTop: 1 },

  scrollContent: { paddingBottom: 100 },

  // Insurance card
  insuranceCardContainer: { paddingHorizontal: 20, marginBottom: 24, position: 'relative' },
  backgroundShape1: {
    position: 'absolute', width: 120, height: 120, borderRadius: 60,
    backgroundColor: `${COLORS.primary}20`, top: -20, right: -30,
  },
  backgroundShape2: {
    position: 'absolute', width: 80, height: 80, borderRadius: 40,
    backgroundColor: `${COLORS.success}20`, bottom: -10, left: -20,
  },
  insuranceCard: {
    backgroundColor: '#1B5E20', borderRadius: 24, padding: 24,
    position: 'relative', zIndex: 1,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 8, elevation: 6,
  },
  cardHeader: { marginBottom: 20 },
  phaseBadge: {
    backgroundColor: `${COLORS.white}30`, paddingHorizontal: 12, paddingVertical: 4,
    borderRadius: 12, alignSelf: 'flex-start', marginBottom: 8,
  },
  phaseBadgePaid: { backgroundColor: '#4CAF5050' },
  phaseBadgeSelection: { backgroundColor: '#FF980050' },
  phaseBadgeText: { color: COLORS.white, fontSize: 12, fontWeight: '600' },
  cardTitle: { fontSize: 20, fontWeight: '700', color: COLORS.white },

  coverageRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  coverageItem: { flex: 1 },
  coverageLabel: { fontSize: 12, color: `${COLORS.white}80`, marginBottom: 4 },
  coverageAmount: { fontSize: 24, fontWeight: '700', color: COLORS.white },
  premiumAmountText: { fontSize: 24, fontWeight: '700', color: COLORS.white, textAlign: 'right' },

  progressContainer: { marginBottom: 20 },
  progressLabel: { fontSize: 12, color: `${COLORS.white}80`, marginBottom: 8 },
  progressBar: { height: 8, backgroundColor: `${COLORS.white}30`, borderRadius: 4, marginBottom: 8 },
  progressFill: { height: '100%', backgroundColor: COLORS.white, borderRadius: 4 },
  progressPercentage: { fontSize: 14, fontWeight: '600', color: COLORS.white, textAlign: 'right' },

  cardDetails: { flexDirection: 'row', justifyContent: 'space-between' },
  detailItem: { flex: 1 },
  detailLabel: { fontSize: 10, color: `${COLORS.white}80`, marginBottom: 2 },
  detailValue: { fontSize: 12, fontWeight: '600', color: COLORS.white },

  // Section
  section: { paddingHorizontal: 20, marginBottom: 24 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: COLORS.black, marginBottom: 16 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  viewAllText: { fontSize: 13, color: COLORS.primary, fontWeight: '600' },

  earningsButton: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, gap: 4,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2, elevation: 2,
  },
  earningsButtonText: { fontSize: 14, fontWeight: '600', color: COLORS.primary },

  // Premium breakdown
  premiumCard: {
    backgroundColor: `${COLORS.primary}08`, borderRadius: 16, padding: 20,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3,
  },
  premiumInnerCard: {
    backgroundColor: `${COLORS.primary}10`, borderRadius: 12, padding: 16, marginBottom: 16,
  },
  premiumFormula: { fontSize: 13, fontWeight: '600', color: COLORS.black, marginBottom: 12, textAlign: 'center' },
  premiumValues: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  valueBox: {
    width: '48%', backgroundColor: COLORS.white, borderRadius: 8, padding: 12, marginBottom: 8,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2, elevation: 1,
  },
  valueLabel: { fontSize: 10, color: COLORS.grey, marginBottom: 4 },
  valueAmount: { fontSize: 14, fontWeight: '600', color: COLORS.black },

  breakdownResult: { paddingTop: 4 },
  breakdownRow: {
    flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6,
    borderBottomWidth: 1, borderBottomColor: '#f0f0f0',
  },
  breakdownLabel: { fontSize: 13, color: COLORS.grey },
  breakdownValue: { fontSize: 13, fontWeight: '500', color: COLORS.black },
  breakdownFinal: { borderBottomWidth: 0, paddingTop: 10, marginTop: 4 },
  breakdownFinalLabel: { fontSize: 15, fontWeight: '700', color: COLORS.primary },
  breakdownFinalValue: { fontSize: 15, fontWeight: '700', color: COLORS.primary },
  guardrailText: { fontSize: 11, color: COLORS.grey, fontStyle: 'italic', marginTop: 6 },

  // Quotes row
  quotesRow: { flexDirection: 'row', gap: 10 },
  quoteCard: {
    flex: 1, backgroundColor: '#fff', borderRadius: 12, padding: 14, alignItems: 'center',
    borderWidth: 1, borderColor: '#e0e0e0',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.08, shadowRadius: 3, elevation: 2,
  },
  quoteCardRecommended: { borderColor: COLORS.primary, borderWidth: 2 },
  recBadge: { fontSize: 8, fontWeight: '700', color: COLORS.primary, marginBottom: 4 },
  quoteTierName: { fontSize: 13, fontWeight: '600', color: COLORS.black, marginBottom: 4 },
  quoteAmount: { fontSize: 20, fontWeight: '700', color: COLORS.primary },
  quotePerWeek: { fontSize: 10, color: COLORS.grey, marginTop: 2 },

  // Transactions / events
  transactionsCard: {
    backgroundColor: COLORS.white, borderRadius: 16, padding: 16,
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3,
  },
  transactionItem: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#f5f5f5' },
  transactionIcon: {
    width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center',
  },
  transactionInfo: { flex: 1, marginLeft: 12 },
  transactionTitle: { fontSize: 14, fontWeight: '500', color: COLORS.black },
  transactionDate: { fontSize: 11, color: COLORS.grey, marginTop: 2 },
  transactionPayout: { fontSize: 14, fontWeight: '600', color: COLORS.primary },

  noEventsContainer: { alignItems: 'center', paddingVertical: 24 },
  noEventsText: { fontSize: 14, fontWeight: '600', color: COLORS.primary, marginTop: 8 },
  noEventsSubtext: { fontSize: 12, color: COLORS.grey, marginTop: 2 },

  // Polling footer
  pollingFooter: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 8, gap: 6,
  },
  pollingDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: COLORS.primary },
  pollingFooterText: { fontSize: 11, color: COLORS.grey },

  bottomSpacer: { height: 20 },
});

export default HomeDashboard;
