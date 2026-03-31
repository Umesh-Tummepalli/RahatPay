import React from "react";
import { cn } from "../../lib/utils";

export function Badge({ children, variant = "gray", className, ...props }) {
  const variants = {
    green: "bg-green-100 text-green-700 border-green-200",
    amber: "bg-amber-100 text-amber-700 border-amber-200",
    red: "bg-red-100 text-red-700 border-red-200",
    blue: "bg-blue-100 text-blue-700 border-blue-200",
    purple: "bg-purple-100 text-purple-700 border-purple-200",
    gray: "bg-slate-100 text-slate-700 border-slate-200",
    primary: "bg-[#4a6850]/10 text-[#4a6850] border-[#4a6850]/20",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium border",
        variants[variant] || variants.gray,
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
