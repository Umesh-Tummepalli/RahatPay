import React, { useMemo, useState } from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useApi } from "../hooks/useApi";

function formatMoney(amount) {
  return `₹${Number(amount || 0).toFixed(2)}`;
}

function formatDateTime(value) {
  if (!value) return "Pending";
  const date = new Date(value);
  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Payouts() {
  const { data: payouts, loading, error } = useApi("/admin/payouts/live", []);
  const [tab, setTab] = useState("all");

  const payoutRows = Array.isArray(payouts) ? payouts : [];
  const filteredRows = useMemo(() => {
    if (tab === "all") return payoutRows;
    return payoutRows.filter(row => row.status === tab);
  }, [payoutRows, tab]);

  const totalDisbursed = payoutRows
    .filter(row => row.status === "success")
    .reduce((sum, row) => sum + Number(row.amount || 0), 0);

  const pendingDisbursal = payoutRows
    .filter(row => row.status === "processing" || row.status === "initiated")
    .reduce((sum, row) => sum + Number(row.amount || 0), 0);

  const failedCount = payoutRows.filter(row => row.status === "failed").length;
  const successTodayCount = payoutRows.filter(row => {
    if (!row.completed_at) return false;
    return new Date(row.completed_at).toDateString() === new Date().toDateString();
  }).length;

  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Payout history
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Total disbursed" value={loading ? "..." : formatMoney(totalDisbursed)} subtext={`${payoutRows.filter(row => row.status === "success").length} successful payouts`} trend="none" />
          <MetricCard title="Disbursed today" value={loading ? "..." : successTodayCount} subtext="Completed today" trend="up" />
          <MetricCard title="Pending disbursal" value={loading ? "..." : formatMoney(pendingDisbursal)} subtext={`${payoutRows.filter(row => row.status === "processing" || row.status === "initiated").length} in queue`} trend="warn" />
          <MetricCard title="Failed payouts" value={loading ? "..." : failedCount} subtext="Needs retry or review" trend="none" />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Payout log</CardTitle>
          <div className="flex gap-4 mt-2 border-b border-slate-100">
            <button onClick={() => setTab("all")} className={`text-[11px] font-medium pb-2 ${tab === "all" ? "text-(--color-primary) border-b-2 border-(--color-primary)" : "text-slate-500 hover:text-slate-700"}`}>All</button>
            <button onClick={() => setTab("success")} className={`text-[11px] font-medium pb-2 ${tab === "success" ? "text-(--color-primary) border-b-2 border-(--color-primary)" : "text-slate-500 hover:text-slate-700"}`}>Disbursed</button>
            <button onClick={() => setTab("processing")} className={`text-[11px] font-medium pb-2 ${tab === "processing" ? "text-(--color-primary) border-b-2 border-(--color-primary)" : "text-slate-500 hover:text-slate-700"}`}>Pending</button>
            <button onClick={() => setTab("failed")} className={`text-[11px] font-medium pb-2 ${tab === "failed" ? "text-(--color-primary) border-b-2 border-(--color-primary)" : "text-slate-500 hover:text-slate-700"}`}>Failed</button>
          </div>
        </CardHeader>
        <CardContent className="pt-2">
          {error && (
            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              Failed to load payouts. Make sure Module 1 is running on port 8001.
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="pb-3 px-2 font-semibold">Payout ID</th>
                  <th className="pb-3 px-2 font-semibold">Worker</th>
                  <th className="pb-3 px-2 font-semibold">Claim ID</th>
                  <th className="pb-3 px-2 font-semibold">Amount</th>
                  <th className="pb-3 px-2 font-semibold">Method</th>
                  <th className="pb-3 px-2 font-semibold">Initiated</th>
                  <th className="pb-3 px-2 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr><td colSpan="7" className="py-4 text-center text-slate-500">Loading payouts...</td></tr>
                ) : filteredRows.length > 0 ? (
                  filteredRows.map(row => (
                    <tr key={row.id} className="hover:bg-slate-50 transition-colors">
                      <td className="py-3 px-2 font-mono font-medium">P-{row.id}</td>
                      <td className="py-3 px-2">
                        <div className="font-mono">{row.partner_id}</div>
                        <div className="text-slate-500">{row.worker_name}</div>
                      </td>
                      <td className="py-3 px-2 font-mono text-slate-500">C-{row.claim_id}</td>
                      <td className="py-3 px-2 font-mono">{formatMoney(row.amount)}</td>
                      <td className="py-3 px-2 text-slate-600 uppercase">{row.gateway}</td>
                      <td className="py-3 px-2 text-slate-500">{formatDateTime(row.initiated_at)}</td>
                      <td className="py-3 px-2">
                        {row.status === "success" && <Badge variant="green">Disbursed</Badge>}
                        {row.status === "processing" && <Badge variant="amber">Pending</Badge>}
                        {row.status === "initiated" && <Badge variant="amber">Initiated</Badge>}
                        {row.status === "failed" && <Badge variant="red">Failed</Badge>}
                        {row.status === "reversed" && <Badge variant="gray">Reversed</Badge>}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan="7" className="py-4 text-center text-slate-500">No payout records yet. Run a disaster simulation first.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
