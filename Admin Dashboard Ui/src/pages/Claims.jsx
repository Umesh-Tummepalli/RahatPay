import React, { useState, useEffect } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { ErrorBanner, LoadingSpinner } from "../components/ui/StatusComponents";
import * as api from "../lib/api";

// ── Mock data — used ONLY when backend is unavailable ─────────────────────────
const MOCK_CLAIMS = [
  { id: 8819, rider_id: 7190, disruption_event_id: "EVT-2026-001", status: "pending",  final_payout: 700,  tier: "suraksha" },
  { id: 8821, rider_id: 4821, disruption_event_id: "EVT-2026-002", status: "pending",  final_payout: 1200, tier: "raksha"   },
  { id: 8815, rider_id: 3342, disruption_event_id: "EVT-2026-001", status: "approved", final_payout: 450,  tier: "kavach"   },
  { id: 8810, rider_id: 9012, disruption_event_id: "EVT-2026-003", status: "paid",     final_payout: 980,  tier: "suraksha" },
];

export default function Claims() {
  const [claims, setClaims]           = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [usingMockData, setUsingMockData] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  // ── Fetch claims via /m3/admin/claims/live → Module 3 (:8003) ─────────────
  const fetchClaims = async () => {
    setLoading(true);
    try {
      // GET /m3/admin/claims/live
      // Vite proxy: /m3/* → strips prefix → http://localhost:8003/admin/claims/live
      const data = await api.getLiveClaims();
      setClaims(Array.isArray(data) ? data : []);
      setError(null);
      setUsingMockData(false);
    } catch {
      if (process.env.NODE_ENV === "development") {
        console.warn("[Claims] API unavailable — fallback mode active");
      }
      setClaims(MOCK_CLAIMS);
      setUsingMockData(true);
      setError("Backend unavailable — showing demo data. Start Module 3 for live claims.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchClaims(); }, []); // eslint-disable-line

  // ── Override a claim via /m3/admin/claims/{id}/override → Module 3 (:8003) ─
  const handleOverride = async (claimId, action) => {
    setActionLoading(prev => ({ ...prev, [claimId]: action }));
    try {
      // PATCH /m3/admin/claims/{id}/override
      // Vite proxy: /m3/* → strips prefix → http://localhost:8003/admin/claims/{id}/override
      await api.overrideClaim(claimId, action);
      // Optimistic: remove resolved claim from list
      setClaims(prev => prev.filter(c => c.id !== claimId));
      setError(null);
    } catch (err) {
      if (process.env.NODE_ENV === "development") {
        console.warn(`[Claims] Override failed for claim ${claimId}:`, err.message);
      }
      setError("Override request failed — backend may be offline. Claim state unchanged.");
    } finally {
      setActionLoading(prev => {
        const next = { ...prev };
        delete next[claimId];
        return next;
      });
    }
  };

  const pendingClaims  = claims.filter(c => c.status === "pending");
  const approvedClaims = claims.filter(c => c.status === "paid" || c.status === "approved");
  const pendingValue   = pendingClaims.reduce((acc, c) => acc + (c.final_payout || 0), 0);

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Claims queue
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Open claims"    value={loading ? "..." : pendingClaims.length}                     subtext="Pending review"    trend="warn" />
          <MetricCard title="Approved today" value={loading ? "..." : approvedClaims.length}                    subtext="System & Manual"   trend="up"   />
          <MetricCard title="Pending value"  value={loading ? "..." : `₹${pendingValue.toFixed(0)}`}            subtext="Exposure"          trend="up"   />
          <MetricCard title="Avg payout"     value="₹1,190"                                                      subtext="Across all tiers"  trend="none" />
        </div>

        {/* ── Status banners ── */}
        <div className="mt-4 space-y-2">
          {usingMockData && (
            <ErrorBanner
              type="info"
              message="Demo mode — showing sample claims. Start Module 3 (:8003) for live data."
            />
          )}
          {error && !usingMockData && (
            <ErrorBanner type="warn" message={error} />
          )}
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>All claims</CardTitle>
          <div className="flex gap-2">
            <Button onClick={fetchClaims} size="sm" variant="outline" className="text-xs" disabled={loading}>
              {loading ? "Loading…" : "↻ Retry"}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-4">
            <input
              type="text"
              placeholder="Search worker ID or trigger type..."
              className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-(--color-primary) w-full max-w-sm"
            />
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All statuses</option>
              <option>Pending</option>
              <option>In review</option>
              <option>Approved</option>
              <option>Rejected</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200 bg-slate-50/50">
                <tr>
                  <th className="py-3 px-2 font-semibold">Claim ID</th>
                  <th className="py-3 px-2 font-semibold">Worker</th>
                  <th className="py-3 px-2 font-semibold">Event ID</th>
                  <th className="py-3 px-2 font-semibold">Tier</th>
                  <th className="py-3 px-2 font-semibold">Amount</th>
                  <th className="py-3 px-2 font-semibold">Status</th>
                  <th className="py-3 px-2 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan="7" className="py-6"><LoadingSpinner message="Loading claims…" /></td></tr>
                ) : claims.length > 0 ? (
                  claims.map(claim => (
                    <tr key={claim.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-2 font-mono font-medium">C-{claim.id}</td>
                      <td className="py-3 px-2 font-mono">W-{claim.rider_id}</td>
                      <td className="py-3 px-2 text-slate-600">{claim.disruption_event_id}</td>
                      <td className="py-3 px-2">
                        <Badge variant={claim.tier === "raksha" ? "amber" : claim.tier === "suraksha" ? "blue" : "gray"}>
                          {claim.tier ? claim.tier.charAt(0).toUpperCase() + claim.tier.slice(1) : "N/A"}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 font-mono">₹{claim.final_payout || claim.calculated_payout || 0}</td>
                      <td className="py-3 px-2">
                        {claim.status === "pending"  && <Badge variant="amber">Pending</Badge>}
                        {claim.status === "approved" && <Badge variant="green">Approved</Badge>}
                        {claim.status === "paid"     && <Badge variant="green">Paid</Badge>}
                        {claim.status === "rejected" && <Badge variant="red">Rejected</Badge>}
                        {claim.status === "in_review" && <Badge variant="blue">In Review</Badge>}
                      </td>
                      <td className="py-3 px-2 flex gap-1">
                        {claim.status === "pending" || claim.status === "in_review" ? (
                          <>
                            <Button
                              size="sm"
                              disabled={!!actionLoading[claim.id]}
                              onClick={() => handleOverride(claim.id, "approve")}
                              className="h-6 text-[10px] px-2 bg-green-600 hover:bg-green-700"
                            >
                              {actionLoading[claim.id] === "approve" ? "…" : "Approve"}
                            </Button>
                            <Button
                              size="sm"
                              disabled={!!actionLoading[claim.id]}
                              onClick={() => handleOverride(claim.id, "reject")}
                              variant="destructive"
                              className="h-6 text-[10px] px-2"
                            >
                              {actionLoading[claim.id] === "reject" ? "…" : "Reject"}
                            </Button>
                          </>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="7" className="py-8 text-center text-slate-500">
                      No claims yet. Run a disaster simulation from the Dashboard.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
