import React, { useState, useEffect, useCallback, useMemo } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ErrorBanner, LoadingSpinner } from "../components/ui/StatusComponents";
import * as api from "../lib/api";

// ── Seasonal lookup (fallback when Module 2 API is unavailable) ───────────────
// IRDAI: Pricing is zone-specific and seasonally adjusted per IRDAI parametric norms.
const SEASONAL_FACTORS = {
  1: 0.90, 2: 0.88, 3: 0.92, 4: 0.95, 5: 1.00, 6: 1.20,
  7: 1.25, 8: 1.25, 9: 1.15, 10: 1.05, 11: 0.95, 12: 0.90,
};

// ── Probability computation ────────────────────────────────────────────────────
function lerp(value, inputRange, outputRange) {
  const [inMin, inMax] = inputRange;
  const [outMin, outMax] = outputRange;
  const clamped = Math.max(inMin, Math.min(inMax, value));
  return outMin + ((clamped - inMin) / (inMax - inMin)) * (outMax - outMin);
}

function computeProbability(zone, seasonalFactor, hasRecentEvent) {
  const riskMult = parseFloat(zone.risk_multiplier) || 1.0;
  // IRDAI: base probability from zone risk multiplier (0.80–1.50 maps to 10–60%)
  const base_prob = lerp(riskMult, [0.80, 1.50], [0.10, 0.60]);
  const seasonal_boost = seasonalFactor;
  const recency_boost = hasRecentEvent ? 1.3 : 1.0;
  return Math.min(base_prob * seasonal_boost * recency_boost, 0.95);
}

function probColor(prob) {
  if (prob < 0.30) return { bar: "#22c55e", text: "text-emerald-700", badge: "green" };
  if (prob < 0.60) return { bar: "#f59e0b", text: "text-amber-700", badge: "amber" };
  return { bar: "#ef4444", text: "text-red-700", badge: "red" };
}

// ── Mock zone data ─────────────────────────────────────────────────────────────
const MOCK_ZONES = [
  { zone_id: 9,  city: "Mumbai",    area_name: "Dharavi",       risk_multiplier: 1.30 },
  { zone_id: 12, city: "Mumbai",    area_name: "Andheri East",  risk_multiplier: 1.35 },
  { zone_id: 19, city: "Delhi",     area_name: "Rohini",        risk_multiplier: 1.40 },
  { zone_id: 20, city: "Delhi",     area_name: "Saket",         risk_multiplier: 1.35 },
  { zone_id: 7,  city: "Mumbai",    area_name: "Bandra West",   risk_multiplier: 1.25 },
  { zone_id: 1,  city: "Chennai",   area_name: "T. Nagar",      risk_multiplier: 1.20 },
  { zone_id: 10, city: "Mumbai",    area_name: "Kurla",         risk_multiplier: 1.20 },
  { zone_id: 17, city: "Delhi",     area_name: "Lajpat Nagar",  risk_multiplier: 1.25 },
  { zone_id: 13, city: "Bangalore", area_name: "Indiranagar",   risk_multiplier: 1.00 },
  { zone_id: 14, city: "Bangalore", area_name: "Koramangala",   risk_multiplier: 1.05 },
  { zone_id: 5,  city: "Chennai",   area_name: "Adyar",         risk_multiplier: 1.00 },
  { zone_id: 6,  city: "Chennai",   area_name: "Velachery",     risk_multiplier: 0.95 },
];

