import React, { useState, useEffect } from "react";
import { Badge } from "../components/ui/Badge";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from "recharts";
import { Button } from "../components/ui/Button";
import { useApi } from "../hooks/useApi";

const ADMIN_HEADERS = {
  "Authorization": "Bearer admin_token",
  "Content-Type": "application/json",
};

const claimsByTriggerData = [
  { name: 'Rain', value: 72, color: 'var(--color-primary)' },
  { name: 'App outage', value: 14, color: '#3cbd9b' },
  { name: 'Lockdown', value: 9, color: 'var(--color-warning)' },
  { name: 'Other', value: 5, color: '#94a3b8' },
];

const subscriptionSplitData = [
  { name: 'Kavach', value: 6740, color: '#94a3b8' },
  { name: 'Suraksha', value: 3870, color: 'var(--color-primary)' },
  { name: 'Raksha', value: 1871, color: 'var(--color-warning)' },
];

const ATTACK_TYPES = [
  { key: 'gps_spoofing',        label: 'GPS Spoofing',         icon: '📍' },
  { key: 'baseline_inflation',  label: 'Baseline Inflation',   icon: '📈' },
  { key: 'velocity_exploit',    label: 'Velocity Exploit',     icon: '⚡' },
  { key: 'collusion_ring',      label: 'Collusion Ring',       icon: '🕸️' },
];

const DISASTER_TYPES = [
  { value: 'heavy_rain',       label: 'Heavy Rain' },
  { value: 'flood',            label: 'Flood' },
  { value: 'cyclone',          label: 'Cyclone' },
  { value: 'extreme_heat',     label: 'Extreme Heat' },
  { value: 'poor_aqi',         label: 'Poor AQI' },
  { value: 'civic_disruption', label: 'Civic Disruption' },
];

