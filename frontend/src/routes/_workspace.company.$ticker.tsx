import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute, notFound, useRouter } from "@tanstack/react-router";
import { Star } from "lucide-react";
import { useState } from "react";
import { FinancialBarChart, PriceChart } from "@/components/ff/charts";
import { ConnectionErrorState, DataLabel, EmptyDataState, MetricCard, Panel } from "@/components/ff/primitives";
import { companyQueryOptions } from "@/lib/api";
import { fmtMoney, fmtPct, freeCashFlow, growth, ratio } from "@/lib/metrics";
import { cn } from "@/lib/utils";

function CompanyError({ reset }: { reset: () => void }) {
  const router = useRouter();
  return (
    <div className="mx-auto max-w-7xl">
      <ConnectionErrorState
        onRetry={() => {
          void router.invalidate();
          reset();
        }}
      />
    </div>
  );
}

export const Route = createFileRoute("/_workspace/company/$ticker")({
  loader: async ({ params, context }) => {
    const data = await context.queryClient.ensureQueryData(companyQueryOptions(params.ticker));
    if (!data) throw notFound();
    return { ticker: data.company.ticker, name: data.company.name };
  },
  errorComponent: CompanyError,
  head: ({ loaderData }) => {
    const t = loaderData ? `${loaderData.name} (${loaderData.ticker}) — Foundation Flow` : "Company unavailable — Foundation Flow";
    const d = loaderData ? `Fundamental research on ${loaderData.name}: financials, margins, cash flow and valuation.` : "Company not found.";
    return { meta: [{ title: t }, { name: "description", content: d }, { property: "og:title", content: t }, { property: "og:description", content: d }] };
  },
  notFoundComponent: () => <EmptyDataState title="Ticker not found" body="This ticker isn't available in the current dataset." />,
  component: CompanyPage,
});

const TABS = ["Overview", "Financial Statements", "Profitability", "Growth", "Balance Sheet", "Cash Flow", "Valuation", "Analyst Estimates", "Analyst Recommendations", "Ownership", "Insider Activity", "Options", "SEC Filings", "Earnings & Calendar"];

