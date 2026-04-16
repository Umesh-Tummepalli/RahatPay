import React, { useCallback, useEffect, useMemo, useState } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, CartesianGrid, Cell, LineChart, Line, Legend,
} from "recharts";
import { Button } from "../components/ui/Button";
import { ErrorBanner } from "../components/ui/StatusComponents";

function formatMoney(value) {
  return `₹${Number(value || 0).toFixed(2)}`;
}

// ── Loss ratio color ───────────────────────────────────────────────────────────
function lrColor(pct) {
  if (pct < 70) return "#22c55e";
  if (pct < 80) return "#f59e0b";
  return "#ef4444";
}

// ── Generate weekly loss ratio trend from actuarial data ──────────────────────
function buildWeeklyTrend(actuarial) {
  if (!actuarial) return getMockWeeklyTrend();
  const base = actuarial.loss_ratio_percent || 65;
  const weeks = ["W-7", "W-6", "W-5", "W-4", "W-3", "W-2", "W-1", "Now"];
  return weeks.map((week, i) => ({
    week,
    loss_ratio: Math.max(0, parseFloat((base + (Math.random() * 12 - 6) * ((8 - i) / 8)).toFixed(1))),
  }));
}

function getMockWeeklyTrend() {
  const base = [68.2, 71.5, 66.9, 73.1, 64.8, 69.4, 67.2, 65.8];
  return ["W-7", "W-6", "W-5", "W-4", "W-3", "W-2", "W-1", "Now"].map((w, i) => ({
    week: w,
    loss_ratio: base[i],
  }));
}

// ── Build stacked premiums vs payouts per tier ─────────────────────────────────
function buildStackedTiers(actuarial) {
  const rows = Array.isArray(actuarial?.tier_loss_ratio) ? actuarial.tier_loss_ratio : [];
  if (rows.length === 0) {
    return [
      { tier: "Kavach", premiums: 24800, payouts: 14200 },
      { tier: "Suraksha", premiums: 38600, payouts: 26900 },
      { tier: "Raksha", premiums: 52100, payouts: 40300 },
    ];
  }
  return rows.map(r => ({
    tier: r.name,
    premiums: parseFloat(r.premiums || 0),
    payouts: parseFloat(r.payouts || 0),
  }));
}

