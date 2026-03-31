import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, AreaChart, Area } from "recharts";

const lossRatioData = [
  { name: "Bronze", value: 52, fill: "var(--color-success)" },
  { name: "Silver", value: 68, fill: "var(--color-warning)" },
  { name: "Gold", value: 84, fill: "var(--color-danger)" },
];

const claimVolumeData = [
  { month: "Jan", volume: 940 },
  { month: "Feb", volume: 1080 },
  { month: "Mar", volume: 1404 },
  { month: "Apr", volume: 1836 },
];

export default function Actuarial() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Actuarial overview
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Loss ratio (MTD)" value="68%" subtext="↑ 4% vs last month" trend="down" />
          <MetricCard title="Premiums collected" value="₹18.7L" subtext="This month" trend="up" />
          <MetricCard title="Claims paid" value="₹42.3L" subtext="1,836 claims" trend="none" />
          <MetricCard title="Payout cap hits" value="34" subtext="Event-level cap formula" trend="none" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Loss ratio by tier</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="h-[180px] w-full mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={lossRatioData} layout="vertical" margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
                  <XAxis type="number" hide domain={[0, 100]} />
                  <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} width={60} />
                  <Tooltip 
                    cursor={{ fill: 'transparent' }}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={12} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            <div className="pt-4 border-t border-slate-100 space-y-3">
              <h4 className="text-xs font-semibold text-slate-700 mb-2">Payout cap utilization</h4>
              <div className="flex justify-between items-center text-xs text-slate-600">
                <span>Claims at cap ceiling</span>
                <span className="font-mono font-medium text-slate-800">34 (1.85%)</span>
              </div>
              <div className="flex justify-between items-center text-xs text-slate-600">
                <span>Avg payout as % of cap</span>
                <span className="font-mono font-medium text-slate-800">72%</span>
              </div>
              <div className="flex justify-between items-center text-xs text-slate-600">
                <span>Max single event payout</span>
                <span className="font-mono font-medium text-slate-800">₹2,000</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Monthly claim volume</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="h-[220px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={claimVolumeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Area type="monotone" dataKey="volume" stroke="var(--color-primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorVolume)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
