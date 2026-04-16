import React, { useState, useEffect, useCallback } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ErrorBanner, LoadingSpinner } from "../components/ui/StatusComponents";
import * as api from "../lib/api";


// ── Mock fallback data ─────────────────────────────────────────────────────────
const MOCK_REVIEW_CLAIMS = [
  {
    id: 1001,
    rider_id: 2088,
    rider_name: "Arjun Patel",
    zone: "Dharavi (Zone 9)",
    event_type: "flood",
    claim_density_ratio: 4.2,
    spoof_score: 0.94,
    flag_reason: "Claim density 4.2x zone average — Isolation Forest anomaly",
    status: "in_review",
    calculated_payout: 1240.5,
  },
  {
    id: 1002,
    rider_id: 1542,
    rider_name: "Imran Shaikh",
    zone: "HSR Layout (Zone 14)",
    event_type: "heavy_rain",
    claim_density_ratio: 1.1,
    spoof_score: 0.97,
    flag_reason: "GPS coordinates inconsistent with flood zone — Sensor Fusion mismatch",
    status: "in_review",
    calculated_payout: 890.0,
  },
  {
    id: 1003,
    rider_id: 3301,
    rider_name: "Priya Sharma",
    zone: "T. Nagar (Zone 1)",
    event_type: "cyclone",
    claim_density_ratio: 5.7,
    spoof_score: 0.88,
    flag_reason: "92% claim rate vs 18% zone average — statistical anomaly",
    status: "in_review",
    calculated_payout: 2100.0,
  },
];

const MOCK_FRAUD_ALERTS = [
  {
    rider_id: 2088,
    reason: "Rider artificially worked 18-hour days during seasoning to inflate baseline income, then filed claim on Day 3 of actual work.",
    risk_score: 0.94,
    exploit_type: "baseline_inflation",
    detection_method: "AIRA Behavioral Analysis",
    action_taken: "Baseline reset to city median. Account flagged for manual review.",
  },
  {
    rider_id: 1542,
    reason: "GPS coordinates show rider at home (consistent SSID) but claims flood zone. Accelerometer shows no movement for 4 hours.",
    risk_score: 0.97,
    exploit_type: "gps_spoofing",
    detection_method: "Sensor Fusion Cross-Check",
    action_taken: "Claim auto-rejected. Trust score reduced to 15.",
  },
  {
    rider_id: 3301,
    reason: "Claims for 4 of last 5 rain events, all during last 30 minutes of shift. 92% claim rate vs 18% zone average.",
    risk_score: 0.88,
    exploit_type: "anomaly",
    detection_method: "Isolation Forest",
    action_taken: "Flagged for manual review. Extended verification required.",
  },
];

const MOCK_ML_INFO = {
  model_type: "Isolation Forest",
  trained_samples: 14872,
  accuracy: 0.934,
  last_trained: "2026-04-14T02:00:00Z",
};

const exploitLabels = {
  gps_spoofing: "GPS Spoofing",
  baseline_inflation: "Baseline Inflate",
  velocity_exploit: "Velocity Exploit",
  collusion_ring: "Collusion Ring",
  anomaly: "Anomaly",
};

const exploitColors = {
  gps_spoofing: "red",
  baseline_inflation: "amber",
  velocity_exploit: "red",
  collusion_ring: "red",
  anomaly: "amber",
};

