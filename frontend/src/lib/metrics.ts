import type { AnnualRow } from "./sample-data";

/** Returns null when inputs are missing or the denominator is zero/negative-meaningless. */
export function ratio(n: number | null | undefined, d: number | null | undefined): number | null {
  if (n == null || d == null || d === 0) return null;
  return n / d;
}

/** YoY growth; null when the prior value is missing or non-positive (growth undefined). */
export function growth(curr: number | null | undefined, prev: number | null | undefined): number | null {
  if (curr == null || prev == null || prev <= 0) return null;
  return curr / prev - 1;
}

/** Operating cash flow − capex; null when either input is missing. */
export function freeCashFlow(r: AnnualRow): number | null {
  if (r.operatingCashFlow == null || r.capex == null) return null;
  return r.operatingCashFlow - Math.abs(r.capex);
}

export function fmtMoney(v: number | null, currency = "USD") {
  if (v == null) return "—";
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  const sym = currency === "USD" ? "$" : "";
  if (abs >= 1e12) return `${sign}${sym}${(abs / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${sign}${sym}${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}${sym}${(abs / 1e6).toFixed(1)}M`;
  return `${sign}${sym}${abs.toLocaleString("en-US")}`;
}

export function fmtPct(v: number | null, digits = 1) {
  if (v == null) return "—";
  return `${v >= 0 ? "" : "-"}${Math.abs(v * 100).toFixed(digits)}%`;
}
