import React from "react";
import { Badge } from "../components/ui/Badge";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";

export default function Workers() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Worker management
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Total registered" value="14,203" subtext="All time" trend="none" />
          <MetricCard title="Active subscribers" value="12,481" subtext="88% active rate" trend="up" />
          <MetricCard title="Pending KYC" value="342" subtext="Needs action" trend="warn" />
          <MetricCard title="Blocked accounts" value="89" subtext="12 this week" trend="down" />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-slate-100">
          <CardTitle>Worker registry</CardTitle>
          <Button size="sm">
            + Add worker
          </Button>
        </CardHeader>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-2 mb-4">
            <input 
              type="text" 
              placeholder="Search by name, ID, phone..." 
              className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none focus:border-[var(--color-primary)] w-full max-w-sm"
            />
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All platforms</option>
              <option>Swiggy</option>
              <option>Zomato</option>
            </select>
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All tiers</option>
              <option>Bronze</option>
              <option>Silver</option>
              <option>Gold</option>
            </select>
            <select className="bg-slate-50 border border-slate-200 rounded-md px-3 py-1.5 text-xs outline-none text-slate-600">
              <option>All statuses</option>
              <option>Active</option>
              <option>Pending KYC</option>
              <option>Blocked</option>
            </select>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left whitespace-nowrap">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200 bg-slate-50/50">
                <tr>
                  <th className="py-3 px-2 font-semibold">Worker ID</th>
                  <th className="py-3 px-2 font-semibold">Name</th>
                  <th className="py-3 px-2 font-semibold">Platform</th>
                  <th className="py-3 px-2 font-semibold">Zone</th>
                  <th className="py-3 px-2 font-semibold">Tier</th>
                  <th className="py-3 px-2 font-semibold">KYC</th>
                  <th className="py-3 px-2 font-semibold">Claims</th>
                  <th className="py-3 px-2 font-semibold">Joined</th>
                  <th className="py-3 px-2 font-semibold">Status</th>
                  <th className="py-3 px-2 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">W-4821</td>
                  <td className="py-3 px-2 font-medium">Ravi Kumar</td>
                  <td className="py-3 px-2 text-slate-600">Swiggy</td>
                  <td className="py-3 px-2 text-slate-600">Koramangala</td>
                  <td className="py-3 px-2"><Badge variant="gray">Silver</Badge></td>
                  <td className="py-3 px-2"><Badge variant="green">Verified</Badge></td>
                  <td className="py-3 px-2 font-mono">4</td>
                  <td className="py-3 px-2 text-slate-500">Jan 2025</td>
                  <td className="py-3 px-2"><Badge variant="green">Active</Badge></td>
                  <td className="py-3 px-2"><Button variant="outline" size="sm" className="h-6 text-[10px] px-2">View</Button></td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-3 px-2 font-mono font-medium">W-3302</td>
                  <td className="py-3 px-2 font-medium">Meena Devi</td>
                  <td className="py-3 px-2 text-slate-600">Zomato</td>
                  <td className="py-3 px-2 text-slate-600">HSR Layout</td>
                  <td className="py-3 px-2"><Badge variant="amber">Gold</Badge></td>
                  <td className="py-3 px-2"><Badge variant="green">Verified</Badge></td>
                  <td className="py-3 px-2 font-mono">7</td>
                  <td className="py-3 px-2 text-slate-500">Nov 2024</td>
                  <td className="py-3 px-2"><Badge variant="green">Active</Badge></td>
                  <td className="py-3 px-2"><Button variant="outline" size="sm" className="h-6 text-[10px] px-2">View</Button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
