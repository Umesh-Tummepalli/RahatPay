import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  AppState
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import { useAuth } from '../context/AuthContext';

const POLL_INTERVAL = 5000;

const EarningsHistoryScreen = ({ navigation }) => {
  const { user, getUserEarnings, riderId } = useAuth();
  const [earnings, setEarnings] = useState(null);
  const [earningsLoading, setEarningsLoading] = useState(false);
  const mountedRef = useRef(true);
  const appStateRef = useRef(AppState.currentState);

  const effectiveRiderId = riderId || 2;

  const fetchEarnings = useCallback(async () => {
    try {
      const result = await getUserEarnings(effectiveRiderId, 15);
      if (result.success && mountedRef.current) {
        setEarnings(result.data);
      }
    } catch (err) {
      console.warn('Earnings fetch error:', err);
    } finally {
      if (mountedRef.current) setEarningsLoading(false);
    }
  }, [effectiveRiderId, getUserEarnings]);

  // Initial fetch + 5-second polling
  useEffect(() => {
    mountedRef.current = true;
    setEarningsLoading(true);
    fetchEarnings();

    const interval = setInterval(() => {
      if (appStateRef.current === 'active') {
        fetchEarnings();
      }
    }, POLL_INTERVAL);

    return () => {
      mountedRef.current = false;
      clearInterval(interval);
    };
  }, [fetchEarnings]);

  // Pause polling when app backgrounded
  useEffect(() => {
    const sub = AppState.addEventListener('change', (next) => {
      appStateRef.current = next;
    });
    return () => sub?.remove();
  }, []);

  const formatCurrency = (amount) => {
    const n = Number(amount);
    return Number.isFinite(n) ? `₹${n.toFixed(2)}` : '₹0.00';
  };

  const formatHours = (hours) => {
    const n = Number(hours);
    return Number.isFinite(n) ? n.toFixed(1) : '0.0';
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  };

  const hasData = earnings && Array.isArray(earnings.daily_history) && earnings.daily_history.length > 0;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={COLORS.primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Earnings History</Text>
        <TouchableOpacity onPress={fetchEarnings} style={styles.backButton}>
          <Ionicons name="refresh" size={20} color={COLORS.primary} />
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={earningsLoading}
            onRefresh={fetchEarnings}
            colors={[COLORS.primary]}
            tintColor={COLORS.primary}
          />
        }
      >
        {/* Summary Cards — only shown when server has data */}
        {hasData && (
          <View style={styles.summaryContainer}>
            <View style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Total Earnings</Text>
              <Text style={styles.summaryValue}>{formatCurrency(earnings.total_earnings)}</Text>
              <Text style={styles.summarySubtext}>{earnings.days ?? 0} days</Text>
            </View>

            <View style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Avg Daily</Text>
              <Text style={styles.summaryValue}>{formatCurrency(earnings.avg_daily_earnings)}</Text>
              <Text style={styles.summarySubtext}>per day</Text>
            </View>

            <View style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>Total Hours</Text>
              <Text style={styles.summaryValue}>{formatHours(earnings.total_hours)}</Text>
              <Text style={styles.summarySubtext}>hours worked</Text>
            </View>
          </View>
        )}

        {/* Baseline Info — from server */}
        {earnings?.baseline && (
          <View style={styles.baselineCard}>
            <Text style={styles.cardTitle}>Your Baseline Profile</Text>
            <View style={styles.baselineRow}>
              <Text style={styles.baselineLabel}>Weekly Income:</Text>
              <Text style={styles.baselineValue}>
                {formatCurrency(earnings.baseline.weekly_income)}
              </Text>
            </View>
            <View style={styles.baselineRow}>
              <Text style={styles.baselineLabel}>Weekly Hours:</Text>
              <Text style={styles.baselineValue}>
                {formatHours(earnings.baseline.weekly_hours)} hrs
              </Text>
            </View>
            <View style={styles.baselineRow}>
              <Text style={styles.baselineLabel}>Hourly Rate:</Text>
              <Text style={styles.baselineValue}>
                {formatCurrency(
                  (() => {
                    const wi = Number(earnings.baseline.weekly_income);
                    const wh = Number(earnings.baseline.weekly_hours);
                    if (!Number.isFinite(wi) || !Number.isFinite(wh) || wh === 0) return 0;
                    return wi / wh;
                  })()
                )}
              </Text>
            </View>
          </View>
        )}

        {/* Daily History — from server */}
        {hasData && (
          <View style={styles.historyCard}>
            <Text style={styles.cardTitle}>Daily Breakdown</Text>
            {earnings.daily_history.map((day, index) => (
              <View key={index} style={styles.dayRow}>
                <View style={styles.dayInfo}>
                  <Text style={styles.dayDate}>{formatDate(day.date)}</Text>
                  <Text style={styles.dayHours}>{formatHours(day.hours)} hrs · {day.orders ?? 0} orders</Text>
                </View>
                <View style={styles.dayEarnings}>
                  <Text style={[
                    styles.dayAmount,
                    day.income === 0 && styles.dayAmountZero
                  ]}>
                    {formatCurrency(day.income)}
                  </Text>
                  {day.income === 0 && (
                    <Text style={styles.dayOffLabel}>Day Off</Text>
                  )}
                </View>
              </View>
            ))}
          </View>
        )}

        {/* Loading State */}
        {earningsLoading && !hasData && (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={COLORS.primary} />
            <Text style={styles.loadingText}>Loading earnings…</Text>
          </View>
        )}

        {/* Empty State — explains that admin must seed data */}
        {!hasData && !earningsLoading && (
          <View style={styles.emptyContainer}>
            <View style={styles.emptyIconCircle}>
              <Ionicons name="time-outline" size={48} color={COLORS.primary} />
            </View>
            <Text style={styles.emptyTitle}>Earnings Data Pending</Text>
            <Text style={styles.emptyText}>
              Your activity data is being set up by the system. This screen will automatically update once your earnings history is available.
            </Text>
            <View style={styles.pollingBadge}>
              <View style={styles.pollingDot} />
              <Text style={styles.pollingText}>Checking every 5 seconds…</Text>
            </View>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    paddingTop: 50,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.primary,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  summaryContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
    gap: 12,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  summaryLabel: {
    fontSize: 12,
    color: COLORS.grey,
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 18,
    fontWeight: '700',
    color: COLORS.primary,
    marginBottom: 2,
  },
  summarySubtext: {
    fontSize: 10,
    color: COLORS.grey,
  },
  baselineCard: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.primary,
    marginBottom: 16,
  },
  baselineRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  baselineLabel: {
    fontSize: 14,
    color: COLORS.grey,
  },
  baselineValue: {
    fontSize: 14,
    fontWeight: '600',
    color: COLORS.black,
  },
  historyCard: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  dayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  dayInfo: {
    flex: 1,
  },
  dayDate: {
    fontSize: 14,
    fontWeight: '500',
    color: COLORS.black,
    marginBottom: 2,
  },
  dayHours: {
    fontSize: 12,
    color: COLORS.grey,
  },
  dayEarnings: {
    alignItems: 'flex-end',
  },
  dayAmount: {
    fontSize: 16,
    fontWeight: '600',
    color: COLORS.success,
  },
  dayAmountZero: {
    color: COLORS.grey,
  },
  dayOffLabel: {
    fontSize: 10,
    color: COLORS.grey,
    fontStyle: 'italic',
  },
  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: COLORS.grey,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 24,
  },
  emptyIconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: `${COLORS.primary}15`,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: COLORS.black,
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    color: COLORS.grey,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 20,
  },
  pollingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: `${COLORS.primary}10`,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    gap: 8,
  },
  pollingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.primary,
  },
  pollingText: {
    fontSize: 12,
    color: COLORS.primary,
    fontWeight: '500',
  },
});

export default EarningsHistoryScreen;
