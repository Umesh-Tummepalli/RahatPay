import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export default function Claims() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Claims queue
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Open claims" value="214" subtext="Pending review" trend="warn" />
          <MetricCard title="Approved today" value="87" subtext="₹1.04L paid" trend="up" />
          <MetricCard title="Flagged claims" value="12" subtext="Manual check needed" trend="down" />
          <MetricCard title="Avg payout" value="₹1,190" subtext="Across all tiers" trend="none" />
        </div>
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
              className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-[var(--color-primary)] w-full max-w-sm"
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
                  <th className="py-3 px-2 font-semibold">Trigger</th>
                  <th className="py-3 px-2 font-semibold">Tier</th>
                  <th className="py-3 px-2 font-semibold">Amount</th>
                  <th className="py-3 px-2 font-semibold">Status</th>
                  <th className="py-3 px-2 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">C-8821</td>
                  <td className="py-3 px-2 font-mono">W-4821</td>
                  <td className="py-3 px-2 text-slate-600">Rain disruption</td>
                  <td className="py-3 px-2"><Badge variant="gray">Silver</Badge></td>
                  <td className="py-3 px-2 font-mono">₹1,200</td>
                  <td className="py-3 px-2"><Badge variant="amber">Pending</Badge></td>
                  <td className="py-3 px-2 flex gap-1">
                    <Button size="sm" className="h-6 text-[10px] px-2">Approve</Button>
                    <Button size="sm" variant="destructive" className="h-6 text-[10px] px-2">Reject</Button>
                  </td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">C-8819</td>
                  <td className="py-3 px-2 font-mono">W-7190</td>
                  <td className="py-3 px-2 text-slate-600">Rain disruption</td>
                  <td className="py-3 px-2"><Badge variant="gray">Bronze</Badge></td>
                  <td className="py-3 px-2 font-mono">₹700</td>
                  <td className="py-3 px-2"><Badge variant="green">Approved</Badge></td>
                  <td className="py-3 px-2 flex gap-1 text-slate-400">—</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
