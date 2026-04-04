import React, { useState, useEffect } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

// Mock data for demo purposes when backend is unavailable
const MOCK_CLAIMS = [
  { id: 8819, rider_id: 7190, disruption_event_id: "EVT-2026-001", status: "pending", final_payout: 700, tier: "suraksha" },
  { id: 8821, rider_id: 4821, disruption_event_id: "EVT-2026-002", status: "pending", final_payout: 1200, tier: "raksha" },
  { id: 8815, rider_id: 3342, disruption_event_id: "EVT-2026-001", status: "approved", final_payout: 450, tier: "kavach" },
  { id: 8810, rider_id: 9012, disruption_event_id: "EVT-2026-003", status: "paid", final_payout: 980, tier: "suraksha" },
];

export default function Claims() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [usingMockData, setUsingMockData] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  const fetchClaims = async () => {
    try {
      const res = await fetch("/admin/claims/live", {
        headers: { "Authorization": "Bearer admin_token" }
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setClaims(Array.isArray(data) ? data : []);
      setError(null);
      setUsingMockData(false);
    } catch (err) {
      console.error("Failed to fetch claims:", err);
      // Use mock data for demo
      setClaims(MOCK_CLAIMS);
      setUsingMockData(true);
      setError("Backend unavailable. Showing demo data. Start the backend for live data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, []);

  const handleOverride = async (claimId, status) => {
    setActionLoading(prev => ({ ...prev, [claimId]: status }));
    try {
      const res = await fetch(`/admin/claims/${claimId}/override`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer admin_token"
        },
        body: JSON.stringify({ status })
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP error! status: ${res.status}`);
      }

      setClaims(prev => prev.filter(claim => claim.id !== claimId));
      setError(null);
    } catch (err) {
      console.error("Failed to override claim:", err);
      setError(err.message || "Failed to update claim. Please try again.");
    } finally {
      setActionLoading(prev => {
        const next = { ...prev };
        delete next[claimId];
        return next;
      });
    }
  };

  // Safe filtering with default empty array
  const pendingClaims = Array.isArray(claims) ? claims.filter(c => c.status === "pending") : [];
  const approvedClaims = Array.isArray(claims) ? claims.filter(c => c.status === "paid" || c.status === "approved") : [];
  const pendingValue = pendingClaims.reduce((acc, c) => acc + (c.final_payout || 0), 0);

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Claims queue
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Open claims" value={loading ? "..." : pendingClaims.length} subtext="Pending review" trend="warn" />
          <MetricCard title="Approved today" value={loading ? "..." : approvedClaims.length} subtext="System & Manual" trend="up" />
          <MetricCard title="Pending Value" value={loading ? "..." : `₹${pendingValue.toFixed(2)}`} subtext="Exposure" trend="up" />
          <MetricCard title="Avg payout" value="₹1,190" subtext="Across all tiers" trend="none" />
        </div>
        {usingMockData && (
          <div className="mt-4 p-4 p-4 bg-blue-50 border border-blue-200 rounded-md text-xs text-blue-800">
            ℹ️ <strong>Demo Mode:</strong> Showing sample data. Start the backend for live claims.
          </div>
        )}
        {error && !usingMockData && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800">
            ⚠️ {error}
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All claims</CardTitle>
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
                  <tr><td colSpan="7" className="py-4 text-center">Loading claims...</td></tr>
                ) : usingMockData ? (
                  <tr><td colSpan="7" className="py-4 text-center text-blue-600">{error}</td></tr>
                ) : claims.length > 0 ? (
                  claims.map(claim => (
                    <tr key={claim.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-2 font-mono font-medium">C-{claim.id}</td>
                      <td className="py-3 px-2 font-mono">W-{claim.rider_id}</td>
                      <td className="py-3 px-2 text-slate-600">EVT-{claim.disruption_event_id}</td>
                      <td className="py-3 px-2">
                        <Badge variant={claim.tier === 'raksha' ? 'amber' : claim.tier === 'suraksha' ? 'blue' : 'gray'}>
                          {claim.tier ? claim.tier.charAt(0).toUpperCase() + claim.tier.slice(1) : 'N/A'}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 font-mono">₹{claim.final_payout || claim.calculated_payout || 0}</td>
                      <td className="py-3 px-2">
                        {claim.status === "pending" && <Badge variant="amber">Pending</Badge>}
                        {claim.status === "approved" && <Badge variant="green">Approved</Badge>}
                        {claim.status === "paid" && <Badge variant="green">Paid</Badge>}
                        {claim.status === "rejected" && <Badge variant="red">Rejected</Badge>}
                      </td>
                      <td className="py-3 px-2 flex gap-1">
                        {claim.status === "pending" ? (
                          <>
                            <Button size="sm" disabled={!!actionLoading[claim.id]} onClick={() => handleOverride(claim.id, "approved")} className="h-6 text-[10px] px-2 bg-green-600 hover:bg-green-700">
                              {actionLoading[claim.id] === "approved" ? "Approving..." : "Approve"}
                            </Button>
                            <Button size="sm" disabled={!!actionLoading[claim.id]} onClick={() => handleOverride(claim.id, "rejected")} variant="destructive" className="h-6 text-[10px] px-2">
                              {actionLoading[claim.id] === "rejected" ? "Rejecting..." : "Reject"}
                            </Button>
                          </>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan="7" className="py-4 text-center text-slate-500">No claims generated yet. Run a disaster simulation.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
