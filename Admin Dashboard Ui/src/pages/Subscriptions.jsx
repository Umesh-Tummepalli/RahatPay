import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const tierData = [
  { name: 'Bronze', workers: 6740, fill: '#94a3b8' },
  { name: 'Silver', workers: 3870, fill: 'var(--color-primary)' },
  { name: 'Gold', workers: 1871, fill: 'var(--color-warning)' },
];

export default function Subscriptions() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Subscriptions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Total subscribers" value="12,481" subtext="↑ 340 this week" trend="up" />
          <MetricCard title="Monthly revenue" value="₹18.7L" subtext="↑ 6.2% MoM" trend="up" />
          <MetricCard title="Churn this month" value="312" subtext="2.5% churn rate" trend="down" />
          <MetricCard title="Payment failures" value="58" subtext="Retry pending" trend="warn" />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Tier distribution</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
                <span className="text-slate-500">Bronze · ₹79/mo · 50% recovery</span>
                <span className="font-mono text-slate-700">6,740 workers</span>
              </div>
              <div className="flex justify-between items-center text-xs pb-2 border-b border-slate-100">
                <span className="text-slate-500">Silver · ₹129/mo · 65% recovery</span>
                <span className="font-mono text-slate-700">3,870 workers</span>
              </div>
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500">Gold · ₹199/mo · 80% recovery</span>
                <span className="font-mono text-slate-700">1,871 workers</span>
              </div>
            </div>
            
            <div className="h-[140px] w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={tierData} layout="vertical" margin={{ top: 0, right: 30, left: 0, bottom: 0 }}>
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} width={50} />
                  <Tooltip 
                    cursor={{ fill: 'transparent' }}
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                  />
                  <Bar dataKey="workers" radius={[0, 4, 4, 0]} barSize={16} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Payment failures needing retry</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="pb-3 font-semibold">Worker ID</th>
                  <th className="pb-3 font-semibold">Tier</th>
                  <th className="pb-3 font-semibold">Failed on</th>
                  <th className="pb-3 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 font-mono font-medium">W-4450</td>
                  <td className="py-3"><Badge variant="gray">Silver</Badge></td>
                  <td className="py-3 text-slate-500">Mar 29</td>
                  <td className="py-3"><Button variant="outline" size="sm" className="h-6 text-[10px] px-3">Retry</Button></td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 font-mono font-medium">W-6612</td>
                  <td className="py-3"><Badge variant="amber">Gold</Badge></td>
                  <td className="py-3 text-slate-500">Mar 28</td>
                  <td className="py-3"><Button variant="outline" size="sm" className="h-6 text-[10px] px-3">Retry</Button></td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
