import React, { useMemo, useState } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from "recharts";
import { useApi } from "../hooks/useApi";

const statusColors = {
  Verified: "var(--color-success)",
  Pending: "var(--color-warning)",
  Rejected: "var(--color-danger)",
};

function formatRelative(timestamp) {
  if (!timestamp) return "Unknown";

  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now - then;
  const diffHours = Math.max(1, Math.floor(diffMs / (1000 * 60 * 60)));

  if (diffHours < 24) return `${diffHours} hr ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
}

export default function Kyc() {
  const { data: workers, loading, error } = useApi("/admin/workers", []);
  const [actionLoading, setActionLoading] = useState({});
  const [pageError, setPageError] = useState(null);

  const allWorkers = Array.isArray(workers) ? workers : [];

  const pendingWorkers = useMemo(
    () => allWorkers.filter(worker => !worker.kyc_verified && !worker.is_blocked),
    [allWorkers]
  );

  const verifiedWorkers = useMemo(
    () => allWorkers.filter(worker => worker.kyc_verified),
    [allWorkers]
  );

  const rejectedWorkers = useMemo(
    () => allWorkers.filter(worker => !worker.kyc_verified && worker.is_blocked),
    [allWorkers]
  );

  const chartData = [
    { name: "Verified", value: verifiedWorkers.length, color: statusColors.Verified },
    { name: "Pending", value: pendingWorkers.length, color: statusColors.Pending },
    { name: "Rejected", value: rejectedWorkers.length, color: statusColors.Rejected },
  ];

  const handleKycAction = async (workerId, action) => {
    setActionLoading(prev => ({ ...prev, [workerId]: action }));
    setPageError(null);

    try {
      const endpoint =
        action === "approve"
          ? `/admin/workers/${workerId}/verify-kyc`
          : `/admin/workers/${workerId}/review-kyc`;

      const options =
        action === "approve"
          ? {
              method: "PATCH",
              headers: {
                Authorization: "Bearer admin_token",
                "Content-Type": "application/json",
              },
            }
          : {
              method: "PATCH",
              headers: {
                Authorization: "Bearer admin_token",
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                action: "reject",
                reason: "Rejected from admin KYC queue",
              }),
            };

      const response = await fetch(endpoint, options);
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.detail || `HTTP error! status: ${response.status}`);
      }

      window.location.reload();
    } catch (err) {
      console.error("Failed to review KYC:", err);
      setPageError(err.message || "Failed to update KYC status.");
    } finally {
      setActionLoading(prev => {
        const next = { ...prev };
        delete next[workerId];
        return next;
      });
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          KYC / Onboarding
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Pending review" value={loading ? "..." : pendingWorkers.length} subtext="Awaiting admin" trend="warn" />
          <MetricCard title="Verified" value={loading ? "..." : verifiedWorkers.length} subtext="Approved KYC" trend="up" />
          <MetricCard title="Rejected" value={loading ? "..." : rejectedWorkers.length} subtext="Needs resubmission" trend="none" />
          <MetricCard title="Review coverage" value={loading ? "..." : `${allWorkers.length ? Math.round((verifiedWorkers.length / allWorkers.length) * 100) : 0}%`} subtext="Verified share" trend="none" />
        </div>
        {(pageError || error) && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-md text-xs text-amber-800">
            {pageError || "Failed to load KYC queue. Make sure Module 1 is running on port 8001."}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Pending KYC queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Worker ID</th>
                    <th className="pb-3 pr-4 font-semibold">Name</th>
                    <th className="pb-3 pr-4 font-semibold">Submitted</th>
                    <th className="pb-3 pr-4 font-semibold">Doc type</th>
                    <th className="pb-3 pr-4 font-semibold">Platform</th>
                    <th className="pb-3 font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loading ? (
                    <tr>
                      <td colSpan="6" className="py-4 text-center text-slate-500">Loading KYC queue...</td>
                    </tr>
                  ) : pendingWorkers.length > 0 ? (
                    pendingWorkers.map(worker => (
                      <tr key={worker.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-4 pr-4 font-mono font-medium">{worker.partner_id}</td>
                        <td className="py-4 pr-4">{worker.name}</td>
                        <td className="py-4 pr-4 text-slate-500">{formatRelative(worker.created_at)}</td>
                        <td className="py-4 pr-4 text-slate-600">{worker.kyc_document_type || "Unknown"}</td>
                        <td className="py-4 pr-4 text-slate-600 capitalize">{worker.platform}</td>
                        <td className="py-4 flex gap-2">
                          <Button
                            size="sm"
                            disabled={!!actionLoading[worker.id]}
                            onClick={() => handleKycAction(worker.id, "approve")}
                            className="h-7 text-[10px] px-3"
                          >
                            {actionLoading[worker.id] === "approve" ? "Approving..." : "Approve"}
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            disabled={!!actionLoading[worker.id]}
                            onClick={() => handleKycAction(worker.id, "reject")}
                            className="h-7 text-[10px] px-3"
                          >
                            {actionLoading[worker.id] === "reject" ? "Rejecting..." : "Reject"}
                          </Button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="6" className="py-4 text-center text-slate-500">No pending KYC reviews right now.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>KYC status breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="h-[200px] w-full mt-[-10px] mb-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip
                    contentStyle={{ borderRadius: "8px", border: "none", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)", fontSize: "12px" }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Verified</span>
                <Badge variant="green">{verifiedWorkers.length}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Pending</span>
                <Badge variant="amber">{pendingWorkers.length}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Rejected</span>
                <Badge variant="red">{rejectedWorkers.length}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
