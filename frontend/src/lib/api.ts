// API service layer for the Foundation Flow FastAPI backend.
//
// Two explicit modes:
//
//   Real-data mode — an API base URL is configured. Every read goes to the
//   FastAPI backend. If the backend is unreachable or returns an error, the
//   query fails and the UI shows a connection error. It NEVER falls back to
//   illustrative data.
//
//   Demo mode — no API base URL is configured. The UI renders the clearly
//   labeled illustrative sample data so the design can be explored without a
//   backend.
//
// URL resolution: the browser uses VITE_API_BASE_URL (build-time, must be a
// browser-reachable address such as http://localhost:8000). During SSR the
// frontend server runs inside Docker, where `localhost` is the frontend
// container itself, so server-side fetches use API_INTERNAL_URL (runtime env,
// e.g. http://backend:8000) when set.

import { queryOptions } from "@tanstack/react-query";
import { COMPANIES, getCompany, type AnnualRow, type Company } from "./sample-data";

const BROWSER_API_BASE = ((import.meta.env["VITE_API_BASE_URL"] as string | undefined) ?? "").replace(/\/$/, "");
const SERVER_API_BASE =
  typeof window === "undefined"
    ? ((typeof process !== "undefined" ? process.env["API_INTERNAL_URL"] : undefined) ?? "").replace(/\/$/, "")
    : "";

const API_BASE = SERVER_API_BASE || BROWSER_API_BASE;

/** True when a backend URL is configured and the app must serve real data only. */
export const REAL_DATA_MODE = API_BASE.length > 0;

export type DataSource = "api" | "illustrative";

export type CompanyResult = { company: Company; source: DataSource };
export type CompaniesResult = { companies: Company[]; source: DataSource };

/** The backend was configured but could not be reached or answered with an error. */
export class ApiConnectionError extends Error {
  constructor(
    message: string,
    public override cause?: unknown,
  ) {
    super(message);
    this.name = "ApiConnectionError";
  }
}

class ApiError extends Error {
  constructor(
    public status: number,
    path: string,
  ) {
    super(`API ${status} for ${path}`);
  }
}

async function fetchJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      signal: signal ?? null,
      headers: { accept: "application/json" },
    });
  } catch (err) {
    throw new ApiConnectionError(`Cannot reach the Foundation Flow API at ${API_BASE}`, err);
  }
  if (!res.ok) throw new ApiError(res.status, path);
  return (await res.json()) as T;
}

// ---- Backend row shapes (landing schema; every column may be null) ----

type ApiProfile = {
  ticker: string;
  info: {
    market_cap: number | null;
    pe_ratio: number | null;
    raw_response: { longName?: string; shortName?: string; sector?: string; industry?: string } | null;
  } | null;
  fast_info: { last_price: number | null; currency: string | null; exchange: string | null; date: string } | null;
  last_bar: { date: string; close: number } | null;
};

type ApiIncomeRow = {
  date: string;
  total_revenue: number | null;
  gross_profit: number | null;
  operating_income: number | null;
  net_income: number | null;
  diluted_eps: number | null;
  basic_eps: number | null;
};

type ApiCashflowRow = {
  date: string;
  operating_cash_flow: number | null;
  capital_expenditure: number | null;
};

type ApiBalanceRow = {
  date: string;
  total_debt: number | null;
  stockholders_equity: number | null;
};

type ApiPriceRow = { date: string; close: number };

type ApiCompanyListEntry = { ticker: string };

