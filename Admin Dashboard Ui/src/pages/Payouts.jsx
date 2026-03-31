import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";

export default function Payouts() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Payout history
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Total disbursed (MTD)" value="₹42.3L" subtext="1,836 claims" trend="none" />
          <MetricCard title="Disbursed today" value="₹1.04L" subtext="87 claims" trend="up" />
          <MetricCard title="Pending disbursal" value="₹2.8L" subtext="214 in queue" trend="warn" />
          <MetricCard title="Rejected this month" value="₹1.2L" subtext="94 claims" trend="none" />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Payout log</CardTitle>
          <div className="flex gap-4 mt-2 border-b border-slate-100">
            <button className="text-[11px] font-medium text-[var(--color-primary)] border-b-2 border-[var(--color-primary)] pb-2">All</button>
            <button className="text-[11px] font-medium text-slate-500 pb-2 hover:text-slate-700">Disbursed</button>
            <button className="text-[11px] font-medium text-slate-500 pb-2 hover:text-slate-700">Pending</button>
            <button className="text-[11px] font-medium text-slate-500 pb-2 hover:text-slate-700">Failed</button>
          </div>
        </CardHeader>
        <CardContent className="pt-2">
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
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">P-2211</td>
                  <td className="py-3 px-2 font-mono">W-7190</td>
                  <td className="py-3 px-2 font-mono text-slate-500">C-8819</td>
                  <td className="py-3 px-2 font-mono">₹700</td>
                  <td className="py-3 px-2 text-slate-600">UPI</td>
                  <td className="py-3 px-2 text-slate-500">10:02 AM</td>
                  <td className="py-3 px-2"><Badge variant="green">Disbursed</Badge></td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">P-2209</td>
                  <td className="py-3 px-2 font-mono">W-4821</td>
                  <td className="py-3 px-2 font-mono text-slate-500">C-8821</td>
                  <td className="py-3 px-2 font-mono">₹1,200</td>
                  <td className="py-3 px-2 text-slate-600">UPI</td>
                  <td className="py-3 px-2 text-slate-500">10:42 AM</td>
                  <td className="py-3 px-2"><Badge variant="amber">Pending</Badge></td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
