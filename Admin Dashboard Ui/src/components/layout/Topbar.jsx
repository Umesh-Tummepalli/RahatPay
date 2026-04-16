import React, { useState, useEffect, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { Download, RefreshCw, UserCircle, Menu } from "lucide-react";
import { Button } from "../ui/Button";
import { GlobalApiStatus } from "../ui/StatusComponents";
import * as api from "../../lib/api";

const ROUTE_NAMES = {
  "/":            "Platform Dashboard",
  "/workers":     "Worker Management",
  "/kyc":         "KYC / Onboarding",
  "/subscriptions": "Subscriptions",
  "/claims":      "Claims Queue",
  "/payouts":     "Payout History",
  "/fraud":       "Fraud Alerts",
  "/isolation":   "Isolation Forest",
  "/zones":       "Zone Management",
  "/actuarial":   "Actuarial Overview",
  "/predictive":  "Predictive Analytics",
  "/stress-test": "BCR Stress Test",
  "/platform":    "Platform Health",
  "/config":      "System Configuration",
};

export function Topbar({ toggleMobile }) {
  const { pathname } = useLocation();
  const pageTitle = ROUTE_NAMES[pathname] || "Dashboard";

  // ── Global API health ─────────────────────────────────────────────────────
  const [health, setHealth] = useState({ module1: null, module2: null, module3: null });
  const [lastChecked, setLastChecked] = useState(null);

  const checkHealth = useCallback(async () => {
    try {
      const status = await api.checkAllHealth();
      setHealth(status);
    } catch {
      setHealth({ module1: false, module2: false, module3: false });
    } finally {
      setLastChecked(new Date());
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const id = setInterval(checkHealth, 20_000);
    return () => clearInterval(id);
  }, [checkHealth]);

  return (
    <header className="h-[60px] border-b bg-[var(--bg-card)] flex items-center justify-between px-4 md:px-6 shrink-0 z-10">
      {/* ── Left: mobile toggle + page title ── */}
      <div className="flex items-center gap-3">
        <button
          onClick={toggleMobile}
          className="lg:hidden p-1.5 -ml-1 text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-sm font-semibold text-slate-800">{pageTitle}</h1>
          <div className="flex items-center text-[10px] md:text-[11px] text-slate-500 mt-0.5 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-(--color-success) shadow-[0_0_4px_var(--color-success)] mr-1.5 animate-pulse shrink-0" />
            <span className="truncate max-w-[120px] sm:max-w-none">
              RahatPay Phase 3 · Admin Console
            </span>
          </div>
        </div>
      </div>

      {/* ── Right: status pill + actions ── */}
      <div className="flex items-center gap-2 md:gap-3">

        {/* Global API status pill with Reconnect button + last-checked + tooltip */}
        <div className="hidden sm:block">
          <GlobalApiStatus
            module1={health.module1}
            module2={health.module2}
            module3={health.module3}
            lastChecked={lastChecked}
            onReconnect={checkHealth}
          />
        </div>

        <div className="hidden sm:block w-px h-5 bg-slate-200 mx-1" />

        <Button
          variant="outline"
          size="sm"
          className="hidden sm:flex h-8 shadow-none text-xs text-slate-600 border-slate-200"
        >
          <Download className="w-3.5 h-3.5 mr-2" />
          Export
        </Button>

        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 sm:w-auto sm:px-3 shadow-none text-slate-600 border-slate-200 shrink-0"
          onClick={() => window.location.reload()}
          aria-label="Refresh page"
          title="Reload page"
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