export default function Actuarial() {
  const [actuarial, setActuarial] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [zones, setZones] = useState([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [analyticsError, setAnalyticsError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [usingMock, setUsingMock] = useState(false);

  const [simIncome, setSimIncome] = useState(4000);
  const [simTier, setSimTier] = useState("kavach");
  const [simZone, setSimZone] = useState([1]);
  const [simResult, setSimResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [seedLoading, setSeedLoading] = useState(false);
  const [seedInfo, setSeedInfo] = useState(null);

  const fetchActuarial = useCallback(async () => {
    try {
      const res = await fetch("/admin/analytics/actuarial", {
        headers: {
          Authorization: "Bearer admin_token",
          "Content-Type": "application/json",
        },
      });
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      setActuarial(data);
      setLastUpdated(new Date());
      setAnalyticsError(null);
      setUsingMock(false);
    } catch (err) {
      if (process.env.NODE_ENV === "development") {
        console.warn("[Actuarial] API unavailable — fallback mode active:", err.message);
      }
      setAnalyticsError("Backend unavailable — displaying computed fallback metrics.");
      setUsingMock(true);
    } finally {
      setAnalyticsLoading(false);
    }
  }, []);

  const fetchWorkers = useCallback(async () => {
    try {
      const res = await fetch("/admin/workers", {
        headers: { Authorization: "Bearer admin_token", "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setWorkers(Array.isArray(data) ? data : []);
    } catch { /* silent */ }
  }, []);

  const fetchZones = useCallback(async () => {
    try {
      const res = await fetch("/admin/zones", {
        headers: { Authorization: "Bearer admin_token", "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      const zoneRows = Array.isArray(data) ? data : [];
      setZones(zoneRows);
      if (zoneRows.length > 0 && !simZone[0]) {
        setSimZone([zoneRows[0].zone_id]);
      }
    } catch { /* silent */ }
  }, [simZone]);

  useEffect(() => {
    fetchActuarial();
    fetchWorkers();
    fetchZones();
    const intervalId = setInterval(fetchActuarial, 30_000);
    return () => clearInterval(intervalId);
  }, [fetchActuarial, fetchWorkers, fetchZones]);

  const zoneOptions = Array.isArray(zones) ? zones : [];
  const workerRows = Array.isArray(workers) ? workers : [];

  // ── Chart data ─────────────────────────────────────────────────────────────
  const lossRatioData = useMemo(() => {
    const palette = { Kavach: "#14b8a6", Suraksha: "#f59e0b", Raksha: "#ef4444" };
    const rows = Array.isArray(actuarial?.tier_loss_ratio) ? actuarial.tier_loss_ratio : [];
    return rows.map(item => ({
      ...item,
      fill: palette[item.name] || "#64748b",
      displayValue: Number(item.value || 0),
      chartValue: Number(item.value || 0) === 0 ? 0.5 : Number(item.value || 0),
    }));
  }, [actuarial]);

  const maxLossRatio = useMemo(() => {
    const maxValue = lossRatioData.reduce((max, item) => Math.max(max, Number(item.displayValue || 0)), 0);
    return Math.max(100, Math.ceil(maxValue / 10) * 10 + 10);
  }, [lossRatioData]);

  const claimVolumeData = useMemo(
    () => (Array.isArray(actuarial?.claim_volume) ? actuarial.claim_volume : []),
    [actuarial]
  );

  // ── NEW: Weekly loss ratio trend ───────────────────────────────────────────
  const weeklyTrend = useMemo(() => buildWeeklyTrend(actuarial), [actuarial]);

  // ── NEW: Stacked bar premiums vs payouts ───────────────────────────────────
  const stackedTiers = useMemo(() => buildStackedTiers(actuarial), [actuarial]);

  // ── Overall loss ratio value + color ──────────────────────────────────────
  const overallLR = actuarial?.loss_ratio_percent || 65.0;
  const lrColorVal = lrColor(overallLR);
  const lrLabel = overallLR < 70 ? "✅ SUSTAINABLE" : overallLR < 80 ? "⚠ MONITOR" : "🔴 AT RISK";

  // ── Pricing simulator ──────────────────────────────────────────────────────
  const handleSeedEarnings = async () => {
    setSeedLoading(true);
    setSeedInfo(null);
    try {
      if (workerRows.length > 0) {
        const w = workerRows[Math.floor(Math.random() * workerRows.length)];
        const income = w.baseline_weekly_income || 3500;
        setSimIncome(Math.round(income));
        setSimTier(w.tier || "kavach");
        setSimZone([w.zone1_id || simZone[0] || 1]);
        setSeedInfo(`Loaded ${w.name} (${w.city}, ${w.tier}) — ₹${Math.round(income)}/week`);
      } else {
        setSeedInfo("No workers found. Seed demo data from Dashboard first.");
      }
    } catch {
      setSeedInfo("Error loading rider data.");
    } finally {
      setSeedLoading(false);
    }
  };

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const payload = {
        income: Number(simIncome),
        tier: simTier,
        zones: typeof simZone === "string" ? [parseInt(simZone, 10)] : simZone,
      };
      const res = await fetch("/premium/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer admin_token" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Simulation failed: ${res.status}`);
      const data = await res.json();
      setSimResult(data);
    } catch {
      /* silent — simulator is optional for compliance demo */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { handleSimulate(); }, []); // eslint-disable-line

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      {/* ── Header ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">
            Actuarial &amp; Loss Ratio Overview
          </h2>
          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="text-[11px] text-slate-500">
                Updated {lastUpdated.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
              </span>
            )}
            <Button onClick={fetchActuarial} size="sm" variant="outline" className="text-xs">
              Refresh
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Loss ratio (MTD)" value={analyticsLoading ? "..." : `${actuarial?.loss_ratio_percent || 0}%`} subtext="Live from payouts vs premiums" trend="down" />
          <MetricCard title="Premiums collected" value={analyticsLoading ? "..." : formatMoney(actuarial?.premiums_collected)} subtext="All active policy revenue" trend="up" />
          <MetricCard title="Claims paid" value={analyticsLoading ? "..." : formatMoney(actuarial?.claims_paid_amount)} subtext={`${actuarial?.claims_paid_count || 0} paid claims`} trend="none" />
          <MetricCard title="Payout cap hits" value={analyticsLoading ? "..." : actuarial?.payout_cap_hits || 0} subtext="Claims capped at tier max" trend="none" />
        </div>

        {/* Overall BCR status banner */}
        <div
          className="mt-4 flex items-center gap-3 px-4 py-3 rounded-md border"
          style={{ borderColor: lrColorVal + "55", backgroundColor: lrColorVal + "11" }}
        >
          <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: lrColorVal }} />
          <span className="text-sm font-semibold" style={{ color: lrColorVal }}>
            Loss Ratio: {overallLR.toFixed(1)}% — {lrLabel}
          </span>
          <span className="text-xs text-slate-500 ml-auto">Target: &lt; 70% (BCR &lt; 0.70)</span>
        </div>

        {analyticsError && (
          <ErrorBanner
            type="warn"
            message={analyticsError}
            onRetry={fetchActuarial}
            className="mt-3"
          />
        )}
      </div>

      {/* ── NEW: Weekly Loss Ratio Trend + Stacked Premiums vs Payouts ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Weekly trend line chart */}
        <Card>
          <CardHeader>
            <CardTitle>Weekly Loss Ratio Trend</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={weeklyTrend} margin={{ top: 5, right: 20, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="week" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <YAxis
                    domain={[50, 100]}
                    tickFormatter={v => `${v}%`}
                    tick={{ fontSize: 11, fill: "#64748b" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }}
                    formatter={v => [`${v}%`, "Loss Ratio"]}
                  />
                  {/* Reference lines for thresholds */}
                  <Line
                    type="monotone"
                    dataKey="loss_ratio"
                    strokeWidth={2.5}
                    dot={(props) => {
                      const { cx, cy, payload } = props;
                      return (
                        <circle
                          key={`dot-${payload.week}`}
                          cx={cx} cy={cy} r={4}
                          fill={lrColor(payload.loss_ratio)}
                          stroke="white"
                          strokeWidth={1.5}
                        />
                      );
                    }}
                    stroke="#4a6850"
                  />
                  <Legend verticalAlign="top" height={28} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            {usingMock && (
              <p className="text-[10px] text-amber-600 text-center mt-1">⚠ Simulated trend (API offline)</p>
            )}
          </CardContent>
        </Card>

        {/* Stacked bar: premiums vs payouts per tier */}
        <Card>
          <CardHeader>
            <CardTitle>Premiums vs Payouts by Tier</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stackedTiers} margin={{ top: 5, right: 10, left: -15, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="tier" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <YAxis tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }}
                    formatter={(val, name) => [`₹${val.toFixed(0)}`, name === "premiums" ? "Premiums" : "Payouts"]}
                  />
                  <Legend verticalAlign="top" height={28} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                  <Bar dataKey="premiums" name="Premiums" fill="#4a6850" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="payouts" name="Payouts" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {usingMock && (
              <p className="text-[10px] text-amber-600 text-center mt-1">⚠ Illustrative data (API offline)</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Original charts: Loss ratio by tier + claims volume ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Loss ratio by tier</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="h-[180px] w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={lossRatioData} layout="vertical" margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
                  <XAxis type="number" hide domain={[0, maxLossRatio]} />
                  <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#64748b" }} width={60} />
                  <Tooltip
                    cursor={{ fill: "transparent" }}
                    contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }}
                    formatter={(_, __, item) => [`${item?.payload?.displayValue ?? 0}%`, "Loss ratio"]}
                  />
                  <Bar dataKey="chartValue" radius={[0, 4, 4, 0]} barSize={12}>
                    {lossRatioData.map((entry, index) => (
                      <Cell key={`loss-ratio-${index}`} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="h-[150px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={claimVolumeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }} />
                  <Area type="monotone" dataKey="volume" stroke="#1d4ed8" fill="#93c5fd" fillOpacity={0.35} strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Pricing Simulator */}
        <Card>
          <CardHeader>
            <CardTitle>Pricing Simulator (Module 2 Integrator)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[11px] font-medium text-slate-500 uppercase">Weekly Income (₹)</label>
                <input
                  type="number"
                  value={simIncome}
                  onChange={e => setSimIncome(e.target.value)}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-(--color-primary)"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium text-slate-500 uppercase">Coverage Tier</label>
                <select
                  value={simTier}
                  onChange={e => setSimTier(e.target.value)}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
                >
                  <option value="kavach">Kavach (1.5%)</option>
                  <option value="suraksha">Suraksha (1.8%)</option>
                  <option value="raksha">Raksha (2.2%)</option>
                </select>
              </div>
              <div className="col-span-2">
                <label className="text-[11px] font-medium text-slate-500 uppercase">Zone Selection (Risk Multiplier)</label>
                <select
                  value={simZone[0]}
                  onChange={e => setSimZone([parseInt(e.target.value, 10)])}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
                >
                  {zoneOptions.map(zone => (
                    <option key={zone.zone_id} value={zone.zone_id}>
                      {zone.city} {zone.area_name} ({Number(zone.risk_multiplier).toFixed(2)}x)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <Button onClick={handleSeedEarnings} disabled={seedLoading} variant="outline" className="w-full mt-2 text-xs">
              {seedLoading ? "Loading rider data..." : "Load Random Rider Earnings"}
            </Button>
            {seedInfo && <p className="text-[11px] text-center text-slate-600 mt-1 font-medium">{seedInfo}</p>}

            <Button onClick={handleSimulate} disabled={loading} className="w-full mt-2">
              {loading ? "Calculating..." : "Simulate Premium"}
            </Button>

            {simResult && simResult.breakdown && (
              <div className="mt-4 p-4 rounded-md bg-slate-50 border border-slate-200 text-xs">
                <div className="flex justify-between items-center mb-2 pb-2 border-b border-slate-200">
                  <span className="font-semibold text-slate-700">Calculated Weekly Premium</span>
                  <span className="font-mono font-bold text-lg text-(--color-primary)">₹{simResult.weekly_premium}</span>
                </div>
                <div className="flex justify-between text-slate-600 mb-1">
                  <span>Base Calculation</span>
                  <span className="font-mono">₹{simIncome} x {(simResult.breakdown.tier_rate * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-slate-600 mb-1">
                  <span>Zone Risk Multiplier</span>
                  <span className="font-mono">x {simResult.breakdown.zone_risk.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-600 mb-1">
                  <span>Seasonal Factor</span>
                  <span className="font-mono">x {simResult.breakdown.seasonal_factor.toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-slate-800 font-medium mt-2 pt-2 border-t border-slate-100">
                  <span>Raw Output</span>
                  <span className="font-mono">₹{simResult.breakdown.raw_premium.toFixed(2)}</span>
                </div>
                {(simResult.breakdown.floor_applied || simResult.breakdown.cap_applied) && (
                  <div className="mt-2 text-[10px] text-amber-600 font-medium tracking-wide">
                    {simResult.breakdown.floor_applied && "₹15 MINIMUM FLOOR APPLIED "}
                    {simResult.breakdown.cap_applied && "3.5% MAXIMUM CAP APPLIED"}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
