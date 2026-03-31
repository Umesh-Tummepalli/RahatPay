import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export default function Fraud() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Fraud alerts
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Active alerts" value="27" subtext="3 critical" trend="warn" />
          <MetricCard title="Resolved today" value="8" subtext="By admin team" trend="up" />
          <MetricCard title="Auto-blocked" value="4" subtext="Rule-triggered" trend="none" />
          <MetricCard title="False positives" value="2" subtext="This batch" trend="none" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Alert feed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <span className="w-16 shrink-0 text-[10px] font-mono text-slate-400 mt-1">14 min</span>
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-danger)] shadow-[0_0_5px_var(--color-danger)]" />
              <div>
                <p className="text-[13px] text-slate-800 leading-tight">Zone cap exceeded — Koramangala (38/30)</p>
                <p className="text-[11px] text-slate-500 mt-1">Identity/onboarding fraud · Auto-flagged</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="w-16 shrink-0 text-[10px] font-mono text-slate-400 mt-1">1 hr</span>
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-warning)]" />
              <div>
                <p className="text-[13px] text-slate-800 leading-tight">Referral chain depth 5 — root node W-5512</p>
                <p className="text-[11px] text-slate-500 mt-1">Collusion fraud · Depth limit is 4</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Manual review queue</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="pb-3 px-2 font-semibold">Worker</th>
                  <th className="pb-3 px-2 font-semibold">Alert type</th>
                  <th className="pb-3 px-2 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">W-6641</td>
                  <td className="py-3 px-2"><Badge variant="red">GPS mismatch</Badge></td>
                  <td className="py-3 px-2 flex gap-1">
                    <Button size="sm" variant="destructive" className="h-6 text-[10px] px-2">Block</Button>
                    <Button size="sm" variant="outline" className="h-6 text-[10px] px-2">Clear</Button>
                  </td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">W-5512</td>
                  <td className="py-3 px-2"><Badge variant="amber">Collusion root</Badge></td>
                  <td className="py-3 px-2 flex gap-1">
                    <Button size="sm" variant="destructive" className="h-6 text-[10px] px-2">Block</Button>
                    <Button size="sm" variant="outline" className="h-6 text-[10px] px-2">Clear</Button>
                  </td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
