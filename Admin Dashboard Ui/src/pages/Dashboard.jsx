import React, { useState } from "react";
import { Badge } from "../components/ui/Badge";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from "recharts";
import { Button } from "../components/ui/Button";
import { useApi } from "../hooks/useApi";

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

// Helper to format timestamps
function formatTime(isoString) {
  if (!isoString) return "—";
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "—";
  }
}

// Helper to get event severity badge color
function getSeverityVariant(severity) {
  if (!severity) return "gray";
  const lower = String(severity).toLowerCase();
  if (lower.includes("extreme")) return "red";
  if (lower.includes("severe")) return "red";
  if (lower.includes("high")) return "amber";
  if (lower.includes("moderate")) return "blue";
  return "gray";
}

export default function Dashboard() {
  const { data: analytics, loading: analyticsLoading } = useApi('/admin/analytics/financial', null, { baseUrl: 'module1' });
  const { data: workers, loading: workersLoading } = useApi('/admin/workers', null, { baseUrl: 'module1' });
  const { data: fraudModule1, loading: fraudLoading } = useApi('/admin/fraud/flagged', null, { baseUrl: 'module1' });
  
  // Module 3 live data with 10-second polling
  const { data: pollingLog, loading: pollingLoading, error: pollingError } = useApi(
    '/api/triggers/polling-log',
    [],
    { baseUrl: 'module3', pollingInterval: 10000 }
  );
  const { data: activeDisruptions, loading: disruptionsLoading, error: disruptionsError } = useApi(
    '/api/triggers/active',
    [],
    { baseUrl: 'module3', pollingInterval: 10000 }
  );

  const [seeding, setSeeding] = useState(false);
  const [seedResult, setSeedResult] = useState(null);

  const handleSeedDemo = async () => {
    setSeeding(true);
    setSeedResult(null);
    try {
      const res = await fetch("http://localhost:8001/admin/seed-demo", {
        method: "POST",
        headers: {
          "Authorization": "Bearer admin_token",
          "Content-Type": "application/json"
        }
      });
      const data = await res.json();
      setSeedResult(data);
      // Reload page after brief delay to refresh all data
      setTimeout(() => window.location.reload(), 1500);
    } catch (err) {
      console.error(err);
      setSeedResult({ error: "Failed to seed. Are Module 1 and Module 2 running?" });
    } finally {
      setSeeding(false);
    }
  };

  // Safe array handling
  const pollingLogArray = Array.isArray(pollingLog?.entries)
    ? pollingLog.entries
    : Array.isArray(pollingLog)
      ? pollingLog
      : [];
  const activeDisruptionsArray = Array.isArray(activeDisruptions) ? activeDisruptions : [];

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold">
            Platform overview
          </h2>
          <div className="flex items-center gap-3">
            {seedResult && !seedResult.error && (
              <span className="text-xs text-green-600 font-medium animate-pulse">
                ✓ {seedResult.riders_created} riders seeded! Reloading...
              </span>
            )}
            {seedResult?.error && (
              <span className="text-xs text-red-500 font-medium">{seedResult.error}</span>
            )}
            <Button onClick={handleSeedDemo} disabled={seeding} size="sm" className="text-xs">
              {seeding ? "Seeding..." : "🎲 Seed Demo Data"}
            </Button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard 
            title="Total Workers" 
            value={workersLoading ? "..." : (workers ? workers.length : 0)} 
            subtext="Registered across all platforms" 
            trend="none" 
          />
          <MetricCard 
            title="Total Payouts" 
            value={analyticsLoading ? "..." : `₹${analytics?.total_payouts || 0}`} 
            subtext="All time" 
            trend="none" 
          />
          <MetricCard 
            title="Loss Ratio" 
            value={analyticsLoading ? "..." : `${((analytics?.loss_ratio || 0) * 100).toFixed(1)}%`} 
            subtext="Payouts / Premiums" 
            trend={analytics?.loss_ratio > 0.8 ? "warn" : "down"} 
          />
          <MetricCard 
            title="Total Premiums" 
            value={analyticsLoading ? "..." : `₹${analytics?.total_premiums || 0}`} 
            subtext="Collected so far" 
            trend="up" 
          />
        </div>
      </div>

      {/* Live Polling Feed and Active Disruptions (Module 3) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="border-t-4 border-t-blue-500">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>🔴 Live polling feed (Module 3)</CardTitle>
            <span className="text-xs font-medium text-blue-600">Updates every 10s</span>
          </CardHeader>
          <CardContent>
            {pollingError && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800 mb-3">
                ⚠️ Module 3 unavailable. Polling disabled. Make sure it's running on port 8003.
              </div>
            )}
            {pollingLoading && pollingLogArray.length === 0 ? (
              <div className="text-center py-4 text-slate-500 text-xs">Loading polling logs...</div>
            ) : pollingLogArray.length > 0 ? (
              <div className="max-h-[320px] overflow-y-auto space-y-2">
                {pollingLogArray.slice(0, 15).map((poll, i) => (
                  <div key={i} className="flex gap-2 border-b border-slate-100 pb-2 last:border-0 text-xs">
                    <div className="w-2 h-2 rounded-full mt-1 shrink-0 bg-blue-500 animate-pulse" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 justify-between">
                        <span className="font-medium text-slate-700">{poll.zone_name || poll.zone_id || "Zone"}</span>
                        <span className="text-[10px] text-slate-400">{formatTime(poll.timestamp)}</span>
                      </div>
                    <div className="text-[11px] text-slate-600 mt-0.5">
                        {poll.city && <span>{poll.city} · </span>}
                        <span className="capitalize">{poll.event_type || "Polling"}</span>
                        {poll.severity && <span> · {poll.severity}</span>}
                      </div>
                      {poll.measurements && (
                        <div className="text-[10px] text-slate-500 mt-1">
                          Rain {poll.measurements.rainfall_mm ?? "—"} · AQI {poll.measurements.aqi ?? "—"} · Temp {poll.measurements.temp_c ?? "—"}
                        </div>
                      )}
                      {poll.action_taken && (
                        <div className="text-[10px] text-green-700 mt-1">✓ {poll.action_taken}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 text-xs">No polling logs yet. Triggers will appear here.</div>
            )}
          </CardContent>
        </Card>

        <Card className="border-t-4 border-t-red-500">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>🚨 Active disruptions (Module 3)</CardTitle>
            <Badge variant={activeDisruptionsArray.length > 0 ? "red" : "green"}>
              {activeDisruptionsArray.length} active
            </Badge>
          </CardHeader>
          <CardContent>
            {disruptionsError && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800 mb-3">
                ⚠️ Module 3 unavailable. Make sure it's running on port 8003.
              </div>
            )}
            {disruptionsLoading && activeDisruptionsArray.length === 0 ? (
              <div className="text-center py-4 text-slate-500 text-xs">Loading active disruptions...</div>
            ) : activeDisruptionsArray.length > 0 ? (
              <div className="space-y-3">
                {activeDisruptionsArray.slice(0, 8).map((disruption, i) => (
                  <div key={i} className="p-3 rounded-md border-l-4 border-l-red-500 bg-red-50">
                    <div className="flex items-start justify-between mb-1">
                      <div>
                        <div className="font-medium text-sm text-slate-900">
                          {disruption.zone_name || disruption.zone_id || "Zone"}
                        </div>
                        <div className="text-xs text-slate-600 mt-0.5">
                          {disruption.city && <span>{disruption.city} · </span>}
                          <span className="capitalize">{disruption.event_type || "Unknown"}</span>
                        </div>
                      </div>
                      <Badge variant={getSeverityVariant(disruption.severity)}>
                        {disruption.severity || "N/A"}
                      </Badge>
                    </div>
                    {disruption.description && (
                      <p className="text-xs text-slate-600 mt-2">{disruption.description}</p>
                    )}
                    <div className="text-[10px] text-slate-500 mt-2 flex justify-between">
                      <span>Started: {formatTime(disruption.start_time)}</span>
                      {disruption.end_time && <span>End: {formatTime(disruption.end_time)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 text-xs">No active disruptions. All systems nominal!</div>
            )}
          </CardContent>
        </Card>
      </div>

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
               <div className="text-center py-4 text-slate-500 text-xs">Loading...</div>
            ) : fraudModule1 && fraudModule1.flagged_users ? (
              fraudModule1.flagged_users.slice(0, 4).map((f, i) => (
                <div key={i} className="flex gap-3 items-start border-b border-slate-100 pb-3 last:border-0">
                  <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 shadow-[0_0_5px_var(--color-danger)] ${f.risk_score > 0.9 ? 'bg-(--color-danger)' : 'bg-(--color-warning)'}`} />
                  <div>
                    <p className="text-sm text-slate-800 leading-tight">Rider {f.rider_id}</p>
                    <p className="text-[11px] text-slate-500 mt-1">{f.reason?.substring(0, 80)}{f.reason?.length > 80 ? '...' : ''}</p>
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
          <CardHeader className="flex flex-row items-center justify-between">
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
                    <tr><td colSpan="5" className="py-4 text-center">Loading...</td></tr>
                  ) : workers && workers.length > 0 ? (
                    workers.slice(0, 5).map((w, i) => (
                      <tr key={i} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 pr-4 font-medium">{w.name}</td>
                        <td className="py-3 pr-4 text-slate-600 capitalize">{w.platform}</td>
                        <td className="py-3 pr-4 text-slate-600">{w.city}</td>
                        <td className="py-3 pr-4"><Badge variant={w.tier === 'raksha' ? 'amber' : w.tier === 'suraksha' ? 'blue' : 'gray'}>{w.tier}</Badge></td>
                        <td className="py-3">{w.is_blocked ? <Badge variant="red">Blocked</Badge> : <Badge variant="green">Active</Badge>}</td>
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Claims by trigger</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="h-[200px] w-full mt-[-20px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={claimsByTriggerData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {claimsByTriggerData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Subscription split</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="h-[200px] w-full mt-[-20px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={subscriptionSplitData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {subscriptionSplitData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Platform health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pb-4">
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Module 1 — Registration</span>
              <Badge variant="green">Port 8001</Badge>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Module 2 — Risk Engine</span>
              <Badge variant="green">Port 8002</Badge>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Module 3 — Claims Engine</span>
              <Badge variant={disruptionsError ? "amber" : "green"}>Port 8003</Badge>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">PostgreSQL DB</span>
              <Badge variant="green">Connected</Badge>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Admin Dashboard</span>
              <Badge variant="green">Live</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
