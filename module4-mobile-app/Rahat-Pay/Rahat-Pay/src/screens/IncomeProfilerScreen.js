import React, { useEffect, useState } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  SafeAreaView, 
  StatusBar, 
  ScrollView,
  ActivityIndicator
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS } from '../utils/constants';
import Logo from '../components/Logo';
import Card from '../components/Card';
import Button from '../components/Button';
import { apiClient } from '../services/apiService';
import { useAuth } from '../context/AuthContext';

const FALLBACK_PROFILE = {
  baseline_weekly_income: 4200,
  daily_income_history: Array.from({ length: 15 }, (_, index) => ({
    day: index + 1,
    amount: 450 + index * 20,
  })),
};

const IncomeProfilerScreen = ({ navigation }) => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const userId = user?.uid || 2;
        const resp = await apiClient.get('getIncomeProfile', userId);

        if (resp?.success && resp.data) {
          setProfile(resp.data);
        } else {
          setProfile(FALLBACK_PROFILE);
        }
      } catch (error) {
        console.warn('Failed to load income profile, using fallback profile:', error);
        setProfile(FALLBACK_PROFILE);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [user]);

  if (loading || !profile) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={COLORS.primary} />
          <Text style={{ marginTop: 10, color: COLORS.grey }}>Analyzing your 15-day history...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Calculate highest and finding bounds for a simple bar chart
  const history = profile.daily_income_history || [];
  const maxIncome = Math.max(...history.map(d => d.amount), 1);
  const days = [...history].sort((a,b) => b.day - a.day).slice(0, 15).reverse();

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" backgroundColor={COLORS.background} />
      
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.content}>
          <View style={styles.headerTop}>
            <Logo size="small" />
          </View>

          <Text style={styles.title}>Your Income Profile</Text>
          <Text style={styles.subtitle}>
            We analyzed your last 15 days of deliveries to calculate an objective baseline for your customized coverage.
          </Text>

          <Card style={styles.summaryCard}>
            <View style={styles.summaryRow}>
              <View>
                <Text style={styles.summaryLabel}>Baseline Weekly Income</Text>
                <Text style={styles.summaryValue}>₹{Math.round(profile.baseline_weekly_income).toLocaleString()}</Text>
              </View>
              <View style={styles.iconBox}>
                <Ionicons name="bar-chart" size={24} color={COLORS.primary} />
              </View>
            </View>
          </Card>

          <View style={styles.chartContainer}>
            <Text style={styles.chartTitle}>Past 15 Days Activity (Simulated)</Text>
            <View style={styles.chartArea}>
              {days.map((item, index) => {
                const heightPct = (item.amount / maxIncome) * 100;
                return (
                  <View key={index} style={styles.barWrapper}>
                    <View style={[styles.bar, { height: `${heightPct}%` }]} />
                    <Text style={styles.barLabel}>{item.day}</Text>
                  </View>
                );
              })}
            </View>
          </View>

          <View style={styles.infoBox}>
            <Ionicons name="information-circle-outline" size={20} color={COLORS.primary} style={{ marginTop: 2, marginRight: 8 }} />
            <Text style={styles.infoText}>
              Your premium will be calculated precisely as a customized percentage of your Baseline Weekly Income, maintaining complete fairness and affordability.
            </Text>
          </View>

          <Button
            title="Calculate My Premium"
            onPress={() => navigation.navigate('Plans', { profileData: profile })}
            style={styles.continueButton}
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  content: { padding: 20 },
  headerTop: { marginBottom: 20 },
  title: { fontSize: 24, fontWeight: '700', color: COLORS.black, marginBottom: 8 },
  subtitle: { fontSize: 14, color: COLORS.grey, marginBottom: 20, lineHeight: 20 },
  summaryCard: { backgroundColor: '#F0F9F1', borderColor: '#C3E6CB', borderWidth: 1, padding: 20, borderRadius: 12, marginBottom: 24 },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  summaryLabel: { fontSize: 13, color: '#4B6B50', marginBottom: 4 },
  summaryValue: { fontSize: 28, fontWeight: '700', color: COLORS.primary },
  iconBox: { width: 48, height: 48, borderRadius: 24, backgroundColor: '#FFFFFF', justifyContent: 'center', alignItems: 'center' },
  chartContainer: { backgroundColor: COLORS.white, borderRadius: 12, padding: 16, marginBottom: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 6, elevation: 2 },
  chartTitle: { fontSize: 14, fontWeight: '600', color: COLORS.black, marginBottom: 16 },
  chartArea: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end', height: 120, borderBottomWidth: 1, borderBottomColor: COLORS.lightGrey, paddingBottom: 8 },
  barWrapper: { alignItems: 'center', flex: 1 },
  bar: { backgroundColor: COLORS.primary, width: 8, borderRadius: 4, minHeight: 4 },
  barLabel: { fontSize: 8, color: COLORS.grey, marginTop: 4 },
  infoBox: { flexDirection: 'row', backgroundColor: '#F8FAFC', padding: 16, borderRadius: 12, marginBottom: 24 },
  infoText: { flex: 1, fontSize: 13, color: COLORS.grey, lineHeight: 18 },
  continueButton: { paddingVertical: 14 }
});

export default IncomeProfilerScreen;
