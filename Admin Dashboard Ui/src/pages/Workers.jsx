import React, { useState, useCallback } from "react";
import { Badge } from "../components/ui/Badge";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { useApi } from "../hooks/useApi";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const PHASE_BADGE = {
  trial_active: { variant: "blue", label: "Trial Active" },
  plan_selection: { variant: "amber", label: "Plan Selection" },
  paid_active: { variant: "green", label: "Active Plan" },
};

const TIER_COLORS = {
  kavach: "#94a3b8",
  suraksha: "var(--color-primary)",
  raksha: "var(--color-warning)",
};

function SeedButton({ worker, onSeedComplete }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSeed = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8001/admin/workers/${worker.id}/seed-sample-data`, {
        method: "POST",
        headers: {
          "Authorization": "Bearer admin_token",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          rider_id: worker.id,
          days: 15,
          base_hourly_rate: 70.0,
          avg_hours_per_day: 5.0,
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
      onSeedComplete(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [worker.id, onSeedComplete]);

  return (
    <div className="flex items-center gap-1">
      <Button
        variant={worker.has_seeded_history ? "outline" : "default"}
        size="sm"
        className="h-6 text-[10px] px-2 whitespace-nowrap"
        onClick={handleSeed}
        disabled={loading}
      >
        {loading ? (
          <span className="flex items-center gap-1">
            <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
            </svg>
            Seeding…
          </span>
        ) : worker.has_seeded_history ? "↻ Re-seed Data" : "🌱 Seed 15-Day Data"}
      </Button>
      {error && <span className="text-[9px] text-red-500 max-w-[100px] truncate" title={error}>✗ {error}</span>}
    </div>
  );
}

function PremiumQuotesPanel({ seedResult }) {
  if (!seedResult) return null;

  const { premium_quotes, new_baseline, daily_history, trial_transition } = seedResult;

  const chartData = (daily_history || []).map((d, i) => ({
    day: i + 1,
    income: d.income,
    hours: d.hours,
  }));

  return (
    <div className="space-y-4">
      {/* Transition info */}
      {trial_transition && (
        <div className="flex flex-wrap gap-2 text-[10px]">
          <span className="bg-blue-50 text-blue-700 border border-blue-100 px-2 py-0.5 rounded-md font-mono">
            {trial_transition.from_phase} → {trial_transition.to_phase}
          </span>
          {trial_transition.first_seed && (
            <span className="bg-green-50 text-green-700 border border-green-100 px-2 py-0.5 rounded-md">
              First seed ✓
            </span>
          )}
          {trial_transition.notification_pending && (
            <span className="bg-amber-50 text-amber-700 border border-amber-100 px-2 py-0.5 rounded-md">
              📬 Notification sent to user
            </span>
          )}
        </div>
      )}

      {/* Baseline summary */}
      {new_baseline && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-white border border-slate-200 rounded-md p-3 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Weekly Income</p>
            <p className="text-sm font-bold text-slate-800 mt-1">₹{new_baseline.weekly_income?.toFixed(0)}</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-md p-3 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Weekly Hours</p>
            <p className="text-sm font-bold text-slate-800 mt-1">{new_baseline.weekly_hours?.toFixed(1)}h</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-md p-3 text-center">
            <p className="text-[10px] text-slate-500 uppercase tracking-wider">Hourly Rate</p>
            <p className="text-sm font-bold text-slate-800 mt-1">₹{new_baseline.hourly_rate?.toFixed(0)}</p>
          </div>
        </div>
      )}

      {/* Income chart */}
      {chartData.length > 0 && (
        <div>
          <h5 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">15-Day Income History</h5>
          <div className="h-40 w-full bg-white border border-slate-200 rounded-md p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8' }} tickFormatter={(v) => `D${v}`} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8' }} tickFormatter={(v) => `₹${v}`} />
                <Tooltip
                  contentStyle={{ borderRadius: '6px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '11px' }}
                  formatter={(value, name) => [`₹${value?.toFixed(0)}`, name === 'income' ? 'Income' : 'Hours']}
                  labelFormatter={(l) => `Day ${l}`}
                />
                <Line type="monotone" dataKey="income" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Premium Quotes — all 3 tiers */}
      {premium_quotes && Object.keys(premium_quotes).length > 0 && (
        <div>
          <h5 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Dynamic Premium Quotes</h5>
          <div className="grid grid-cols-3 gap-3">
            {Object.entries(premium_quotes).map(([tier, quote]) => {
              const bd = quote.premium_breakdown || {};
              return (
                <div
                  key={tier}
                  className={`bg-white border rounded-lg p-3 ${quote.recommended ? 'border-blue-400 ring-2 ring-blue-100' : 'border-slate-200'}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-xs capitalize">{quote.display_name?.split('—')[0]?.trim() || tier}</span>
                    {quote.recommended && (
                      <span className="text-[8px] bg-blue-500 text-white px-1.5 py-0.5 rounded-full font-bold">★ REC</span>
                    )}
                  </div>
                  <p className="text-lg font-bold text-slate-800">₹{quote.weekly_premium?.toFixed(2)}</p>
                  <p className="text-[9px] text-slate-500 mb-2">per week</p>

                  <div className="space-y-1 text-[9px] text-slate-600">
                    <div className="flex justify-between"><span>Tier rate</span><span className="font-mono">{bd.tier_rate_percent}</span></div>
                    <div className="flex justify-between"><span>Zone risk</span><span className="font-mono">×{bd.zone_risk?.toFixed(2)}</span></div>
                    <div className="flex justify-between"><span>Season</span><span className="font-mono">×{bd.seasonal_factor?.toFixed(2)}</span></div>
                    <div className="flex justify-between border-t border-slate-100 pt-1 mt-1">
                      <span>Raw</span><span className="font-mono">₹{bd.raw_premium?.toFixed(2)}</span>
                    </div>
                    {bd.floor_applied && (
                      <div className="flex justify-between text-amber-600">
                        <span>Floor applied</span><span className="font-mono">₹15 min</span>
                      </div>
                    )}
                    {bd.cap_applied && (
                      <div className="flex justify-between text-amber-600">
                        <span>Cap applied</span><span className="font-mono">{bd.premium_cap_percent}</span>
                      </div>
                    )}
                  </div>

                  <div className="mt-2 pt-2 border-t border-slate-100 text-[9px] text-slate-500">
                    Cap: ₹{quote.weekly_payout_cap?.toLocaleString()}/wk
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Workers() {
  const { data: workers, loading, error, refetch } = useApi('/admin/workers', null, { pollingInterval: 10000 });
  const [expandedWorkerId, setExpandedWorkerId] = useState(null);
  const [seedResults, setSeedResults] = useState({});

  const toggleExpand = (id) => {
    setExpandedWorkerId(expandedWorkerId === id ? null : id);
  };

  const handleSeedComplete = useCallback((workerId, result) => {
    setSeedResults((prev) => ({ ...prev, [workerId]: result }));
    setExpandedWorkerId(workerId);
    // Refetch workers list to update badges
    setTimeout(refetch, 500);
  }, [refetch]);

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Worker management
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Total registered" value={workers ? workers.length : "..."} subtext="All time" trend="none" />
          <MetricCard title="Active subscribers" value={workers ? workers.filter(w => !w.is_blocked).length : "..."} subtext="Currently active" trend="up" />
          <MetricCard title="Pending KYC" value={workers ? workers.filter(w => !w.kyc_verified).length : "..."} subtext="Needs action" trend="warn" />
          <MetricCard title="Blocked accounts" value={workers ? workers.filter(w => w.is_blocked).length : "..."} subtext="This week" trend="down" />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-slate-100">
          <CardTitle>Worker registry</CardTitle>
          <Button size="sm" onClick={refetch}>
            ↻ Refresh
          </Button>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-2 mb-4">
            <input 
              type="text" 
              placeholder="Search by name, ID, phone..." 
              className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-(--color-primary) w-full max-w-sm"
            />
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All platforms</option>
              <option>Swiggy</option>
              <option>Zomato</option>
            </select>
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All tiers</option>
              <option>Kavach</option>
              <option>Suraksha</option>
              <option>Raksha</option>
            </select>
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All statuses</option>
              <option>Active</option>
              <option>Pending KYC</option>
              <option>Blocked</option>
            </select>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200 bg-slate-50/50">
                <tr>
                  <th className="py-3 px-2 font-semibold">Worker ID</th>
                  <th className="py-3 px-2 font-semibold">Name</th>
                  <th className="py-3 px-2 font-semibold">Platform</th>
                  <th className="py-3 px-2 font-semibold">City</th>
                  <th className="py-3 px-2 font-semibold">Tier</th>
                  <th className="py-3 px-2 font-semibold">Phase</th>
                  <th className="py-3 px-2 font-semibold">Data</th>
                  <th className="py-3 px-2 font-semibold">Status</th>
                  <th className="py-3 px-2 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading && (
                  <tr>
                    <td colSpan="9" className="py-4 text-center text-slate-500">Loading workers...</td>
                  </tr>
                )}
                {error && (
                  <tr>
                    <td colSpan="9" className="py-4 text-center text-red-500">Error loading workers. Is the backend running?</td>
                  </tr>
                )}
                {workers && workers.map((worker) => {
                  const phase = PHASE_BADGE[worker.trial_phase] || { variant: "gray", label: worker.trial_phase || "Unknown" };
                  return (
                    <React.Fragment key={worker.id}>
                      <tr className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-2 font-mono font-medium">{worker.partner_id}</td>
                        <td className="py-3 px-2 font-medium">{worker.name}</td>
                        <td className="py-3 px-2 text-slate-600 capitalize">{worker.platform}</td>
                        <td className="py-3 px-2 text-slate-600">{worker.city}</td>
                        <td className="py-3 px-2">
                          <Badge variant={worker.tier === 'raksha' ? 'amber' : worker.tier === 'suraksha' ? 'blue' : 'gray'}>
                            {worker.tier}
                          </Badge>
                        </td>
                        <td className="py-3 px-2">
                          <Badge variant={phase.variant}>{phase.label}</Badge>
                        </td>
                        <td className="py-3 px-2">
                          {worker.has_seeded_history ? (
                            <Badge variant="green">✓ Seeded</Badge>
                          ) : (
                            <Badge variant="gray">No data</Badge>
                          )}
                        </td>
                        <td className="py-3 px-2">
                          {worker.is_blocked ? <Badge variant="red">Blocked</Badge> : <Badge variant="green">Active</Badge>}
                        </td>
                        <td className="py-3 px-2">
                          <div className="flex items-center gap-1">
                            <SeedButton
                              worker={worker}
                              onSeedComplete={(result) => handleSeedComplete(worker.id, result)}
                            />
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="h-6 text-[10px] px-2" 
                              onClick={() => toggleExpand(worker.id)}
                            >
                              {expandedWorkerId === worker.id ? "Hide" : "Details"}
                            </Button>
                          </div>
                        </td>
                      </tr>
                      {expandedWorkerId === worker.id && (
                        <tr className="bg-slate-50/70 border-b border-slate-100">
                          <td colSpan="9" className="p-4">
                            {seedResults[worker.id] ? (
                              <PremiumQuotesPanel seedResult={seedResults[worker.id]} />
                            ) : worker.has_seeded_history && worker.quote_summary ? (
                              <div className="space-y-3">
                                {/* Income chart from worker.daily_income_history */}
                                {worker.daily_income_history && worker.daily_income_history.length > 0 && (
                                  <div>
                                    <h5 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">15-Day Income History</h5>
                                    <div className="h-40 w-full max-w-2xl bg-white border border-slate-200 rounded-md p-2">
                                      <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={worker.daily_income_history} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                          <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8' }} tickFormatter={(v) => `D${v}`} />
                                          <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 9, fill: '#94a3b8' }} tickFormatter={(v) => `₹${v}`} />
                                          <Tooltip
                                            contentStyle={{ borderRadius: '6px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                                            formatter={(value) => [`₹${value}`, 'Income']}
                                            labelFormatter={(l) => `Day ${l}`}
                                          />
                                          <Line type="monotone" dataKey="amount" stroke="var(--color-primary)" strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 4 }} />
                                        </LineChart>
                                      </ResponsiveContainer>
                                    </div>
                                  </div>
                                )}
                                {/* Last known quotes summary */}
                                <div>
                                  <h5 className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Last Premium Quotes</h5>
                                  <div className="flex gap-3 text-xs">
                                    {Object.entries(worker.quote_summary || {}).map(([tier, amount]) => (
                                      <div key={tier} className="bg-white border border-slate-200 rounded-md px-3 py-2">
                                        <span className="capitalize font-medium">{tier}</span>
                                        <span className="ml-2 font-bold">₹{amount?.toFixed(2)}</span>/wk
                                      </div>
                                    ))}
                                  </div>
                                </div>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  className="text-[10px]"
                                  onClick={() => {/* The SeedButton handles re-seeding */}}
                                >
                                  Click "Re-seed Data" above to generate fresh quotes
                                </Button>
                              </div>
                            ) : (
                              <p className="text-xs text-slate-500 italic">
                                No income history yet. Click "Seed 15-Day Data" to generate activity data and calculate dynamic premiums for this worker.
                              </p>
                            )}
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
