import React from "react";
import { Badge } from "../components/ui/Badge";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from "recharts";

const claimsByTriggerData = [
  { name: 'Rain', value: 72, color: 'var(--color-primary)' },
  { name: 'App outage', value: 14, color: '#3cbd9b' }, // teal
  { name: 'Lockdown', value: 9, color: 'var(--color-warning)' },
  { name: 'Other', value: 5, color: '#94a3b8' },
];

const subscriptionSplitData = [
  { name: 'Bronze', value: 6740, color: '#94a3b8' },
  { name: 'Silver', value: 3870, color: 'var(--color-primary)' },
  { name: 'Gold', value: 1871, color: 'var(--color-warning)' },
];

export default function Dashboard() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Platform overview
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Active workers" value="12,481" subtext="↑ 340 this week" trend="up" />
          <MetricCard title="Claims this month" value="1,836" subtext="₹42.3L paid out" trend="none" />
          <MetricCard title="Loss ratio" value="68%" subtext="↑ 4% vs last month" trend="down" />
          <MetricCard title="Fraud flags (batch)" value="27" subtext="3 need manual review" trend="warn" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent claims</CardTitle>
            <span className="text-xs text-[var(--color-primary)] hover:underline cursor-pointer font-medium">
              View all →
            </span>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="pb-3 pr-4 font-semibold">Worker</th>
                    <th className="pb-3 pr-4 font-semibold">Trigger</th>
                    <th className="pb-3 pr-4 font-semibold">Tier</th>
                    <th className="pb-3 pr-4 font-semibold">Amount</th>
                    <th className="pb-3 pr-4 font-semibold">Platform</th>
                    <th className="pb-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 pr-4 font-mono font-medium">W-4821</td>
                    <td className="py-3 pr-4 text-slate-600">Rain disruption</td>
                    <td className="py-3 pr-4"><Badge variant="gray">Silver</Badge></td>
                    <td className="py-3 pr-4 font-mono text-slate-700">₹1,200</td>
                    <td className="py-3 pr-4 text-slate-600">Swiggy</td>
                    <td className="py-3"><Badge variant="amber">Pending</Badge></td>
                  </tr>
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 pr-4 font-mono font-medium">W-3302</td>
                    <td className="py-3 pr-4 text-slate-600">App outage</td>
                    <td className="py-3 pr-4"><Badge variant="amber">Gold</Badge></td>
                    <td className="py-3 pr-4 font-mono text-slate-700">₹2,000</td>
                    <td className="py-3 pr-4 text-slate-600">Zomato</td>
                    <td className="py-3"><Badge variant="blue">In review</Badge></td>
                  </tr>
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 pr-4 font-mono font-medium">W-7190</td>
                    <td className="py-3 pr-4 text-slate-600">Rain disruption</td>
                    <td className="py-3 pr-4"><Badge variant="gray">Bronze</Badge></td>
                    <td className="py-3 pr-4 font-mono text-slate-700">₹700</td>
                    <td className="py-3 pr-4 text-slate-600">Swiggy</td>
                    <td className="py-3"><Badge variant="green">Approved</Badge></td>
                  </tr>
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 pr-4 font-mono font-medium">W-6641</td>
                    <td className="py-3 pr-4 text-slate-600">Area lockdown</td>
                    <td className="py-3 pr-4"><Badge variant="amber">Gold</Badge></td>
                    <td className="py-3 pr-4 font-mono text-slate-700">₹2,000</td>
                    <td className="py-3 pr-4 text-slate-600">Zomato</td>
                    <td className="py-3"><Badge variant="red">Flagged</Badge></td>
                  </tr>
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 pr-4 font-mono font-medium">W-2218</td>
                    <td className="py-3 pr-4 text-slate-600">App outage</td>
                    <td className="py-3 pr-4"><Badge variant="gray">Silver</Badge></td>
                    <td className="py-3 pr-4 font-mono text-slate-700">₹1,200</td>
                    <td className="py-3 pr-4 text-slate-600">Swiggy</td>
                    <td className="py-3"><Badge variant="amber">Pending</Badge></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Fraud alerts</CardTitle>
            <span className="text-xs text-[var(--color-primary)] hover:underline cursor-pointer font-medium">
              View all →
            </span>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-3 items-start border-b border-slate-100 pb-3">
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-danger)] shadow-[0_0_5px_var(--color-danger)]" />
              <div>
                <p className="text-sm text-slate-800 leading-tight">Zone cap exceeded — Koramangala</p>
                <p className="text-[11px] text-slate-500 mt-1">Identity · 14 min ago</p>
              </div>
            </div>
            <div className="flex gap-3 items-start border-b border-slate-100 pb-3">
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-warning)]" />
              <div>
                <p className="text-sm text-slate-800 leading-tight">Referral chain depth {"\u003e"} 4, root W-5512</p>
                <p className="text-[11px] text-slate-500 mt-1">Collusion · 1 hr ago</p>
              </div>
            </div>
            <div className="flex gap-3 items-start border-b border-slate-100 pb-3">
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-warning)]" />
              <div>
                <p className="text-sm text-slate-800 leading-tight">Filing spike: 42 claims / 20 min, HSR</p>
                <p className="text-[11px] text-slate-500 mt-1">Systemic · 3 hr ago</p>
              </div>
            </div>
            <div className="flex gap-3 items-start">
              <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-[var(--color-primary)]" />
              <div>
                <p className="text-sm text-slate-800 leading-tight">GPS mismatch — W-8803</p>
                <p className="text-[11px] text-slate-500 mt-1">GPS/location · 6 hr ago</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Claims by trigger</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="h-[200px] w-full mt-[-20px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={claimsByTriggerData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {claimsByTriggerData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Subscription split</CardTitle>
          </CardHeader>
          <CardContent className="pt-2">
            <div className="h-[200px] w-full mt-[-20px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={subscriptionSplitData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {subscriptionSplitData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Platform health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pb-4">
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Swiggy API</span>
              <Badge variant="green">Live</Badge>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Zomato API</span>
              <Badge variant="green">Live</Badge>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">Isolation Forest</span>
              <Badge variant="blue">2 AM batch</Badge>
            </div>
            <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
              <span className="text-slate-500">KYC Service</span>
              <Badge variant="amber">Degraded</Badge>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-500">Payouts</span>
              <Badge variant="green">Healthy</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
