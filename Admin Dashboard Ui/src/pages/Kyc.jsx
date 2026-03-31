import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from "recharts";

const kycStatusData = [
  { name: 'Verified', value: 82, color: 'var(--color-success)' },
  { name: 'Pending', value: 14, color: 'var(--color-warning)' },
  { name: 'Rejected', value: 4, color: 'var(--color-danger)' },
];

export default function Kyc() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          KYC / Onboarding
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Pending review" value="342" subtext="Awaiting admin" trend="warn" />
          <MetricCard title="Verified today" value="48" subtext="↑ vs yesterday" trend="up" />
          <MetricCard title="Rejected today" value="7" subtext="Doc mismatch" trend="none" />
          <MetricCard title="Avg review time" value="3.2h" subtext="Median turnaround" trend="none" />
        </div>
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
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-4 pr-4 font-mono font-medium">W-7190</td>
                    <td className="py-4 pr-4">Arjun Menon</td>
                    <td className="py-4 pr-4 text-slate-500">2 hr ago</td>
                    <td className="py-4 pr-4 text-slate-600">Aadhaar</td>
                    <td className="py-4 pr-4 text-slate-600">Swiggy</td>
                    <td className="py-4 flex gap-2">
                      <Button size="sm" className="h-7 text-[10px] px-3">Approve</Button>
                      <Button size="sm" variant="destructive" className="h-7 text-[10px] px-3">Reject</Button>
                    </td>
                  </tr>
                  <tr className="hover:bg-slate-50 transition-colors">
                    <td className="py-4 pr-4 font-mono font-medium">W-5501</td>
                    <td className="py-4 pr-4">Raman S</td>
                    <td className="py-4 pr-4 text-slate-500">4 hr ago</td>
                    <td className="py-4 pr-4 text-slate-600">PAN + Aadhaar</td>
                    <td className="py-4 pr-4 text-slate-600">Zomato</td>
                    <td className="py-4 flex gap-2">
                      <Button size="sm" className="h-7 text-[10px] px-3">Approve</Button>
                      <Button size="sm" variant="destructive" className="h-7 text-[10px] px-3">Reject</Button>
                    </td>
                  </tr>
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
                    data={kycStatusData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {kycStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <RechartsTooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)', fontSize: '12px' }}
                    formatter={(value) => [`${value}%`]}
                  />
                  <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
