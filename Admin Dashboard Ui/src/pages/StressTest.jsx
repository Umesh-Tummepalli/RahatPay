import React, { useState, useCallback } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ErrorBanner, LoadingSpinner } from "../components/ui/StatusComponents";
import * as api from "../lib/api";

// ── Constants ──────────────────────────────────────────────────────────────────
const SEVERITY = 0.75; // 14-day simulation severity
const SIM_DAYS = 14;

// ── BCR color helper ──────────────────────────────────────────────────────────
function bcrColor(bcr) {
  if (bcr < 0.70) return { text: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200", badge: "green", label: "SUSTAINABLE" };
  if (bcr < 0.80) return { text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200", badge: "amber", label: "MONITOR" };
  return { text: "text-red-700", bg: "bg-red-50", border: "border-red-200", badge: "red", label: "AT RISK" };
}

// Normalise backend status string ("AT_RISK" → "AT RISK") for display
function normalizeStatus(s) {
  return typeof s === "string" ? s.replace(/_/g, " ") : s;
}


// ── Mock fallback data (generated when API is offline) ────────────────────────
function generateMockResult() {
  const zones = [
    { zone_id: 9,  zone_name: "Dharavi, Mumbai",       riders: 48, weekly_premiums: 4320, simulated_payouts: 2808, bcr: 0.65 },
    { zone_id: 12, zone_name: "Andheri East, Mumbai",  riders: 62, weekly_premiums: 6820, simulated_payouts: 4778, bcr: 0.70 },
    { zone_id: 19, zone_name: "Rohini, Delhi",         riders: 35, weekly_premiums: 5250, simulated_payouts: 4462, bcr: 0.85 },
    { zone_id: 1,  zone_name: "T. Nagar, Chennai",     riders: 57, weekly_premiums: 4845, simulated_payouts: 3206, bcr: 0.66 },
    { zone_id: 14, zone_name: "Koramangala, Bangalore", riders: 44, weekly_premiums: 3960, simulated_payouts: 2732, bcr: 0.69 },
    { zone_id: 7,  zone_name: "Bandra West, Mumbai",   riders: 29, weekly_premiums: 3770, simulated_payouts: 2829, bcr: 0.75 },
    { zone_id: 13, zone_name: "Indiranagar, Bangalore", riders: 51, weekly_premiums: 4590, simulated_payouts: 2845, bcr: 0.62 },
    { zone_id: 17, zone_name: "Lajpat Nagar, Delhi",   riders: 38, weekly_premiums: 4560, simulated_payouts: 3511, bcr: 0.77 },
  ].map(z => ({ ...z, status: bcrColor(z.bcr).label }));

  const totalPremiums = zones.reduce((s, z) => s + z.weekly_premiums * SIM_DAYS, 0);
  const totalPayouts = zones.reduce((s, z) => s + z.simulated_payouts * SIM_DAYS, 0);
  const totalBcr = totalPremiums > 0 ? totalPayouts / totalPremiums : 0;

  return {
    summary: {
      total_bcr: parseFloat(totalBcr.toFixed(4)),
      status: bcrColor(totalBcr).label,
      sim_days: SIM_DAYS,
      severity: SEVERITY,
      total_premiums: Math.round(totalPremiums),
      total_payouts: Math.round(totalPayouts),
      zones_simulated: zones.length,
    },
    zones,
  };
}

export default function StressTest() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [usingMock, setUsingMock] = useState(false);

  const runStressTest = useCallback(async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      // POST /admin/stress-test  → Module 1 (:8000)
      const data = await api.runStressTest(SIM_DAYS, SEVERITY);
      setResult(data);
      setUsingMock(false);
    } catch (err) {
      console.warn("Stress test API unavailable, using mock result:", err.message);
      // Graceful fallback — generate realistic mock data
      await new Promise(r => setTimeout(r, 1200));
      setResult(generateMockResult());
      setUsingMock(true);
      setError("Stress test API unavailable — showing simulated result");
    } finally {
      setRunning(false);
    }
  }, []);

  const summary = result?.summary;
  const zones = Array.isArray(result?.zones) ? result.zones : [];

  // Summary BCR colors
  const sumColors = summary ? bcrColor(summary.total_bcr) : null;

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      {/* ── Header ── */}
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          BCR Stress Test — 14-Day Simulation
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total BCR"
            value={summary ? summary.total_bcr.toFixed(3) : "—"}
            subtext="Benefits-to-Contribution Ratio"
            trend={summary ? (summary.total_bcr < 0.70 ? "down" : "warn") : "none"}
          />
          <MetricCard
            title="Sim Period"
            value={`${SIM_DAYS} days`}
            subtext={`Severity: ${(SEVERITY * 100).toFixed(0)}%`}
            trend="none"
          />
          <MetricCard
            title="Zones Covered"
            value={summary ? summary.zones_simulated || zones.length : "—"}
            subtext="Active zones simulated"
            trend="none"
          />
          <MetricCard
            title="Target BCR"
            value="< 0.70"
            subtext="IRDAI sustainability threshold"
            trend="up"
          />
        </div>
      </div>

      {/* ── Error banner ── */}
      {error && <ErrorBanner message={error} type="warn" />}

      {/* ── Run button + summary ── */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <CardTitle>
            {running ? (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                Running Simulation…
              </span>
            ) : "BCR Stress Test Engine"}
          </CardTitle>
          <Button onClick={runStressTest} disabled={running} className="text-xs">
            {running ? "Computing…" : "▶ Run Stress Test"}
          </Button>
        </CardHeader>
        <CardContent>
          {/* Params info */}
          <div className="mb-4 p-3 rounded-md bg-slate-50 border border-slate-200 text-xs text-slate-600 flex flex-wrap gap-4">
            <span>
              <strong>Simulation:</strong> {SIM_DAYS}-day window
            </span>
            <span>
              <strong>Severity:</strong> {(SEVERITY * 100).toFixed(0)}% of weekly income
            </span>
            <span>
              <strong>Payout cap:</strong> Applied per tier limits
            </span>
            <span className="text-slate-400">
              {/* Social Security Code 2020: Production target is 90-day engagement, demo uses 14-day */}
              📋 SSC 2020: Demo window = 14 days (Production = 90 days)
            </span>
          </div>

          {/* Summary result */}
          {summary && (
            <div
              className={`mb-6 p-4 rounded-lg border flex flex-wrap items-center gap-6 ${sumColors.bg} ${sumColors.border}`}
            >
              <div>
                <div className="text-[10px] uppercase text-slate-500 font-semibold tracking-wide mb-1">Total BCR</div>
                <div className={`text-4xl font-bold font-mono ${sumColors.text}`}>
                  {summary.total_bcr.toFixed(3)}
                </div>
              </div>
              <div>
                <Badge variant={sumColors.badge} className="text-sm px-3 py-1">
                  {normalizeStatus(summary.status)}
                </Badge>
              </div>
              <div className="ml-auto text-xs text-slate-600 space-y-1 text-right">
                <div>Total Premiums (sim): <strong>₹{(summary.total_premiums || 0).toLocaleString("en-IN")}</strong></div>
                <div>Total Payouts (sim): <strong>₹{(summary.total_payouts || 0).toLocaleString("en-IN")}</strong></div>
              </div>
            </div>
          )}

          {/* Zone table */}
          {zones.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Zone</th>
                    <th className="pb-3 pr-4 font-semibold text-right">Riders</th>
                    <th className="pb-3 pr-4 font-semibold text-right">Premiums (wk)</th>
                    <th className="pb-3 pr-4 font-semibold text-right">Sim Payouts</th>
                    <th className="pb-3 pr-4 font-semibold text-right">BCR</th>
                    <th className="pb-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {zones.map((z, i) => {
                    const colors = bcrColor(z.bcr);
                    return (
                      <tr key={z.zone_id || i} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3 pr-4">
                          <div className="font-medium text-slate-800">{z.zone_name || `Zone ${z.zone_id}`}</div>
                        </td>
                        <td className="py-3 pr-4 text-right font-mono">{z.riders}</td>
                        <td className="py-3 pr-4 text-right font-mono">₹{(z.weekly_premiums || 0).toLocaleString("en-IN")}</td>
                        <td className="py-3 pr-4 text-right font-mono">₹{(z.simulated_payouts || 0).toLocaleString("en-IN")}</td>
                        <td className={`py-3 pr-4 text-right font-mono font-bold ${colors.text}`}>
                          {z.bcr.toFixed(3)}
                        </td>
                        <td className="py-3">
                          <Badge variant={colors.badge}>{colors.label}</Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : !running ? (
            <div className="text-center py-10 text-slate-400 text-sm">
              <div className="text-4xl mb-3">📊</div>
              <p>Click <strong>"Run Stress Test"</strong> to simulate 14-day BCR across all active zones.</p>
              <p className="text-xs mt-1 text-slate-400">Verifies system remains below 0.70 BCR threshold under severity scenarios.</p>
            </div>
          ) : (
            <div className="text-center py-10 text-slate-400 text-sm animate-pulse">
              Simulating disruption events across all zones…
            </div>
          )}

          {usingMock && result && (
            <p className="text-[10px] text-slate-400 mt-3 text-center">
              ⚠ Simulated result — connect Module 1 backend for live stress test computation
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
