import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card";
import { Button } from "../components/ui/Button";

export default function Config() {
  return (
    <div className="flex flex-col gap-6 w-full pb-10">
      <div>
        <h2 className="text-[10px] tracking-widest uppercase text-slate-500 font-bold mb-4">
          Configuration
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Subscription tiers — payout parameters</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Bronze — monthly premium (₹)</span>
                <input type="number" defaultValue="79" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Bronze — recovery %</span>
                <input type="number" defaultValue="50" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Silver — monthly premium (₹)</span>
                <input type="number" defaultValue="129" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Max payout per event (₹)</span>
                <input type="number" defaultValue="2000" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Batch job schedule</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Isolation Forest run time</span>
                <input type="time" defaultValue="02:00" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">API sync interval (min)</span>
                <input type="number" defaultValue="5" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Fraud detection thresholds</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Max workers per zone</span>
                <input type="number" defaultValue="30" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">Max referral chain depth</span>
                <input type="number" defaultValue="4" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-600">GPS zone tolerance (km)</span>
                <input type="number" defaultValue="2" className="bg-slate-50 border border-slate-200 rounded px-2 py-1 w-24 text-right font-mono outline-none focus:border-[var(--color-primary)]" />
              </div>
            </CardContent>
          </Card>

          <Button className="w-full">Save all changes</Button>
        </div>
      </div>
    </div>
  );
}