export default function PredictiveAnalytics() {
  const [zones, setZones] = useState([]);
  const [zonesLoading, setZonesLoading] = useState(true);
  const [usingMock, setUsingMock] = useState(false);
  const [seasonalFactor, setSeasonalFactor] = useState(null);
  const [recentEventZones, setRecentEventZones] = useState(new Set());
  const [filterCity, setFilterCity] = useState("all");
  const [sortOrder, setSortOrder] = useState("desc");

  const currentMonth = new Date().getMonth() + 1;

  // ── Fetch zones ────────────────────────────────────────────────────────────
  const fetchZones = useCallback(async () => {
    try {
      // GET /admin/zones → Module 1 (:8000)
      const data = await api.getZones();
      const rows = Array.isArray(data) ? data : [];
      setZones(rows.length > 0 ? rows : MOCK_ZONES);
      setUsingMock(rows.length === 0);

      // Check which zones had recent events (last 7 days)
      const recentSet = new Set();
      rows.forEach(z => {
        const eventDate = z.latest_event_at ? new Date(z.latest_event_at) : null;
        const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        if (eventDate && eventDate >= sevenDaysAgo) {
          recentSet.add(z.zone_id);
        }
      });
      setRecentEventZones(recentSet);
    } catch {
      if (process.env.NODE_ENV === "development") {
        console.warn("[PredictiveAnalytics] Zone API unavailable — fallback mode active");
      }
      setZones(MOCK_ZONES);
      setUsingMock(true);
      setRecentEventZones(new Set([9, 19, 7]));
    } finally {
      setZonesLoading(false);
    }
  }, []);

  // ── Fetch seasonal factor for current month ────────────────────────────────
  const fetchSeasonal = useCallback(async () => {
    try {
      // GET /api/seasonal/{city}/{month} → Module 2 (:8002)
      const data = await api.getSeasonalFactor("Mumbai", currentMonth);
      setSeasonalFactor(data.seasonal_factor || SEASONAL_FACTORS[currentMonth]);
    } catch {
      setSeasonalFactor(SEASONAL_FACTORS[currentMonth] || 1.0);
    }
  }, [currentMonth]);

  useEffect(() => {
    fetchZones();
    fetchSeasonal();
  }, [fetchZones, fetchSeasonal]);

  // ── Compute zone probabilities ─────────────────────────────────────────────
  const scored = useMemo(() => {
    const sf = seasonalFactor || SEASONAL_FACTORS[currentMonth] || 1.0;
    return zones.map(z => ({
      ...z,
      probability: computeProbability(z, sf, recentEventZones.has(z.zone_id)),
      hasRecentEvent: recentEventZones.has(z.zone_id),
    }));
  }, [zones, seasonalFactor, recentEventZones, currentMonth]);

  // ── Filter + sort ──────────────────────────────────────────────────────────
  const cities = useMemo(() => ["all", ...new Set(zones.map(z => z.city).filter(Boolean))], [zones]);

  const filtered = useMemo(() => {
    let rows = filterCity === "all" ? scored : scored.filter(z => z.city === filterCity);
    return [...rows].sort((a, b) =>
      sortOrder === "desc" ? b.probability - a.probability : a.probability - b.probability
    );
  }, [scored, filterCity, sortOrder]);

  // ── Summary stats ──────────────────────────────────────────────────────────
  const highRiskCount = scored.filter(z => z.probability >= 0.60).length;
  const medRiskCount = scored.filter(z => z.probability >= 0.30 && z.probability < 0.60).length;
  const avgProbability = scored.length > 0
    ? (scored.reduce((s, z) => s + z.probability, 0) / scored.length * 100).toFixed(1)
    : "—";

  const sf = seasonalFactor || SEASONAL_FACTORS[currentMonth] || 1.0;
  const monthName = new Date(2000, currentMonth - 1, 1).toLocaleString("en-IN", { month: "long" });

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      {/* ── Header ── */}
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Predictive Zone Risk Analytics
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="High Risk Zones" value={zonesLoading ? "..." : highRiskCount} subtext="Probability ≥ 60%" trend="warn" />
          <MetricCard title="Medium Risk Zones" value={zonesLoading ? "..." : medRiskCount} subtext="30–60% probability" trend="none" />
          <MetricCard title="Avg. Zone Risk" value={zonesLoading ? "..." : `${avgProbability}%`} subtext="Across all active zones" trend="none" />
          <MetricCard
            title="Seasonal Factor"
            value={`${sf.toFixed(2)}x`}
            subtext={`${monthName} multiplier`}
            trend={sf > 1.1 ? "warn" : "none"}
          />
        </div>
      </div>

      {/* ── Banners ── */}
      {usingMock && (
        <ErrorBanner
          message="Zone API offline — showing illustrative risk scores based on zone configuration defaults."
          type="warn"
          onRetry={fetchZones}
        />
      )}
      <div className="p-3 rounded-md bg-blue-50 border border-blue-200 text-xs text-blue-800">
        📐 <strong>Formula:</strong>{" "}
        <span className="font-mono">
          probability = min(lerp(risk_mult, [0.80→1.50], [0.10→0.60]) × seasonal({sf.toFixed(2)}x) × recency_boost, 0.95)
        </span>
      </div>

      {/* ── Filter + sort controls ── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle>Zone Risk Scores — Sorted by Probability</CardTitle>
          <div className="flex gap-2">
            <select
              value={filterCity}
              onChange={e => setFilterCity(e.target.value)}
              className="text-xs bg-white border border-slate-200 rounded-md px-2 py-1.5 outline-none"
            >
              {cities.map(c => <option key={c} value={c}>{c === "all" ? "All cities" : c}</option>)}
            </select>
            <Button
              size="sm"
              variant="outline"
              className="text-xs"
              onClick={() => setSortOrder(o => o === "desc" ? "asc" : "desc")}
            >
              {sortOrder === "desc" ? "↓ Highest first" : "↑ Lowest first"}
            </Button>
            <Button size="sm" variant="outline" className="text-xs" onClick={fetchZones} disabled={zonesLoading}>
              {zonesLoading ? "…" : "↻ Retry"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {zonesLoading ? (
            <LoadingSpinner message="Computing zone risk scores…" />
          ) : filtered.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-xs">No zones found.</div>
          ) : (
            <div className="space-y-3">
              {filtered.map(zone => {
                const pct = (zone.probability * 100).toFixed(1);
                const colors = probColor(zone.probability);
                return (
                  <div key={zone.zone_id} className="flex items-center gap-4">
                    {/* Zone info */}
                    <div className="w-44 shrink-0">
                      <div className="text-xs font-semibold text-slate-800">
                        {zone.area_name || `Zone ${zone.zone_id}`}
                      </div>
                      <div className="text-[10px] text-slate-500">
                        {zone.city}
                        {zone.hasRecentEvent && (
                          <span className="ml-1.5 text-amber-600 font-medium">[Recent event]</span>
                        )}
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div className="flex-1 relative h-5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="absolute left-0 top-0 h-full rounded-full transition-all duration-700"
                        style={{ width: `${pct}%`, backgroundColor: colors.bar }}
                      />
                    </div>
                    {/* Percentage */}
                    <div className={`w-14 text-right text-sm font-bold shrink-0 ${colors.text}`}>
                      {pct}%
                    </div>
                    {/* Risk multiplier */}
                    <div className="w-10 text-[10px] text-slate-400 shrink-0 font-mono text-right">
                      {Number(zone.risk_multiplier).toFixed(2)}x
                    </div>
                    {/* Badge */}
                    <div className="w-16 shrink-0">
                      <Badge variant={colors.badge}>
                        {zone.probability >= 0.60 ? "HIGH" : zone.probability >= 0.30 ? "MEDIUM" : "LOW"}
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
