import React from "react";
import { MetricCard } from "../components/ui/MetricCard";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export default function Isolation() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Isolation Forest — nightly batch results
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard title="Last run" value="2:00 AM" subtext="Apr 1, 2026" trend="none" />
          <MetricCard title="Workers scanned" value="12,481" subtext="Full dataset" trend="none" />
          <MetricCard title="Anomalies flagged" value="27" subtext="0.22% anomaly rate" trend="warn" />
          <MetricCard title="Next run" value="2:00 AM" subtext="Apr 2, 2026" trend="none" />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Anomaly scores — flagged workers</CardTitle>
          <span className="text-xs text-slate-400">Score closer to 1.0 = more anomalous</span>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[10px] uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="pb-3 px-2 font-semibold">Worker ID</th>
                  <th className="pb-3 px-2 font-semibold w-64">Anomaly score</th>
                  <th className="pb-3 px-2 font-semibold">Key signals</th>
                  <th className="pb-3 px-2 font-semibold">Zone</th>
                  <th className="pb-3 px-2 font-semibold">Status</th>
                  <th className="pb-3 px-2 font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-2 font-mono font-medium">W-6641</td>
                  <td className="py-4 px-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] w-8">0.91</span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full">
                        <div className="h-full bg-(--color-danger) rounded-full" style={{ width: "91%" }} />
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-2 text-slate-500">Filing freq, zone mismatch</td>
                  <td className="py-4 px-2 text-slate-600">Marathahalli</td>
                  <td className="py-4 px-2"><Badge variant="red">Critical</Badge></td>
                  <td className="py-4 px-2"><Button size="sm" variant="destructive" className="h-6 text-[10px] px-3">Block</Button></td>
                </tr>
                <tr className="hover:bg-slate-50 transition-colors">
                  <td className="py-4 px-2 font-mono font-medium">W-5512</td>
                  <td className="py-4 px-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[10px] w-8">0.85</span>
                      <div className="flex-1 h-1.5 bg-slate-100 rounded-full">
                        <div className="h-full bg-(--color-danger) rounded-full" style={{ width: "85%" }} />
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-2 text-slate-500">Referral depth, timing</td>
                  <td className="py-4 px-2 text-slate-600">HSR Layout</td>
                  <td className="py-4 px-2"><Badge variant="red">Critical</Badge></td>
                  <td className="py-4 px-2"><Button size="sm" variant="destructive" className="h-6 text-[10px] px-3">Block</Button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
