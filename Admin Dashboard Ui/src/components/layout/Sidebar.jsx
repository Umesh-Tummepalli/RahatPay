import React from "react";
import { NavLink } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Users,
  UserCheck,
  CreditCard,
  FileText,
  Banknote,
  ShieldAlert,
  Network,
  Map,
  Calculator,
  Server,
  Settings,
  X,
} from "lucide-react";
import { cn } from "../../lib/utils";

const NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ id: "dashboard", path: "/", icon: LayoutDashboard, label: "Dashboard" }],
  },
  {
    label: "Workers",
    items: [
      { id: "workers", path: "/workers", icon: Users, label: "Worker Management" },
      { id: "kyc", path: "/kyc", icon: UserCheck, label: "KYC / Onboarding" },
      { id: "subscriptions", path: "/subscriptions", icon: CreditCard, label: "Subscriptions" },
    ],
  },
  {
    label: "Claims",
    items: [
      { id: "claims", path: "/claims", icon: FileText, label: "Claims Queue" },
      { id: "payouts", path: "/payouts", icon: Banknote, label: "Payout History" },
    ],
  },
  {
    label: "Fraud",
    items: [
      { id: "fraud", path: "/fraud", icon: ShieldAlert, label: "Fraud Alerts", badge: "3" },
      { id: "isolation", path: "/isolation", icon: Network, label: "Isolation Forest" },
    ],
  },
  {
    label: "Coverage",
    items: [
      { id: "zones", path: "/zones", icon: Map, label: "Zone Management" },
      { id: "actuarial", path: "/actuarial", icon: Calculator, label: "Actuarial Overview" },
    ],
  },
  {
    label: "System",
    items: [
      { id: "platform", path: "/platform", icon: Server, label: "Platform Health" },
      { id: "config", path: "/config", icon: Settings, label: "Config" },
    ],
  },
];

export function Sidebar({ isMobileOpen, closeMobile }) {
  return (
    <>
      <AnimatePresence>
        {isMobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={closeMobile}
            className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-sm lg:hidden"
          />
        )}
      </AnimatePresence>

      <aside
        className={cn(
          "w-[var(--sidebar-width)] min-w-[var(--sidebar-width)] bg-[var(--bg-card)] border-r flex flex-col h-screen font-sans fixed lg:static inset-y-0 left-0 z-50 transition-transform duration-300 ease-in-out lg:translate-x-0",
          isMobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
        )}
      >
        <div className="p-6 border-b flex items-start justify-between pb-5">
          <div className="flex flex-col">
            <div className="w-full flex items-center mt-1 mb-2">
              <img src="/logo.png" alt="RahatPay Logo" className="h-10 md:h-14 w-auto object-contain drop-shadow-sm" />
            </div>
            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold ml-1">
              Admin Console
            </div>
          </div>
          <button onClick={closeMobile} className="lg:hidden p-1 text-slate-500 hover:text-slate-800 rounded-md hover:bg-slate-100">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
          {NAV_GROUPS.map((group, i) => (
            <div key={i}>
              <p className="px-3 text-[10px] font-bold tracking-wider text-slate-400 uppercase mb-2">
                {group.label}
              </p>
              <nav className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors relative group",
                        isActive
                          ? "text-[var(--color-primary)] bg-[var(--color-primary)]/10 font-medium"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <motion.div
                            layoutId="sidebar-active"
                            className="absolute left-0 w-1 h-5 bg-[var(--color-primary)] rounded-r-md"
                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                          />
                        )}
                        <item.icon
                          className={cn(
                            "w-4 h-4 transition-colors",
                            isActive ? "text-[var(--color-primary)]" : "text-slate-400 group-hover:text-slate-600"
                          )}
                        />
                        <span className="truncate">{item.label}</span>
                        {item.badge && (
                          <span className="ml-auto bg-[var(--color-danger)]/10 text-[var(--color-danger)] text-[10px] px-2 py-0.5 rounded-full font-mono font-medium shrink-0">
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </nav>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
