import React from "react";
import { useLocation } from "react-router-dom";
import { Download, RefreshCw, UserCircle, Menu } from "lucide-react";
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

export function Topbar({ toggleMobile }) {
  const { pathname } = useLocation();
  const pageTitle = ROUTE_NAMES[pathname] || "Dashboard";

  return (
    <header className="h-[60px] border-b bg-[var(--bg-card)] flex items-center justify-between px-4 md:px-6 shrink-0 z-10">
      <div className="flex items-center gap-3">
        <button 
          onClick={toggleMobile} 
          className="lg:hidden p-1.5 -ml-1 text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
          aria-label="Open template menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-sm font-semibold text-slate-800">{pageTitle}</h1>
          <div className="flex items-center text-[10px] md:text-[11px] text-slate-500 mt-0.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-(--color-success) shadow-[0_0_4px_var(--color-success)] mr-1.5 animate-pulse shrink-0" />
            <span className="truncate max-w-[120px] sm:max-w-none">Live · Last refresh 2 min ago</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 md:gap-3">
        <Button variant="outline" size="sm" className="hidden sm:flex h-8 shadow-none text-xs text-slate-600 border-slate-200">
          <Download className="w-3.5 h-3.5 mr-2" />
          Export
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 sm:w-auto sm:px-3 shadow-none text-slate-600 border-slate-200 shrink-0"
          onClick={() => window.location.reload()}
          aria-label="Refresh"
        >
          <RefreshCw className="w-3.5 h-3.5 sm:mr-2" />
          <span className="hidden sm:inline text-xs">Refresh</span>
        </Button>
        
        <div className="hidden sm:block w-px h-5 bg-slate-200 mx-1" />
        
        <div className="flex items-center gap-2 text-xs font-medium text-slate-600 shrink-0 ml-1">
          <UserCircle className="w-6 h-6 text-(--color-primary)" />
          <span className="hidden md:inline">ops@rahatpay.in</span>
        </div>
      </div>
    </header>
  );
}
