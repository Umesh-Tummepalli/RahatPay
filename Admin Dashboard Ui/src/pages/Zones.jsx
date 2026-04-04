import React, { useCallback, useEffect, useState } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

function formatRelative(value) {
  if (!value) return "No recent event";
  const date = new Date(value);
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Zones() {
  const [zones, setZones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState(null);

  const [simEventType, setSimEventType] = useState("heavy_rain");
  const [simSeverity, setSimSeverity] = useState("severe_l1");
  const [simZoneId, setSimZoneId] = useState("");
  const [simLostHours, setSimLostHours] = useState(4.0);
  const [simSeverityRate, setSimSeverityRate] = useState(0.8);
  const [simLoading, setSimLoading] = useState(false);
  const [simResult, setSimResult] = useState(null);

  const fetchZones = useCallback(async () => {
    try {
      const res = await fetch("http://localhost:8001/admin/zones", {
        headers: { Authorization: "Bearer admin_token" }
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      setZones(Array.isArray(data) ? data : []);
      if (data && data.length > 0 && !simZoneId) {
        setSimZoneId(data[0].zone_id);
      }
      setPageError(null);
    } catch (err) {
      console.error(err);
      setPageError("Failed to load zones. Make sure Module 1 is running on port 8001.");
    } finally {
      setLoading(false);
    }
  }, [simZoneId]);

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  const handleSimulateDisaster = async () => {
    setSimLoading(true);
    setSimResult(null);
    try {
      const res = await fetch("http://localhost:8001/admin/simulate-disaster", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer admin_token"
        },
        body: JSON.stringify({
          event_type: simEventType,
          severity: simSeverity,
          affected_zone: parseInt(simZoneId, 10),
          lost_hours: parseFloat(simLostHours),
          severity_rate: parseFloat(simSeverityRate)
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to run simulation.");
      }

      setSimResult(data);
      await fetchZones();
    } catch (err) {
      console.error(err);
      setSimResult({ error: err.message || "Failed to run simulation." });
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Zone management
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Active zones" value={loading ? "..." : zones.length} subtext="Total tracked zones" trend="none" />
          <MetricCard title="High-risk zones" value={loading ? "..." : zones.filter(z => z.risk_multiplier > 1.2).length} subtext="Risk > 1.2x" trend="warn" />
          <MetricCard title="Zones with events" value={loading ? "..." : zones.filter(z => z.recent_event_count > 0).length} subtext="Last 7 days" trend="up" />
          <MetricCard title="Recent event volume" value={loading ? "..." : zones.reduce((sum, z) => sum + (z.recent_event_count || 0), 0)} subtext="Tracked in registry" trend="none" />
        </div>
        {pageError && (
          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
            {pageError}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Zone registry</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-[320px] overflow-y-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200 sticky top-0 bg-white">
                  <tr>
                    <th className="pb-3 px-2 font-semibold">ID</th>
                    <th className="pb-3 px-2 font-semibold">City</th>
                    <th className="pb-3 px-2 font-semibold">Area Name</th>
                    <th className="pb-3 px-2 font-semibold">Risk</th>
                    <th className="pb-3 px-2 font-semibold">Recent Events</th>
                    <th className="pb-3 px-2 font-semibold">Latest Trigger</th>
                    <th className="pb-3 px-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr><td colSpan="7" className="py-4 text-center">Loading...</td></tr>
                  ) : zones.length > 0 ? (
                    zones.map(z => (
                      <tr key={z.zone_id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 px-2 font-mono text-slate-500">{z.zone_id}</td>
                        <td className="py-3 px-2">{z.city}</td>
                        <td className="py-3 px-2 font-medium">{z.area_name}</td>
                        <td className="py-3 px-2 font-mono">{z.risk_multiplier.toFixed(2)}x</td>
                        <td className="py-3 px-2">
                          <div className="font-mono text-slate-700">{z.recent_event_count || 0}</div>
                          <div className="text-slate-400">Cap {z.registration_cap}</div>
                        </td>
                        <td className="py-3 px-2">
                          <div className="text-slate-700">{z.latest_event_type || "None"}</div>
                          <div className="text-slate-400">{formatRelative(z.latest_event_at)}</div>
                        </td>
                        <td className="py-3 px-2">
                          {z.is_active ? <Badge variant="green">Active</Badge> : <Badge variant="gray">Disabled</Badge>}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="7" className="py-4 text-center text-slate-500">No zones found</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card className="border-(--color-primary)/20 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] border-t-4 border-t-(--color-primary)">
          <CardHeader>
            <CardTitle>Disaster Engine (Simulation)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-slate-500 mb-2">Simulate disruptions to generate events, claims, and payout records that ripple through the admin dashboard.</p>

            <div>
              <label className="text-[10px] font-medium text-slate-500 uppercase">Trigger Event</label>
              <select
                value={simEventType}
                onChange={e => setSimEventType(e.target.value)}
                className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
              >
                <option value="heavy_rain">Heavy Rain</option>
                <option value="cyclone">Cyclone</option>
                <option value="flood">Flood</option>
                <option value="extreme_heat">Extreme Heat</option>
                <option value="civic_disruption">Civic Disruption</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-medium text-slate-500 uppercase">Affected Zone</label>
                <select
                  value={simZoneId}
                  onChange={e => setSimZoneId(e.target.value)}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
                >
                  {zones.map(z => <option key={z.zone_id} value={z.zone_id}>{z.city} - {z.area_name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-[10px] font-medium text-slate-500 uppercase">Severity</label>
                <select
                  value={simSeverity}
                  onChange={e => setSimSeverity(e.target.value)}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
                >
                  <option value="moderate">Moderate</option>
                  <option value="severe_l1">Severe L1</option>
                  <option value="severe_l2">Severe L2</option>
                  <option value="extreme">Extreme</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] font-medium text-slate-500 uppercase">Lost Hrs</label>
                <input
                  type="number"
                  step="0.5"
                  value={simLostHours}
                  onChange={e => setSimLostHours(e.target.value)}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-medium text-slate-500 uppercase">Severity Rate</label>
                <input
                  type="number"
                  step="0.1"
                  max="1.0"
                  value={simSeverityRate}
                  onChange={e => setSimSeverityRate(e.target.value)}
                  className="mt-1 w-full bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none"
                />
              </div>
            </div>

            <Button onClick={handleSimulateDisaster} disabled={simLoading || !simZoneId} className="w-full mt-2 font-medium tracking-wide">
              {simLoading ? "Simulating..." : "SIMULATE DISASTER"}
            </Button>

            {simResult && (
              <div className="mt-4 p-3 rounded-md bg-green-50 border border-green-200 text-xs">
                {simResult.error ? (
                  <span className="text-red-600">{simResult.error}</span>
                ) : (
                  <div className="space-y-1">
                    <h4 className="font-semibold text-green-800 mb-1">Evt_ID: {simResult.event_id} Recorded</h4>
                    <div className="flex justify-between text-green-700">
                      <span>Workers impacted:</span>
                      <span className="font-bold">{simResult.workers_impacted}</span>
                    </div>
                    <div className="flex justify-between text-green-700">
                      <span>Claims drafted:</span>
                      <span className="font-bold">{simResult.claims_created}</span>
                    </div>
                    <div className="flex justify-between text-green-700">
                      <span>Payout rows created:</span>
                      <span className="font-bold">{simResult.payouts_created}</span>
                    </div>
                    <div className="flex justify-between text-green-700 mt-1">
                      <span>Total estimated exposure:</span>
                      <span className="font-mono font-bold">₹{simResult.total_payout_estimated}</span>
                    </div>
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
