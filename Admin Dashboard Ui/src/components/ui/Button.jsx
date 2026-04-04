import React from "react";
import { cn } from "../../lib/utils";

export function Button({ 
  children, 
  variant = "default", 
  size = "default", 
  className, 
  ...props 
}) {
  const baseStyles = "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";
  
  const variants = {
    default: "bg-(--color-primary) text-white hover:bg-(--color-primary)/90 shadow-sm",
    destructive: "bg-(--color-danger) text-white hover:bg-(--color-danger)/90 shadow-sm",
    outline: "border border-slate-200 bg-transparent hover:bg-slate-100 text-slate-700",
    secondary: "bg-(--color-brand-olive) text-white hover:bg-(--color-brand-olive)/90 shadow-sm",
    ghost: "hover:bg-slate-100 hover:text-slate-900",
    link: "underline-offset-4 hover:underline text-slate-900",
  };

  const sizes = {
    default: "h-9 py-2 px-4 text-sm",
    sm: "h-7 px-3 text-xs",
    lg: "h-11 px-8 rounded-md",
    icon: "h-9 w-9",
  };

  return (
    <button
      className={cn(baseStyles, variants[variant], sizes[size], className)}
      {...props}
    >
      {children}
    </button>
  );
}
