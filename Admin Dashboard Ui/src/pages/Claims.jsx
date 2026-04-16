import React, { useState, useEffect } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { useApi, useApiMutation } from "../hooks/useApi";

// Mock data for demo purposes when backend is unavailable
const MOCK_CLAIMS = [
  { id: 8819, rider_id: 7190, disruption_event_id: "EVT-2026-001", status: "pending", final_payout: 700, tier: "suraksha" },
  { id: 8821, rider_id: 4821, disruption_event_id: "EVT-2026-002", status: "in_review", final_payout: 1200, tier: "raksha" },
  { id: 8815, rider_id: 3342, disruption_event_id: "EVT-2026-001", status: "approved", final_payout: 450, tier: "kavach" },
  { id: 8810, rider_id: 9012, disruption_event_id: "EVT-2026-003", status: "paid", final_payout: 980, tier: "suraksha" },
];

export default function Claims() {
  // Module 3 endpoint for live claims
  const { data: claimsData, loading, error, refetch } = useApi(
    '/admin/claims/live',
    [],
    { baseUrl: 'module3' }
  );

  // Mutation hook for claim override
  const { execute: overrideClaim, loading: overrideLoading, error: overrideError } = useApiMutation(
    '', // Will be set dynamically
    'PATCH',
    { baseUrl: 'module3' }
  );

  const [claims, setClaims] = useState([]);
  const [usingMockData, setUsingMockData] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionLoading, setActionLoading] = useState({});
  const [filterStatus, setFilterStatus] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");

  // Initialize claims data with fallback to mock
  useEffect(() => {
    if (Array.isArray(claimsData) && claimsData.length > 0) {
      setClaims(claimsData);
      setUsingMockData(false);
    } else if (error) {
      setClaims(MOCK_CLAIMS);
      setUsingMockData(true);
    }
  }, [claimsData, error]);

  const handleOverride = async (claimId, newStatus) => {
    setActionLoading(prev => ({ ...prev, [claimId]: newStatus }));
    setActionError(null);
    try {
      // Use dynamic URL for the override endpoint
      const endpoint = `/admin/claims/${claimId}/override`;
      const res = await fetch(`http://localhost:8003${endpoint}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer admin_token"
        },
        body: JSON.stringify({ status: newStatus })
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP error! status: ${res.status}`);
      }

      // Remove the claim from the list after successful override
      setClaims(prev => prev.filter(claim => claim.id !== claimId));
      setActionError(null);
      
      // Refetch to get updated data
      refetch();
    } catch (err) {
      console.error("Failed to override claim:", err);
      setActionError(err.message || "Failed to update claim. Please try again.");
    } finally {
      setActionLoading(prev => {
        const next = { ...prev };
        delete next[claimId];
        return next;
      });
    }
  };

  // Safe filtering with default empty array
  const displayClaims = Array.isArray(claims) ? claims : [];
  
  // Apply filter and search
  let filteredClaims = displayClaims;
  if (filterStatus !== "all") {
    filteredClaims = filteredClaims.filter(c => c.status === filterStatus);
  }
  if (searchTerm) {
    filteredClaims = filteredClaims.filter(c => 
      String(c.rider_id).includes(searchTerm) || 
      String(c.id).includes(searchTerm) ||
      String(c.disruption_event_id).includes(searchTerm)
    );
  }

  const pendingClaims = displayClaims.filter(c => c.status === "pending" || c.status === "in_review");
  const inReviewClaims = displayClaims.filter(c => c.status === "in_review");
  const approvedClaims = displayClaims.filter(c => c.status === "paid" || c.status === "approved");
  const pendingValue = pendingClaims.reduce((acc, c) => acc + (c.final_payout || c.calculated_payout || 0), 0);

  // Status badge helper
  function getStatusBadge(status) {
    switch (status) {
      case "pending":
        return <Badge variant="amber">Pending</Badge>;
      case "in_review":
        return <Badge variant="red">In Review</Badge>;
      case "approved":
        return <Badge variant="green">Approved</Badge>;
      case "paid":
        return <Badge variant="green">Paid</Badge>;
      case "rejected":
        return <Badge variant="red">Rejected</Badge>;
      default:
        return <Badge variant="gray">{status}</Badge>;
    }
  }

  // Determine if actions are available for this status
  function canTakeAction(status) {
    return status === "pending" || status === "in_review";
  }

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Claims queue (Module 3)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard 
            title="Pending & In Review" 
            value={loading ? "..." : pendingClaims.length} 
            subtext="Awaiting decision" 
            trend={pendingClaims.length > 0 ? "warn" : "down"} 
          />
          <MetricCard 
            title="In review (fraud)" 
            value={loading ? "..." : inReviewClaims.length} 
            subtext="Flagged for manual review" 
            trend={inReviewClaims.length > 0 ? "warn" : "none"} 
          />
          <MetricCard 
            title="Approved/Paid" 
            value={loading ? "..." : approvedClaims.length} 
            subtext="System & Manual" 
            trend="up" 
          />
          <MetricCard 
            title="Pending Value" 
            value={loading ? "..." : `₹${pendingValue.toFixed(2)}`} 
            subtext="Exposure" 
            trend="up" 
          />
        </div>
        
        {usingMockData && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md text-xs text-blue-800">
            ℹ️ <strong>Demo Mode:</strong> Showing sample data. Start the Module 3 backend (port 8003) for live claims.
          </div>
        )}
        
        {error && !usingMockData && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800">
            ⚠️ Failed to fetch claims from Module 3. Make sure it's running on port 8003.
          </div>
        )}
        
        {actionError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md text-xs text-red-800">
            ❌ {actionError}
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
              placeholder="Search claim ID, worker ID, or event..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-slate-400 w-full max-w-sm"
            />
            <select 
              value={filterStatus} 
              onChange={e => setFilterStatus(e.target.value)}
              className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-slate-400"
            >
              <option value="all">All statuses</option>
              <option value="pending">Pending</option>
              <option value="in_review">In Review</option>
              <option value="approved">Approved</option>
              <option value="paid">Paid</option>
              <option value="rejected">Rejected</option>
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
                {loading && filteredClaims.length === 0 ? (
                  <tr><td colSpan="7" className="py-4 text-center text-slate-500">Loading claims...</td></tr>
                ) : usingMockData && filteredClaims.length === 0 ? (
                  <tr><td colSpan="7" className="py-4 text-center text-blue-600">Demo Mode: No live data available</td></tr>
                ) : filteredClaims.length > 0 ? (
                  filteredClaims.map(claim => (
                    <tr key={claim.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-2 font-mono font-medium">C-{claim.id}</td>
                      <td className="py-3 px-2 font-mono text-slate-600">W-{claim.rider_id}</td>
                      <td className="py-3 px-2 text-slate-600">{claim.disruption_event_id}</td>
                      <td className="py-3 px-2">
                        <Badge variant={claim.tier === 'raksha' ? 'amber' : claim.tier === 'suraksha' ? 'blue' : 'gray'}>
                          {claim.tier ? claim.tier.charAt(0).toUpperCase() + claim.tier.slice(1) : 'N/A'}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 font-mono">₹{claim.final_payout || claim.calculated_payout || 0}</td>
                      <td className="py-3 px-2">
                        {getStatusBadge(claim.status)}
                      </td>
                      <td className="py-3 px-2 flex gap-1">
                        {canTakeAction(claim.status) ? (
                          <>
                            <Button 
                              size="sm" 
                              disabled={!!actionLoading[claim.id]} 
                              onClick={() => handleOverride(claim.id, "approved")} 
                              className="h-6 text-[10px] px-2 bg-green-600 hover:bg-green-700"
                            >
                              {actionLoading[claim.id] === "approved" ? "..." : "✓"}
                            </Button>
                            <Button 
                              size="sm" 
                              disabled={!!actionLoading[claim.id]} 
                              onClick={() => handleOverride(claim.id, "rejected")} 
                              variant="destructive" 
                              className="h-6 text-[10px] px-2"
                            >
                              {actionLoading[claim.id] === "rejected" ? "..." : "✗"}
                            </Button>
                          </>
                        ) : (
                          <span className="text-slate-400 text-[10px]">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan="7" className="py-4 text-center text-slate-500">No claims match your search. Run a simulation to generate data.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Status Legend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Claim Status Reference</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
            <div className="flex items-center gap-2">
              <Badge variant="amber">Pending</Badge>
              <span className="text-slate-600">Awaiting initial review</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="red">In Review</Badge>
              <span className="text-slate-600">Fraud signals detected</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="green">Approved</Badge>
              <span className="text-slate-600">Manual approval given</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="green">Paid</Badge>
              <span className="text-slate-600">Payout processed</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="red">Rejected</Badge>
              <span className="text-slate-600">Claim denied</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
