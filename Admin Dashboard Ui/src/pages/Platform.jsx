import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";

export default function Platform() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Platform health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Swiggy API uptime" value="99.8%" subtext="Last 30 days" trend="up" />
          <MetricCard title="Zomato API uptime" value="99.3%" subtext="Last 30 days" trend="up" />
          <MetricCard title="KYC service" value="Degraded" subtext="↑ latency 2.1s" trend="down" />
          <MetricCard title="Payout gateway" value="Healthy" subtext="0 failures today" trend="up" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>API sync status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-500">Swiggy — last sync</span>
              <div className="flex items-center gap-2">
                <Badge variant="green">Live</Badge>
                <span className="text-slate-500">4 min ago</span>
              </div>
            </div>
            <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-500">Zomato — last sync</span>
              <div className="flex items-center gap-2">
                <Badge variant="green">Live</Badge>
                <span className="text-slate-500">7 min ago</span>
              </div>
            </div>
            <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-500">Sync frequency</span>
              <span className="text-slate-800">Every 5 min</span>
            </div>
            <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-500">Records synced today</span>
              <span className="text-slate-800 font-mono">1,42,840</span>
            </div>
            <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
              <span className="text-slate-500">Isolation Forest batch</span>
              <Badge variant="blue">2:00 AM daily</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Service health log</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <span className="w-16 shrink-0 text-[10px] font-mono text-slate-400 mt-1">10:42 AM</span>
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-success)] shadow-[0_0_5px_var(--color-success)]" />
              <div>
                <p className="text-[13px] text-slate-800 leading-tight">Swiggy API sync completed</p>
                <p className="text-[11px] text-slate-500 mt-1">72,440 records · 1.2s</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="w-16 shrink-0 text-[10px] font-mono text-slate-400 mt-1">10:37 AM</span>
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-success)]" />
              <div>
                <p className="text-[13px] text-slate-800 leading-tight">Zomato API sync completed</p>
                <p className="text-[11px] text-slate-500 mt-1">70,400 records · 1.4s</p>
              </div>
            </div>
            <div className="flex gap-4">
              <span className="w-16 shrink-0 text-[10px] font-mono text-slate-400 mt-1">09:11 AM</span>
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-warning)]" />
              <div>
                <p className="text-[13px] text-slate-800 leading-tight">KYC service latency spike</p>
                <p className="text-[11px] text-slate-500 mt-1">P99 latency: 2,100ms (threshold: 1,000ms)</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
