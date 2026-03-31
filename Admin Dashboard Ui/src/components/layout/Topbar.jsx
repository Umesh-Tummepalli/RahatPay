import React from "react";
import { useLocation } from "react-router-dom";
import { Download, RefreshCw, UserCircle } from "lucide-react";
import { Button } from "../ui/Button";

const ROUTE_NAMES = {
  "/": "Platform Dashboard",
  "/workers": "Worker Management",
  "/kyc": "KYC / Onboarding",
  "/subscriptions": "Subscriptions",
  "/claims": "Claims Queue",
  "/payouts": "Payout History",
  "/fraud": "Fraud Alerts",
  "/isolation": "Isolation Forest",
  "/zones": "Zone Management",
  "/actuarial": "Actuarial Overview",
  "/platform": "Platform Health",
  "/config": "System Configuration",
};

export function Topbar() {
  const { pathname } = useLocation();
  const pageTitle = ROUTE_NAMES[pathname] || "Dashboard";

  return (
    <header className="h-[60px] border-b bg-[var(--bg-card)] flex items-center justify-between px-6 shrink-0">
      <div>
        <h1 className="text-sm font-semibold text-slate-800">{pageTitle}</h1>
        <div className="flex items-center text-[11px] text-slate-500 mt-0.5 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] shadow-[0_0_4px_var(--color-success)] mr-1.5 animate-pulse" />
          Live · Last refresh 2 min ago · Apr 1, 2026
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button variant="outline" size="sm" className="h-8 shadow-none text-xs text-slate-600 border-slate-200">
          <Download className="w-3.5 h-3.5 mr-2" />
          Export
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="h-8 shadow-none text-xs text-slate-600 border-slate-200"
          onClick={() => window.location.reload()}
        >
          <RefreshCw className="w-3.5 h-3.5 mr-2" />
          Refresh
        </Button>
        
        <div className="w-px h-5 bg-slate-200 mx-1" />
        
        <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
          <UserCircle className="w-6 h-6 text-slate-400" />
          <span>ops@rahatpay.in</span>
        </div>
      </div>
    </header>
  );
}
