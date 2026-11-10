import { useSuspenseQuery } from "@tanstack/react-query";
import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { PriceChart } from "@/components/ff/charts";
import { ConnectionErrorState, DataFreshnessIndicator, DataLabel, EmptyDataState, MetricCard, Panel } from "@/components/ff/primitives";
import { companiesQueryOptions } from "@/lib/api";
import { fmtMoney, fmtPct, freeCashFlow, growth, ratio } from "@/lib/metrics";

function DashboardError({ reset }: { reset: () => void }) {
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

export const Route = createFileRoute("/_workspace/dashboard")({
  loader: ({ context }) => context.queryClient.ensureQueryData(companiesQueryOptions),
  errorComponent: DashboardError,
  head: () => ({
    meta: [
      { title: "Research Workspace — Foundation Flow" },
      { name: "description", content: "Your fundamental investment research workspace: watchlist, KPIs and historical charts." },
      { property: "og:title", content: "Research Workspace — Foundation Flow" },
      { property: "og:description", content: "Analyze fundamentals. Understand businesses. Identify opportunities." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { data } = useSuspenseQuery(companiesQueryOptions);
  const companies = data.companies;
  const srcLabel = data.source === "api" ? "Reported" : "Illustrative";
  if (companies.length === 0) {
    return (
      <div className="mx-auto max-w-7xl">
        <EmptyDataState
          title="No companies in the database yet"
          body="The API is connected, but the landing schema has no ingested tickers. Run the Airflow pipelines to populate market data."
        />
      </div>
    );
  }
  const focus = companies[0]!;
  const last = focus.annual.at(-1);
  const prev = focus.annual.at(-2);
  return (
    <div className="mx-auto max-w-7xl space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="eyebrow mb-2">Workspace</div>
          <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Your Investment Research Workspace</h1>
          <p className="mt-2 text-muted-foreground">Analyze fundamentals. Understand businesses. Identify opportunities.</p>
        </div>
        <DataFreshnessIndicator date={focus.priceDate} kind={srcLabel} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label={`${focus.ticker} price`} value={focus.price != null ? `$${focus.price.toFixed(2)}` : "—"} date={`Observed ${focus.priceDate}`} hint="Latest stored closing price, not live." label2={srcLabel} />
        <MetricCard label="Market cap" value={fmtMoney(focus.marketCap)} date={`Observed ${focus.priceDate}`} label2={srcLabel} />
        <MetricCard label="Revenue" value={fmtMoney(last?.revenue ?? null)} date={last ? `FY${last.fiscalYear}` : ""} change={growth(last?.revenue, prev?.revenue)} label2={srcLabel} />
        <MetricCard label="Free cash flow" value={last ? fmtMoney(freeCashFlow(last)) : "—"} date={last ? `FY${last.fiscalYear}` : ""} hint="Operating cash flow minus capital expenditure." label2="Calculated" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel className="lg:col-span-2" eyebrow={focus.ticker} title="Price history" actions={<DataLabel kind={srcLabel} />}>
          <PriceChart data={focus.prices} />
        </Panel>
        <Panel title="Financial insights" eyebrow="Calculated from statements">
          <ul className="space-y-4 text-sm">
            {companies.map((c) => {
              const a = c.annual.at(-1), b = c.annual.at(-2);
              if (!a || !b) return null;
              const om = ratio(a.operatingIncome, a.revenue), pom = ratio(b.operatingIncome, b.revenue);
              const up = om != null && pom != null && om > pom;
              return (
                <li key={c.ticker} className="slash-accent pl-4">
                  <div className="font-semibold text-foreground">{c.ticker} · {up ? "Operating margin expansion" : "Operating margin contraction"}</div>
                  <div className="num text-muted-foreground">
                    {fmtPct(pom)} → <span className={up ? "text-positive" : "text-negative"}>{fmtPct(om)}</span> (FY{b.fiscalYear}–FY{a.fiscalYear})
                  </div>
                </li>
              );
            })}
          </ul>
        </Panel>
      </div>

      <Panel title="Watchlist" eyebrow="Summary" actions={<DataLabel kind={srcLabel} />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="eyebrow border-b text-left">
                <th className="pb-3 font-semibold">Company</th>
                <th className="pb-3 text-right font-semibold">Price</th>
                <th className="pb-3 text-right font-semibold">Market cap</th>
                <th className="pb-3 text-right font-semibold">Revenue (FY)</th>
                <th className="pb-3 text-right font-semibold">Rev. growth</th>
                <th className="pb-3 text-right font-semibold">Net margin</th>
              </tr>
            </thead>
            <tbody className="num">
              {companies.map((c) => {
                const a = c.annual.at(-1), b = c.annual.at(-2);
                const g = growth(a?.revenue, b?.revenue);
                return (
                  <tr key={c.ticker} className="border-b last:border-0 hover:bg-accent/40">
                    <td className="py-3">
                      <Link to="/company/$ticker" params={{ ticker: c.ticker }} className="flex items-center gap-3">
                        <span className="font-bold text-chart">{c.ticker}</span>
                        <span className="text-muted-foreground">{c.name}</span>
                      </Link>
                    </td>
                    <td className="py-3 text-right">{c.price != null ? `$${c.price.toFixed(2)}` : "—"}</td>
                    <td className="py-3 text-right">{fmtMoney(c.marketCap)}</td>
                    <td className="py-3 text-right">{fmtMoney(a?.revenue ?? null)} {a && <span className="text-muted-foreground">FY{a.fiscalYear}</span>}</td>
                    <td className={`py-3 text-right ${g == null ? "" : g >= 0 ? "text-positive" : "text-negative"}`}>{fmtPct(g)}</td>
                    <td className="py-3 text-right">{fmtPct(ratio(a?.netIncome, a?.revenue))}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
