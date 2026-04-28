import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmt(n: number | undefined | null, decimals = 2): string {
  if (n == null || isNaN(n)) return "—";
  return n.toFixed(decimals);
}

export function fmtPct(n: number | undefined | null): string {
  if (n == null || isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

export function fmtK(n: number | undefined | null): string {
  if (n == null || isNaN(n)) return "—";
  if (Math.abs(n) >= 1000) return `$${(n / 1000).toFixed(1)}k`;
  return `$${n.toFixed(0)}`;
}

export function fmtTs(ts: number): string {
  return new Date(ts).toLocaleTimeString("en-US", { hour12: false });
}

export function roasColor(roas: number): string {
  if (roas >= 2.0) return "text-emerald-400";
  if (roas >= 1.2) return "text-amber-400";
  return "text-red-400";
}

export function deltaColor(v: number): string {
  if (v > 0) return "text-emerald-400";
  if (v < 0) return "text-red-400";
  return "text-zinc-400";
}
