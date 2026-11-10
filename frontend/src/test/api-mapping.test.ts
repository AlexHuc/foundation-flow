import { describe, expect, it } from "vitest";
import { getCompanyData, mapApiToCompany } from "@/lib/api";

const profile = {
  ticker: "CRDO",
  info: { market_cap: 21_800_000_000, pe_ratio: 94.1, raw_response: { longName: "Credo Technology Group", sector: "Technology", industry: "Semiconductors" } },
  fast_info: { last_price: 128.4, currency: "USD", exchange: "NMS", date: "2026-11-04" },
  last_bar: { date: "2026-11-04", close: 128.4 },
};

describe("mapApiToCompany", () => {
  it("keeps missing values null instead of fabricating them", () => {
    const c = mapApiToCompany(
      "CRDO",
      profile,
      [{ date: "2025-05-03", total_revenue: 437_000_000, gross_profit: null, operating_income: null, net_income: 52_000_000, diluted_eps: null, basic_eps: null }],
      [], // no cash flow rows
      [], // no balance sheet rows
      [],
    );
    const row = c.annual[0]!;
    expect(row.revenue).toBe(437_000_000);
    expect(row.grossProfit).toBeNull();
    expect(row.operatingCashFlow).toBeNull();
    expect(row.capex).toBeNull();
    expect(row.eps).toBeNull();
    expect(c.totalDebt).toBeNull();
    expect(c.totalEquity).toBeNull();
  });

  it("stores capex as a positive magnitude and prefers diluted EPS over basic", () => {
    const c = mapApiToCompany(
      "CRDO",
      profile,
      [{ date: "2025-05-03", total_revenue: 1, gross_profit: 1, operating_income: 1, net_income: 1, diluted_eps: 0.3, basic_eps: 0.31 }],
      [{ date: "2025-05-03", operating_cash_flow: 96_000_000, capital_expenditure: -33_000_000 }],
      [{ date: "2025-05-03", total_debt: 20_000_000, stockholders_equity: 1_100_000_000 }],
      [],
    );
    expect(c.annual[0]!.capex).toBe(33_000_000);
    expect(c.annual[0]!.eps).toBe(0.3);
    expect(c.totalDebt).toBe(20_000_000);
  });

  it("uses the company name from the info snapshot and falls back to the ticker", () => {
    const named = mapApiToCompany("CRDO", profile, [], [], [], []);
    expect(named.name).toBe("Credo Technology Group");
    const unnamed = mapApiToCompany("XYZ", { ticker: "XYZ", info: null, fast_info: null, last_bar: null }, [], [], [], []);
    expect(unnamed.name).toBe("XYZ");
    expect(unnamed.price).toBeNull();
  });
});

describe("getCompanyData fallback", () => {
  it("returns illustrative sample data when no backend is configured", async () => {
    const result = await getCompanyData("CRDO");
    expect(result?.source).toBe("illustrative");
    expect(result?.company.ticker).toBe("CRDO");
  });

  it("returns null for a ticker nobody knows", async () => {
    expect(await getCompanyData("NOPE")).toBeNull();
  });
});
