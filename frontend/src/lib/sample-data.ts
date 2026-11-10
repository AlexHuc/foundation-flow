// ILLUSTRATIVE sample data. Shown only until the PostgreSQL `landing` schema is connected.
// Every surface rendering these values must carry the "Illustrative" label.

export type AnnualRow = {
  fiscalYear: number;
  periodEnd: string;
  revenue: number | null;
  grossProfit: number | null;
  operatingIncome: number | null;
  netIncome: number | null;
  eps: number | null;
  operatingCashFlow: number | null;
  capex: number | null;
};

export type Company = {
  ticker: string;
  name: string;
  exchange: string;
  sector: string;
  industry: string;
  currency: string;
  price: number | null;
  priceDate: string;
  marketCap: number | null;
  pe: number | null;
  totalDebt: number | null;
  totalEquity: number | null;
  annual: AnnualRow[];
  prices: { date: string; close: number }[];
};

function priceSeries(start: number, drift: number, seed: number) {
  const out: { date: string; close: number }[] = [];
  let p = start;
  let s = seed;
  for (let m = 0; m < 36; m++) {
    s = (s * 9301 + 49297) % 233280;
    p = p * (1 + drift + (s / 233280 - 0.5) * 0.14);
    const d = new Date(Date.UTC(2023, 10 + m, 1));
    out.push({ date: d.toISOString().slice(0, 10), close: Math.round(p * 100) / 100 });
  }
  return out;
}

const B = 1_000_000_000;
const M = 1_000_000;

export const COMPANIES: Company[] = [
  {
    ticker: "CRDO", name: "Credo Technology Group", exchange: "NASDAQ", sector: "Technology",
    industry: "Semiconductors", currency: "USD", price: 128.4, priceDate: "2026-11-06",
    marketCap: 21.8 * B, pe: 94.1, totalDebt: 0.02 * B, totalEquity: 1.1 * B,
    annual: [
      { fiscalYear: 2022, periodEnd: "2022-04-30", revenue: 106 * M, grossProfit: 63 * M, operatingIncome: -11 * M, netIncome: -12 * M, eps: -0.09, operatingCashFlow: 5 * M, capex: 22 * M },
      { fiscalYear: 2023, periodEnd: "2023-04-29", revenue: 184 * M, grossProfit: 106 * M, operatingIncome: -15 * M, netIncome: -17 * M, eps: -0.11, operatingCashFlow: 21 * M, capex: 36 * M },
      { fiscalYear: 2024, periodEnd: "2024-04-27", revenue: 193 * M, grossProfit: 120 * M, operatingIncome: -37 * M, netIncome: -28 * M, eps: -0.18, operatingCashFlow: 32 * M, capex: 18 * M },
      { fiscalYear: 2025, periodEnd: "2025-05-03", revenue: 437 * M, grossProfit: 279 * M, operatingIncome: 41 * M, netIncome: 52 * M, eps: 0.3, operatingCashFlow: 96 * M, capex: 33 * M },
    ],
    prices: priceSeries(30, 0.045, 7),
  },
  {
    ticker: "MSFT", name: "Microsoft Corporation", exchange: "NASDAQ", sector: "Technology",
    industry: "Software — Infrastructure", currency: "USD", price: 512.3, priceDate: "2026-11-06",
    marketCap: 3810 * B, pe: 37.8, totalDebt: 60 * B, totalEquity: 343 * B,
    annual: [
      { fiscalYear: 2022, periodEnd: "2022-06-30", revenue: 198.3 * B, grossProfit: 135.6 * B, operatingIncome: 83.4 * B, netIncome: 72.7 * B, eps: 9.65, operatingCashFlow: 89 * B, capex: 23.9 * B },
      { fiscalYear: 2023, periodEnd: "2023-06-30", revenue: 211.9 * B, grossProfit: 146.1 * B, operatingIncome: 88.5 * B, netIncome: 72.4 * B, eps: 9.68, operatingCashFlow: 87.6 * B, capex: 28.1 * B },
      { fiscalYear: 2024, periodEnd: "2024-06-30", revenue: 245.1 * B, grossProfit: 171 * B, operatingIncome: 109.4 * B, netIncome: 88.1 * B, eps: 11.8, operatingCashFlow: 118.5 * B, capex: 44.5 * B },
      { fiscalYear: 2025, periodEnd: "2025-06-30", revenue: 281.7 * B, grossProfit: 193.9 * B, operatingIncome: 128.5 * B, netIncome: 101.8 * B, eps: 13.64, operatingCashFlow: 136.2 * B, capex: 64.6 * B },
    ],
    prices: priceSeries(360, 0.01, 3),
  },
  {
    ticker: "NVDA", name: "NVIDIA Corporation", exchange: "NASDAQ", sector: "Technology",
    industry: "Semiconductors", currency: "USD", price: 188.2, priceDate: "2026-11-06",
    marketCap: 4580 * B, pe: 52.6, totalDebt: 10.3 * B, totalEquity: 79.3 * B,
    annual: [
      { fiscalYear: 2023, periodEnd: "2023-01-29", revenue: 27 * B, grossProfit: 15.4 * B, operatingIncome: 4.2 * B, netIncome: 4.4 * B, eps: 0.17, operatingCashFlow: 5.6 * B, capex: 1.8 * B },
      { fiscalYear: 2024, periodEnd: "2024-01-28", revenue: 60.9 * B, grossProfit: 44.3 * B, operatingIncome: 33 * B, netIncome: 29.8 * B, eps: 1.19, operatingCashFlow: 28.1 * B, capex: 1.1 * B },
      { fiscalYear: 2025, periodEnd: "2025-01-26", revenue: 130.5 * B, grossProfit: 97.9 * B, operatingIncome: 81.5 * B, netIncome: 72.9 * B, eps: 2.94, operatingCashFlow: 64.1 * B, capex: 3.2 * B },
    ],
    prices: priceSeries(45, 0.035, 11),
  },
  {
    ticker: "AAPL", name: "Apple Inc.", exchange: "NASDAQ", sector: "Technology",
    industry: "Consumer Electronics", currency: "USD", price: 268.9, priceDate: "2026-11-06",
    marketCap: 3990 * B, pe: 40.2, totalDebt: 101.7 * B, totalEquity: 73.7 * B,
    annual: [
      { fiscalYear: 2022, periodEnd: "2022-09-24", revenue: 394.3 * B, grossProfit: 170.8 * B, operatingIncome: 119.4 * B, netIncome: 99.8 * B, eps: 6.11, operatingCashFlow: 122.2 * B, capex: 10.7 * B },
      { fiscalYear: 2023, periodEnd: "2023-09-30", revenue: 383.3 * B, grossProfit: 169.1 * B, operatingIncome: 114.3 * B, netIncome: 97 * B, eps: 6.13, operatingCashFlow: 110.5 * B, capex: 11 * B },
      { fiscalYear: 2024, periodEnd: "2024-09-28", revenue: 391 * B, grossProfit: 180.7 * B, operatingIncome: 123.2 * B, netIncome: 93.7 * B, eps: 6.08, operatingCashFlow: 118.3 * B, capex: 9.4 * B },
      { fiscalYear: 2025, periodEnd: "2025-09-27", revenue: 416.2 * B, grossProfit: 195.2 * B, operatingIncome: 133.1 * B, netIncome: 112 * B, eps: 7.46, operatingCashFlow: 111.5 * B, capex: 12.7 * B },
    ],
    prices: priceSeries(190, 0.009, 5),
  },
];

export function getCompany(ticker: string) {
  return COMPANIES.find((c) => c.ticker === ticker.toUpperCase());
}
