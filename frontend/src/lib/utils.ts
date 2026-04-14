import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export const cn = (...i: ClassValue[]) => twMerge(clsx(i));

export const brl = (v: number | string | null | undefined) => {
  if (v == null) return "—";
  const n = typeof v === "string" ? parseFloat(v) : v;
  return isNaN(n) ? "—" : n.toLocaleString("pt-BR", { minimumFractionDigits: 2 });
};

export const fmtDate = (s: string) => {
  try { return new Date(s).toLocaleString("pt-BR"); } catch { return s; }
};

export function getPayload(): Record<string, string> | null {
  const t = localStorage.getItem("access");
  if (!t) return null;
  try { return JSON.parse(atob(t.split(".")[1])); } catch { return null; }
}

export const isAdmin = () => getPayload()?.role === "admin";
