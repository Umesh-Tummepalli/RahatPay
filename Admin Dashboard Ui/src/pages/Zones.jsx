import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";

export default function Zones() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Zone management
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Active zones" value="24" subtext="Bangalore" trend="none" />
          <MetricCard title="Over-capacity zones" value="2" subtext="Exceed worker cap" trend="down" />
          <MetricCard title="Avg workers/zone" value="520" subtext="vs 500 cap" trend="none" />
          <MetricCard title="Disabled zones" value="3" subtext="No coverage" trend="none" />
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Zone registry</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="pb-3 px-2 font-semibold">Zone</th>
                  <th className="pb-3 px-2 font-semibold">Workers registered</th>
                  <th className="pb-3 px-2 font-semibold">Cap</th>
                  <th className="pb-3 px-2 font-semibold w-40">Utilization</th>
                  <th className="pb-3 px-2 font-semibold">Status</th>
                  <th className="pb-3 px-2 font-semibold">Toggle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-2 font-medium">Koramangala</td>
                  <td className="py-4 px-2 font-mono">38</td>
                  <td className="py-4 px-2 font-mono text-slate-500">30</td>
                  <td className="py-4 px-2">
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                      <div className="h-full bg-[var(--color-danger)] rounded-full" style={{ width: "100%" }} />
                    </div>
                  </td>
                  <td className="py-4 px-2"><Badge variant="red">Over cap</Badge></td>
                  <td className="py-4 px-2">
                    <div className="w-8 h-4 bg-[var(--color-success)] rounded-full relative cursor-pointer">
                      <div className="absolute right-0.5 top-0.5 w-3 h-3 bg-white rounded-full shadow-sm" />
                    </div>
                  </td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-2 font-medium">Indiranagar</td>
                  <td className="py-4 px-2 font-mono">28</td>
                  <td className="py-4 px-2 font-mono text-slate-500">30</td>
                  <td className="py-4 px-2">
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                      <div className="h-full bg-[var(--color-warning)] rounded-full" style={{ width: "93%" }} />
                    </div>
                  </td>
                  <td className="py-4 px-2"><Badge variant="amber">Near cap</Badge></td>
                  <td className="py-4 px-2">
                    <div className="w-8 h-4 bg-[var(--color-success)] rounded-full relative cursor-pointer">
                      <div className="absolute right-0.5 top-0.5 w-3 h-3 bg-white rounded-full shadow-sm" />
                    </div>
                  </td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-2 font-medium">Marathahalli</td>
                  <td className="py-4 px-2 font-mono">22</td>
                  <td className="py-4 px-2 font-mono text-slate-500">30</td>
                  <td className="py-4 px-2">
                    <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden w-24">
                      <div className="h-full bg-[var(--color-success)] rounded-full" style={{ width: "73%" }} />
                    </div>
                  </td>
                  <td className="py-4 px-2"><Badge variant="green">Healthy</Badge></td>
                  <td className="py-4 px-2">
                    <div className="w-8 h-4 bg-[var(--color-success)] rounded-full relative cursor-pointer">
                      <div className="absolute right-0.5 top-0.5 w-3 h-3 bg-white rounded-full shadow-sm" />
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