function CompanyPage() {
  const { ticker } = Route.useLoaderData();
  const { data } = useSuspenseQuery(companyQueryOptions(ticker));
  const c = data!.company;
  const srcLabel = data!.source === "api" ? "Reported" : "Illustrative";
  const [tab, setTab] = useState("Overview");
  const [watched, setWatched] = useState(false);
  const last = c.annual.at(-1), prev = c.annual.at(-2);
  const chartData = c.annual.map((r) => ({ period: `FY${r.fiscalYear}`, revenue: r.revenue, netIncome: r.netIncome, fcf: freeCashFlow(r) }));

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <header className="ambient diagonal-lines relative overflow-hidden rounded-xl border bg-surface p-6 md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="flex h-16 w-16 -skew-x-6 items-center justify-center rounded-lg bg-primary text-lg font-black text-primary-foreground">{c.ticker.slice(0, 2)}</div>
            <div>
              <div className="eyebrow">{c.exchange} · {c.sector} · {c.industry}</div>
              <h1 className="mt-1 text-3xl font-bold tracking-tight md:text-4xl">{c.name}</h1>
              <div className="mt-1 text-sm font-bold text-chart">{c.ticker}</div>
            </div>
          </div>
          <div className="text-right">
            <div className="num text-4xl font-bold">{c.price != null ? `$${c.price.toFixed(2)}` : "—"} <span className="text-sm text-muted-foreground">{c.currency}</span></div>
            <div className="mt-1 flex items-center justify-end gap-2 text-xs text-muted-foreground">
              Observed <span className="num">{c.priceDate}</span> <DataLabel kind={srcLabel} />
            </div>
            <div className="num mt-1 text-sm text-muted-foreground">Mkt cap {fmtMoney(c.marketCap)}</div>
            <button
              onClick={() => setWatched((w) => !w)}
              className={cn("mt-4 inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold transition-shadow", watched ? "border border-primary text-foreground" : "bg-primary text-primary-foreground hover:glow-primary")}
            >
              <Star className={cn("h-4 w-4", watched && "fill-current")} /> {watched ? "On watchlist" : "Add to Watchlist"}
            </button>
          </div>
        </div>
      </header>

      <div className="flex gap-1 overflow-x-auto border-b">
        {TABS.map((t) => (
          <button key={t} onClick={() => setTab(t)} className={cn("whitespace-nowrap border-b-2 px-3 py-2.5 text-[13px] font-medium transition-colors", tab === t ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground")}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Overview" ? (
        <>
          {last ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard label="Revenue" value={fmtMoney(last.revenue)} date={`FY${last.fiscalYear} · Reported`} change={growth(last.revenue, prev?.revenue)} label2={srcLabel} />
            <MetricCard label="Net income" value={fmtMoney(last.netIncome)} date={`FY${last.fiscalYear} · Reported`} change={growth(last.netIncome, prev?.netIncome)} label2={srcLabel} />
            <MetricCard label="EPS" value={last.eps != null ? `$${last.eps.toFixed(2)}` : "—"} date={`FY${last.fiscalYear} · Diluted`} label2={srcLabel} />
            <MetricCard label="Free cash flow" value={fmtMoney(freeCashFlow(last))} date={`FY${last.fiscalYear}`} label2="Calculated" hint="Operating cash flow − capex" />
            <MetricCard label="Gross margin" value={fmtPct(ratio(last.grossProfit, last.revenue))} date={`FY${last.fiscalYear}`} label2="Calculated" />
            <MetricCard label="Operating margin" value={fmtPct(ratio(last.operatingIncome, last.revenue))} date={`FY${last.fiscalYear}`} label2="Calculated" />
            <MetricCard label="Debt / Equity" value={ratio(c.totalDebt, c.totalEquity)?.toFixed(2) ?? "—"} unit="x" date="Latest balance sheet" label2="Calculated" />
            <MetricCard label="P/E ratio" value={c.pe?.toFixed(1) ?? "—"} unit="x" date={`Observed ${c.priceDate}`} label2={srcLabel} />
          </div>
          ) : (
            <EmptyDataState title="No financial statements yet" body="The pipelines haven't ingested income statement data for this ticker." />
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel eyebrow="Annual · Reported" title="Revenue"><FinancialBarChart data={chartData} dataKey="revenue" label="Revenue" /></Panel>
            <Panel eyebrow="Annual · Calculated" title="Free cash flow"><FinancialBarChart data={chartData} dataKey="fcf" label="FCF" /></Panel>
          </div>
          <Panel eyebrow="Daily close" title="Price history" actions={<DataLabel kind={srcLabel} />}><PriceChart data={c.prices} /></Panel>

          <Panel eyebrow="Annual" title="Income statement summary" actions={<DataLabel kind="Reported" />}>
            <div className="overflow-x-auto">
              <table className="num w-full text-sm">
                <thead>
                  <tr className="eyebrow border-b text-left"><th className="pb-3">Line item</th>{c.annual.map((r) => <th key={r.fiscalYear} className="pb-3 text-right">FY{r.fiscalYear}<div className="text-[10px] font-normal normal-case tracking-normal">{r.periodEnd}</div></th>)}</tr>
                </thead>
                <tbody>
                  {([["Revenue", "revenue"], ["Gross profit", "grossProfit"], ["Operating income", "operatingIncome"], ["Net income", "netIncome"], ["Operating cash flow", "operatingCashFlow"]] as const).map(([lbl, k]) => (
                    <tr key={k} className="border-b last:border-0">
                      <td className="py-2.5 text-muted-foreground">{lbl}</td>
                      {c.annual.map((r) => <td key={r.fiscalYear} className={cn("py-2.5 text-right", r[k] != null && r[k]! < 0 && "text-negative")}>{fmtMoney(r[k])}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      ) : (
        <EmptyDataState title={`${tab} — coming in the next phase`} body="This section will read from your PostgreSQL landing schema once the connection is configured." />
      )}
    </div>
  );
}