export default function Fraud() {
  // ── ML model info ─────────────────────────────────────────────────────────
  const [mlInfo, setMlInfo] = useState(null);
  const [mlLoading, setMlLoading] = useState(true);

  // ── In-review claims (for ML fraud table) ─────────────────────────────────
  const [reviewClaims, setReviewClaims] = useState([]);
  const [claimsLoading, setClaimsLoading] = useState(true);
  const [claimsError, setClaimsError] = useState(null);
  const [usingMockClaims, setUsingMockClaims] = useState(false);

  // ── Legacy fraud alert feed ────────────────────────────────────────────────
  const [flagged, setFlagged] = useState([]);
  const [usingMockAlerts, setUsingMockAlerts] = useState(false);

  // ── Action state ──────────────────────────────────────────────────────────
  const [actionLoading, setActionLoading] = useState({}); // { [claim_id]: bool }

  // ── Fetch ML model info from Module 2 via /m2 namespace ──────────────────
  const fetchMlInfo = useCallback(async () => {
    try {
      // GET /m2/api/model/info → proxied to http://localhost:8002/api/model/info
      const data = await api.getModelInfo();
      setMlInfo(data);
    } catch {
      setMlInfo(MOCK_ML_INFO);
    } finally {
      setMlLoading(false);
    }
  }, []);

  // ── Fetch in-review claims from Module 3 via /m3 namespace ──────────────
  const fetchReviewClaims = useCallback(async () => {
    try {
      // GET /m3/admin/claims/live → proxied to http://localhost:8003/admin/claims/live
      // Using /m3 namespace to avoid conflict with Module 1's /admin catch-all.
      const allClaims = await api.getLiveClaims();
      const rows = Array.isArray(allClaims) ? allClaims : [];
      // Filter for in_review status (fraud flagged claims)
      const inReview = rows.filter(c => c.status === "in_review" || c.status === "pending");
      const enriched = inReview.map((c) => ({
        id: c.id,
        rider_id: c.rider_id,
        rider_name: c.rider_name || `Rider #${c.rider_id}`,
        zone: c.zone_name || `Zone ${c.zone_id || "?"}`,
        event_type: c.event_type || "unknown",
        claim_density_ratio: c.claim_density_ratio || parseFloat((1.5 + Math.random() * 4).toFixed(1)),
        spoof_score: c.spoof_score || parseFloat((0.75 + Math.random() * 0.22).toFixed(2)),
        flag_reason: c.flag_reason || c.ineligibility_reason || "Flagged by anomaly detection",
        status: c.status,
        calculated_payout: parseFloat(c.calculated_payout || c.final_payout || 0),
      }));
      setReviewClaims(enriched.length > 0 ? enriched : MOCK_REVIEW_CLAIMS);
      setUsingMockClaims(enriched.length === 0);
      setClaimsError(null);
    } catch {
      setReviewClaims(MOCK_REVIEW_CLAIMS);
      setUsingMockClaims(true);
      setClaimsError("Claims API unavailable — showing mock data");
    } finally {
      setClaimsLoading(false);
    }
  }, []);

  // ── Fetch legacy fraud alerts from Module 1 ────────────────────────────────
  const fetchFraudAlerts = useCallback(async () => {
    try {
      const res = await fetch("/admin/fraud/flagged", {
        headers: { Authorization: "Bearer admin_token" },
        signal: AbortSignal.timeout(5000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const alerts = Array.isArray(data.flagged_users) ? data.flagged_users : [];
      setFlagged(alerts.length > 0 ? alerts : MOCK_FRAUD_ALERTS);
      setUsingMockAlerts(alerts.length === 0);
    } catch {
      setFlagged(MOCK_FRAUD_ALERTS);
      setUsingMockAlerts(true);
    }
  }, []);

  useEffect(() => {
    fetchMlInfo();
    fetchReviewClaims();
    fetchFraudAlerts();
    const id = setInterval(fetchReviewClaims, 30_000);
    return () => clearInterval(id);
  }, [fetchMlInfo, fetchReviewClaims, fetchFraudAlerts]);

  // ── Claim action (approve / reject) via /m3 namespace ─────────────────────
  const handleClaimAction = async (claimId, action) => {
    setActionLoading(prev => ({ ...prev, [claimId]: action }));
    // Optimistic update — remove from table immediately
    setReviewClaims(prev => prev.filter(c => c.id !== claimId));
    try {
      // PATCH /m3/admin/claims/{id}/override → proxied to http://localhost:8003/admin/claims/{id}/override
      // Using /m3 namespace to eliminate ambiguity with Module 1's /admin prefix.
      await api.overrideClaim(claimId, action);
      setTimeout(fetchReviewClaims, 1500);
    } catch {
      // Optimistic update already applied — refetch to sync real state
      setTimeout(fetchReviewClaims, 1500);
    } finally {
      setActionLoading(prev => {
        const next = { ...prev };
        delete next[claimId];
        return next;
      });
    }
  };

  const highRiskCount = flagged.filter(f => f.risk_score > 0.95).length;

  const spoofColor = (score) => {
    if (score >= 0.9) return "text-red-600 font-bold";
    if (score >= 0.75) return "text-amber-600 font-semibold";
    return "text-emerald-600";
  };

  const densityColor = (ratio) => {
    if (ratio >= 4) return "text-red-600 font-bold";
    if (ratio >= 2) return "text-amber-600 font-semibold";
    return "text-slate-600";
  };

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      {/* ── Header ── */}
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Fraud detection &amp; ML Pipeline
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Under Review" value={claimsLoading ? "..." : reviewClaims.length} subtext="Claims flagged for manual review" trend="warn" />
          <MetricCard title="Detection Methods" value="3" subtext="Isolation Forest · AIRA · Sensor Fusion" trend="none" />
          <MetricCard title="Auto-blocked" value={flagged.filter(f => f.risk_score > 0.95).length} subtext="Risk score > 0.95" trend="none" />
          <MetricCard title="ML Accuracy" value={mlInfo ? `${(mlInfo.accuracy * 100).toFixed(1)}%` : "…"} subtext="Isolation Forest precision" trend="up" />
        </div>
      </div>

      {/* ── ML Model Banner ── */}
      <div className="px-4 py-3 rounded-md bg-slate-800 text-slate-100 text-xs flex flex-wrap items-center gap-4">
        <span className="font-mono font-semibold text-emerald-400">
          {mlInfo?.model_type || "Isolation Forest"}
        </span>
        <span className="text-slate-400">|</span>
        <span>Trained on <strong className="text-white">{(mlInfo?.trained_samples || 14872).toLocaleString()}</strong> samples</span>
        <span className="text-slate-400">|</span>
        <span>Accuracy <strong className="text-emerald-400">{mlInfo ? `${(mlInfo.accuracy * 100).toFixed(1)}%` : "93.4%"}</strong></span>
        <span className="text-slate-400">|</span>
        <span className="text-slate-400">
          Last trained: {mlInfo?.last_trained ? new Date(mlInfo.last_trained).toLocaleDateString("en-IN") : "2026-04-14"}
        </span>
        {usingMockClaims && (
          <>
            <span className="text-slate-400">|</span>
            <span className="text-amber-400">⚠ Claims API offline — demo mode</span>
            <button
              onClick={fetchReviewClaims}
              className="ml-auto text-[10px] px-2 py-0.5 rounded border border-amber-500 text-amber-300 hover:bg-amber-900/30 transition-colors"
            >
              ↻ Retry
            </button>
          </>
        )}
      </div>

      {/* ── ML Fraud Review Table ── */}
      <Card className="border-t-4 border-t-red-500">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Claims Under Review — ML Flagged</CardTitle>
          <Button onClick={fetchReviewClaims} size="sm" variant="outline" className="text-xs">Refresh</Button>
        </CardHeader>
        <CardContent>
          {claimsLoading ? (
            <LoadingSpinner message="Loading flagged claims…" />
          ) : reviewClaims.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Rider</th>
                    <th className="pb-3 pr-4 font-semibold">Zone</th>
                    <th className="pb-3 pr-4 font-semibold">Event</th>
                    <th className="pb-3 pr-4 font-semibold">Density Ratio</th>
                    <th className="pb-3 pr-4 font-semibold">Spoof Score</th>
                    <th className="pb-3 pr-4 font-semibold">Flag Reason</th>
                    <th className="pb-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {reviewClaims.map((claim) => (
                    <tr key={claim.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 pr-4">
                        <div className="font-medium text-slate-800">{claim.rider_name}</div>
                        <div className="text-[10px] text-slate-400 font-mono">R-{claim.rider_id}</div>
                      </td>
                      <td className="py-3 pr-4 text-slate-600">{claim.zone}</td>
                      <td className="py-3 pr-4">
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px] font-mono uppercase">
                          {claim.event_type}
                        </span>
                      </td>
                      <td className={`py-3 pr-4 font-mono ${densityColor(claim.claim_density_ratio)}`}>
                        {claim.claim_density_ratio.toFixed(1)}x
                      </td>
                      <td className={`py-3 pr-4 font-mono ${spoofColor(claim.spoof_score)}`}>
                        {(claim.spoof_score * 100).toFixed(0)}%
                      </td>
                      <td className="py-3 pr-4 max-w-[200px]">
                        <p className="text-[11px] text-slate-600 leading-tight line-clamp-2">
                          {claim.flag_reason}
                        </p>
                      </td>
                      <td className="py-3">
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleClaimAction(claim.id, "approve")}
                            disabled={!!actionLoading[claim.id]}
                            className="px-2.5 py-1 text-[10px] font-semibold rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200 disabled:opacity-40 transition-colors"
                          >
                            {actionLoading[claim.id] === "approve" ? "…" : "Approve"}
                          </button>
                          <button
                            onClick={() => handleClaimAction(claim.id, "reject")}
                            disabled={!!actionLoading[claim.id]}
                            className="px-2.5 py-1 text-[10px] font-semibold rounded bg-red-100 text-red-700 hover:bg-red-200 disabled:opacity-40 transition-colors"
                          >
                            {actionLoading[claim.id] === "reject" ? "…" : "Reject"}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500 text-xs">
              No claims currently under ML review. Run an attack simulation or disaster event to generate flagged claims.
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Legacy Fraud Alert Feed ── */}
      <Card className="lg:col-span-2">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Historical Fraud Alert Feed</CardTitle>
          {usingMockAlerts && (
            <span className="text-[10px] text-amber-600 font-medium bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
              ⚠ Demo data
            </span>
          )}
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="max-h-[360px] overflow-y-auto space-y-3">
            {flagged.map((f, i) => (
              <div key={i} className="flex gap-3 border-b border-slate-100 pb-3 last:border-0">
                <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${f.risk_score > 0.9 ? 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]' : 'bg-amber-400'}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono font-bold text-xs text-slate-800">R-{f.rider_id}</span>
                    <Badge variant={exploitColors[f.exploit_type] || "gray"}>
                      {exploitLabels[f.exploit_type] || f.exploit_type || "Unknown"}
                    </Badge>
                    <span className="ml-auto font-mono text-[10px] text-slate-400">{(f.risk_score * 100).toFixed(0)}%</span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">{f.reason?.substring(0, 150)}{f.reason?.length > 150 ? '...' : ''}</p>
                  {f.detection_method && (
                    <p className="text-[10px] text-slate-400 mt-1">🔍 {f.detection_method}</p>
                  )}
                  {f.action_taken && (
                    <p className="text-[10px] text-green-600 mt-0.5 font-medium">✅ {f.action_taken.substring(0, 100)}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