export default function Dashboard() {
  const { data: analytics, loading: analyticsLoading } = useApi('/admin/analytics/financial');
  const { data: workers, loading: workersLoading } = useApi('/admin/workers');
  const { data: fraud, loading: fraudLoading } = useApi('/admin/fraud/flagged');

  // ── Seed demo data ────────────────────────────────────────────────────────
  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState(null);

  const handleSeedDemo = async () => {
    setSeeding(true);
    setSeedResult(null);
    try {
      const res = await fetch("/admin/seed-demo", { method: "POST", headers: ADMIN_HEADERS });
      const data = await res.json();
      setSeedResult(data);
      setTimeout(() => window.location.reload(), 1500);
    } catch (err) {
      setSeedResult({ error: "Failed to seed. Are Module 1 and Module 2 running?" });
    } finally {
      setSeeding(false);
    }
  };

  // ── Attack simulation ─────────────────────────────────────────────────────
  const [attackLoading, setAttackLoading] = useState(null); // key of active attack
  const [attackResult, setAttackResult] = useState(null);

  const handleSimulateAttack = async (attackType) => {
    setAttackLoading(attackType);
    setAttackResult(null);
    try {
      const res = await fetch("/admin/simulate-attack", {
        method: "POST",
        headers: ADMIN_HEADERS,
        body: JSON.stringify({ attack_type: attackType }),
      });
      const data = await res.json();
      setAttackResult({ success: true, ...data });
    } catch (err) {
      setAttackResult({ success: false, error: err.message });
    } finally {
      setAttackLoading(null);
    }
  };

  // ── Disaster simulation ───────────────────────────────────────────────────
  const [disasterForm, setDisasterForm] = useState({
    event_type: 'heavy_rain',
    severity: 'severe_l1',
    affected_zone: 9,
    lost_hours: 5,
    severity_rate: 0.60,
  });
  const [disasterLoading, setDisasterLoading] = useState(false);
  const [disasterResult, setDisasterResult] = useState(null);

  const handleSimulateDisaster = async () => {
    setDisasterLoading(true);
    setDisasterResult(null);
    try {
      const res = await fetch("/admin/simulate-disaster", {
        method: "POST",
        headers: ADMIN_HEADERS,
        body: JSON.stringify(disasterForm),
      });
      const data = await res.json();
      setDisasterResult({ success: res.ok, ...data });
    } catch (err) {
      setDisasterResult({ success: false, error: err.message });
    } finally {
      setDisasterLoading(false);
    }
  };

  // ── Platform health checks ────────────────────────────────────────────────
  const [healthStatus, setHealthStatus] = useState({
    module1: null, module2: null, module3: null,
  });

  useEffect(() => {
    const check = async () => {
      const checks = await Promise.all([
        fetch('/health').then(r => r.ok).catch(() => false),
        fetch('/m2/health').then(r => r.ok).catch(() => false),
        fetch('/m3/health').then(r => r.ok).catch(() => false),
      ]);
      setHealthStatus({ module1: checks[0], module2: checks[1], module3: checks[2] });
    };
    check();
    const id = setInterval(check, 15000);
    return () => clearInterval(id);
  }, []);

  const healthBadge = (up) => {
    if (up === null) return <Badge variant="gray">Checking…</Badge>;
    return up ? <Badge variant="green">Online</Badge> : <Badge variant="red">Offline</Badge>;
  };

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      {/* ── Header row ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">
            Platform overview
          </h2>
          <div className="flex items-center gap-3">
            {seedResult && !seedResult.error && (
              <span className="text-xs text-green-600 font-medium animate-pulse">
                ✓ {seedResult.riders_created} riders seeded! Reloading…
              </span>
            )}
            {seedResult?.error && (
              <span className="text-xs text-red-500 font-medium">{seedResult.error}</span>
            )}
            <Button onClick={handleSeedDemo} disabled={seeding} size="sm" className="text-xs">
              {seeding ? "Seeding…" : "🎲 Seed Demo Data"}
            </Button>
          </div>
        </div>

        {/* ── KPI cards ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Workers"
            value={workersLoading ? "…" : (workers ? workers.length : 0)}
            subtext="Registered across all platforms"
            trend="none"
          />
          <MetricCard
            title="Total Payouts"
            value={analyticsLoading ? "…" : `₹${analytics?.total_payouts || 0}`}
            subtext="All time"
            trend="none"
          />
          <MetricCard
            title="Loss Ratio"
            value={analyticsLoading ? "…" : `${((analytics?.loss_ratio || 0) * 100).toFixed(1)}%`}
            subtext="Payouts / Premiums"
            trend={analytics?.loss_ratio > 0.8 ? "warn" : "down"}
          />
          <MetricCard
            title="Total Premiums"
            value={analyticsLoading ? "…" : `₹${analytics?.total_premiums || 0}`}
            subtext="Collected so far"
            trend="up"
          />
        </div>
      </div>

      {/* ── Fraud alerts + Worker summary ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Fraud alerts</CardTitle>
            <span className="text-xs text-(--color-primary) hover:underline cursor-pointer font-medium">
              View all →
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            {fraudLoading ? (
              <div className="text-center py-4 text-slate-500 text-xs">Loading…</div>
            ) : fraud?.flagged_users?.length > 0 ? (
              fraud.flagged_users.slice(0, 4).map((f, i) => (
                <div key={i} className="flex gap-3 items-start border-b border-slate-100 pb-3 last:border-0">
                  <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 shadow-[0_0_5px_var(--color-danger)] ${f.risk_score > 0.9 ? 'bg-(--color-danger)' : 'bg-(--color-warning)'}`} />
                  <div>
                    <p className="text-sm text-slate-800 leading-tight">Rider {f.rider_id}</p>
                    <p className="text-[11px] text-slate-500 mt-1">{f.reason?.substring(0, 80)}{f.reason?.length > 80 ? '…' : ''}</p>
                    {f.exploit_type && (
                      <span className="inline-block mt-1 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-red-50 text-red-600 border border-red-100">{f.exploit_type.replace('_', ' ')}</span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-slate-500 text-xs">No active alerts</div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Worker summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Name</th>
                    <th className="pb-3 pr-4 font-semibold">Platform</th>
                    <th className="pb-3 pr-4 font-semibold">City</th>
                    <th className="pb-3 pr-4 font-semibold">Tier</th>
                    <th className="pb-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {workersLoading ? (
                    <tr><td colSpan="5" className="py-4 text-center">Loading…</td></tr>
                  ) : workers?.length > 0 ? (
                    workers.slice(0, 5).map((w, i) => (
                      <tr key={i} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 pr-4 font-medium">{w.name}</td>
                        <td className="py-3 pr-4 text-slate-600 capitalize">{w.platform}</td>
                        <td className="py-3 pr-4 text-slate-600">{w.city}</td>
                        <td className="py-3 pr-4">
                          <Badge variant={w.tier === 'raksha' ? 'amber' : w.tier === 'suraksha' ? 'blue' : 'gray'}>{w.tier}</Badge>
                        </td>
                        <td className="py-3">
                          {w.is_blocked ? <Badge variant="red">Blocked</Badge> : <Badge variant="green">Active</Badge>}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="5" className="py-4 text-center text-slate-500">No workers yet. Click "Seed Demo Data" above.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Charts + Platform health ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader><CardTitle>Claims by trigger</CardTitle></CardHeader>
          <CardContent className="pt-2">
            <div className="h-[200px] w-full mt-[-20px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={claimsByTriggerData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {claimsByTriggerData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Subscription split</CardTitle></CardHeader>
          <CardContent className="pt-2">
            <div className="h-[200px] w-full mt-[-20px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={subscriptionSplitData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {subscriptionSplitData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <RechartsTooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }} />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Platform health — live checks */}
        <Card>
          <CardHeader><CardTitle>Platform health</CardTitle></CardHeader>
          <CardContent className="space-y-4 pb-4">
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Module 1 — Registration</span>
              {healthBadge(healthStatus.module1)}
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Module 2 — Risk Engine</span>
              {healthBadge(healthStatus.module2)}
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Module 3 — Claims Engine</span>
              {healthBadge(healthStatus.module3)}
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">PostgreSQL DB</span>
              <Badge variant={healthStatus.module1 ? "green" : "gray"}>
                {healthStatus.module1 ? "Connected" : "Unknown"}
              </Badge>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Admin Dashboard</span>
              <Badge variant="green">Live</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Simulation Controls ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Attack simulation */}
        <Card>
          <CardHeader>
            <CardTitle>🛡️ Simulate Fraud Attack</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Triggers a fraud scenario on the demo rider (Imran Shaikh). The mobile app will receive a live push notification via 5-second polling.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {ATTACK_TYPES.map(({ key, label, icon }) => (
                <button
                  key={key}
                  disabled={!!attackLoading}
                  onClick={() => handleSimulateAttack(key)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 hover:bg-red-50 hover:border-red-200 transition-colors text-xs font-medium text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>{icon}</span>
                  <span>{attackLoading === key ? "Simulating…" : label}</span>
                </button>
              ))}
            </div>

            {attackResult && (
              <div className={`mt-3 p-3 rounded-lg text-xs ${attackResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                {attackResult.success ? (
                  <>
                    <p className="font-semibold text-green-800">✓ {attackResult.title}</p>
                    <p className="text-green-700 mt-1">{attackResult.countermeasure}</p>
                    <p className="text-green-600 mt-1 font-mono text-[10px]">
                      Risk score: {(attackResult.risk_score * 100).toFixed(0)}% · Notification pushed to app: {attackResult.mobile_notification_pushed ? "Yes" : "No"}
                    </p>
                  </>
                ) : (
                  <p className="text-red-700">{attackResult.error || "Simulation failed"}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Disaster / seasonal event simulation */}
        <Card>
          <CardHeader>
            <CardTitle>🌧️ Simulate Seasonal / Disaster Event</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Creates a parametric trigger event. The demo rider's app will receive a payout notification within 5 seconds via polling.
            </p>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Event type</label>
                <select
                  value={disasterForm.event_type}
                  onChange={e => setDisasterForm(f => ({ ...f, event_type: e.target.value }))}
                  className="w-full border border-slate-200 rounded-md text-xs px-2 py-1.5 bg-white"
                >
                  {DISASTER_TYPES.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Severity</label>
                <select
                  value={disasterForm.severity}
                  onChange={e => setDisasterForm(f => ({ ...f, severity: e.target.value }))}
                  className="w-full border border-slate-200 rounded-md text-xs px-2 py-1.5 bg-white"
                >
                  <option value="moderate">Moderate (30%)</option>
                  <option value="severe_l1">Severe L1 (45–60%)</option>
                  <option value="severe_l2">Severe L2 (60–75%)</option>
                  <option value="extreme">Extreme (75%+)</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Zone ID (1–20)</label>
                <input
                  type="number" min={1} max={20}
                  value={disasterForm.affected_zone}
                  onChange={e => setDisasterForm(f => ({ ...f, affected_zone: Number(e.target.value) }))}
                  className="w-full border border-slate-200 rounded-md text-xs px-2 py-1.5"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Lost hours</label>
                <input
                  type="number" min={1} max={12} step={0.5}
                  value={disasterForm.lost_hours}
                  onChange={e => setDisasterForm(f => ({ ...f, lost_hours: Number(e.target.value) }))}
                  className="w-full border border-slate-200 rounded-md text-xs px-2 py-1.5"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Severity rate (0–1)</label>
                <input
                  type="number" min={0.1} max={1} step={0.05}
                  value={disasterForm.severity_rate}
                  onChange={e => setDisasterForm(f => ({ ...f, severity_rate: Number(e.target.value) }))}
                  className="w-full border border-slate-200 rounded-md text-xs px-2 py-1.5"
                />
              </div>

              <div className="flex items-end">
                <Button
                  onClick={handleSimulateDisaster}
                  disabled={disasterLoading}
                  className="w-full text-xs"
                >
                  {disasterLoading ? "Simulating…" : "🚨 Trigger Event"}
                </Button>
              </div>
            </div>

            {disasterResult && (
              <div className={`mt-2 p-3 rounded-lg text-xs ${disasterResult.success ? 'bg-blue-50 border border-blue-200' : 'bg-red-50 border border-red-200'}`}>
                {disasterResult.success ? (
                  <>
                    <p className="font-semibold text-blue-800">✓ Event created (ID #{disasterResult.event_id})</p>
                    <p className="text-blue-700 mt-1">{disasterResult.message}</p>
                    <p className="text-blue-600 font-mono text-[10px] mt-1">
                      Estimated payout: ₹{disasterResult.total_payout_estimated?.toFixed(0)} · Claims: {disasterResult.claims_created} · Notification: {disasterResult.mobile_notification_pushed ? "Pushed ✓" : "Pending"}
                    </p>
                  </>
                ) : (
                  <p className="text-red-700">{disasterResult.error || disasterResult.detail || "Simulation failed"}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
