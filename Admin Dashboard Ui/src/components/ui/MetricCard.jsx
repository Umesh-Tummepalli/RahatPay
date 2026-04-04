import React from "react";
import { motion } from "framer-motion";
import { ArrowUpRight, ArrowDownRight, AlertCircle } from "lucide-react";
import { cn } from "../../lib/utils";
import { Card, CardContent } from "./Card";

export function MetricCard({ title, value, subtext, trend, className }) {
  return (
    <motion.div
      whileHover={{ y: -2 }}
      transition={{ type: "spring", stiffness: 300 }}
    >
      <Card className={cn("overflow-hidden border border-slate-200 shadow-sm", className)}>
        <CardContent className="p-4">
          <p className="text-xs font-medium text-slate-500 mb-1">{title}</p>
          <div className="flex items-baseline mb-1">
            <h2 className="text-2xl font-semibold tracking-tight font-mono text-slate-800">
              {value}
            </h2>
          </div>
          <div className="flex items-center text-[11px] font-medium mt-1">
            {trend === "up" && (
              <span className="flex items-center text-(--color-success) font-medium bg-(--color-success)/10 px-1 rounded-sm mr-2">
                <ArrowUpRight className="w-3 h-3 mr-0.5" />
              </span>
            )}
            {trend === "down" && (
              <span className="flex items-center text-(--color-danger) font-medium bg-(--color-danger)/10 px-1 rounded-sm mr-2">
                <ArrowDownRight className="w-3 h-3 mr-0.5" />
              </span>
            )}
            {trend === "warn" && (
              <span className="flex items-center text-(--color-warning) font-medium bg-(--color-warning)/10 px-1 rounded-sm mr-2">
                <AlertCircle className="w-3 h-3 mr-0.5" />
              </span>
            )}
            <span
              className={cn(
                "text-slate-500",
                trend === "up" && "text-(--color-success)",
                trend === "down" && "text-(--color-danger)",
                trend === "warn" && "text-(--color-warning)"
              )}
            >
              {subtext}
            </span>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