/** Map backend rows onto the Company shape the UI already renders. Nulls stay null — nothing is fabricated. */
export function mapApiToCompany(
  ticker: string,
  profile: ApiProfile,
  income: ApiIncomeRow[],
  cashflow: ApiCashflowRow[],
  balance: ApiBalanceRow[],
  prices: ApiPriceRow[],
): Company {
  const raw = profile.info?.raw_response ?? null;
  const cashflowByDate = new Map(cashflow.map((r) => [r.date, r]));

  const annual: AnnualRow[] = income
    .slice()
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((r) => {
      const cf = cashflowByDate.get(r.date);
      return {
        fiscalYear: new Date(`${r.date}T00:00:00Z`).getUTCFullYear(),
        periodEnd: r.date,
        revenue: r.total_revenue,
        grossProfit: r.gross_profit,
        operatingIncome: r.operating_income,
        netIncome: r.net_income,
        eps: r.diluted_eps ?? r.basic_eps,
        operatingCashFlow: cf?.operating_cash_flow ?? null,
        capex: cf?.capital_expenditure != null ? Math.abs(cf.capital_expenditure) : null,
      };
    });

  const latestBalance = balance.slice().sort((a, b) => b.date.localeCompare(a.date))[0];

  return {
    ticker,
    name: raw?.longName ?? raw?.shortName ?? ticker,
    exchange: profile.fast_info?.exchange ?? "—",
    sector: raw?.sector ?? "—",
    industry: raw?.industry ?? "—",
    currency: profile.fast_info?.currency ?? "USD",
    price: profile.fast_info?.last_price ?? profile.last_bar?.close ?? null,
    priceDate: profile.fast_info?.date ?? profile.last_bar?.date ?? "—",
    marketCap: profile.info?.market_cap ?? null,
    pe: profile.info?.pe_ratio ?? null,
    totalDebt: latestBalance?.total_debt ?? null,
    totalEquity: latestBalance?.stockholders_equity ?? null,
    annual,
    prices: prices.map((p) => ({ date: p.date, close: p.close })),
  };
}

async function fetchCompanyFromApi(ticker: string, signal?: AbortSignal): Promise<Company | null> {
  const t = ticker.toUpperCase();
  let profile: ApiProfile;
  try {
    profile = await fetchJson<ApiProfile>(`/api/companies/${t}`, signal);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
  // Secondary datasets are best-effort: a missing table must not hide the company.
  const optional = <R>(p: Promise<R[]>): Promise<R[]> =>
    p.catch((err) => {
      if (err instanceof ApiConnectionError) throw err;
      return [] as R[];
    });
  const [income, cashflow, balance, prices] = await Promise.all([
    optional(fetchJson<ApiIncomeRow[]>(`/api/companies/${t}/financials/income?period=annual`, signal)),
    optional(fetchJson<ApiCashflowRow[]>(`/api/companies/${t}/financials/cashflow?period=annual`, signal)),
    optional(fetchJson<ApiBalanceRow[]>(`/api/companies/${t}/financials/balance?period=annual`, signal)),
    optional(fetchJson<ApiPriceRow[]>(`/api/companies/${t}/prices`, signal)),
  ]);
  return mapApiToCompany(t, profile, income, cashflow, balance, prices);
}

export async function getCompanyData(ticker: string): Promise<CompanyResult | null> {
  if (REAL_DATA_MODE) {
    // Real-data mode: surface failures — never substitute illustrative data.
    const company = await fetchCompanyFromApi(ticker);
    return company ? { company, source: "api" } : null;
  }
  const sample = getCompany(ticker);
  return sample ? { company: sample, source: "illustrative" } : null;
}

export async function listCompaniesData(): Promise<CompaniesResult> {
  if (REAL_DATA_MODE) {
    const entries = await fetchJson<ApiCompanyListEntry[]>("/api/companies");
    const companies = (await Promise.all(entries.map((e) => fetchCompanyFromApi(e.ticker).catch(() => null)))).filter(
      (c): c is Company => c != null,
    );
    // An empty database is a valid empty state, not a reason to fabricate data.
    return { companies, source: "api" };
  }
  return { companies: COMPANIES, source: "illustrative" };
}

export const companiesQueryOptions = queryOptions({
  queryKey: ["ff", "companies"],
  queryFn: listCompaniesData,
  staleTime: 60_000,
});

export const companyQueryOptions = (ticker: string) =>
  queryOptions({
    queryKey: ["ff", "company", ticker.toUpperCase()],
    queryFn: () => getCompanyData(ticker),
    staleTime: 60_000,
  });
