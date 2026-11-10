import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowRight, BarChart3, Calculator, FileText, Filter, GitCompare, Landmark, Layers, LineChart, Users } from "lucide-react";
import { FinancialBarChart } from "@/components/ff/charts";
import { DataLabel, Logo, MetricCard } from "@/components/ff/primitives";
import { fmtMoney, freeCashFlow, growth } from "@/lib/metrics";
import { COMPANIES } from "@/lib/sample-data";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Foundation Flow — See Beyond the Stock Price" },
      { name: "description", content: "Premium fundamental stock analysis: financial statements, analyst research, ownership, filings and intrinsic value." },
      { property: "og:title", content: "Foundation Flow — See Beyond the Stock Price" },
      { property: "og:description", content: "Discover your Ego. Enter the Flow State. Fundamental research for long-term investors." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

const FEATURES = [
  { icon: LineChart, t: "Fundamental Analysis", d: "Profitability, growth and financial health, calculated only from reported inputs." },
  { icon: FileText, t: "Financial Statements", d: "Income, balance sheet and cash flow across annual and quarterly periods." },
  { icon: BarChart3, t: "Analyst Research", d: "Estimates, revisions, recommendations and price targets." },
  { icon: Users, t: "Ownership & Insiders", d: "Institutional holders, fund positions and insider transactions." },
  { icon: Layers, t: "Options Explorer", d: "Chains by expiration with open interest and implied volatility." },
  { icon: Landmark, t: "SEC Filings", d: "Filing history with exhibits, dated by filing date." },
  { icon: Filter, t: "Stock Screener", d: "Filter the universe on the fundamentals that matter." },
  { icon: GitCompare, t: "Company Comparison", d: "Side-by-side metrics on aligned reporting periods." },
  { icon: Calculator, t: "Intrinsic Value", d: "DCF scenarios built on historical cash flow." },
];

function Landing() {
  const c = COMPANIES[0]!;
  const last = c.annual.at(-1)!, prev = c.annual.at(-2)!;
  return (
    <div className="min-h-screen bg-background">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
        <Logo />
        <Link to="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground">Sign in</Link>
      </nav>

      <section className="relative overflow-hidden border-b">
        <div className="ambient diagonal-lines absolute inset-0" aria-hidden />
        <svg className="absolute -right-24 top-0 h-full w-[60%] opacity-40" viewBox="0 0 600 600" preserveAspectRatio="none" aria-hidden>
          <path d="M600 0 L260 600" className="stroke-primary" strokeWidth="1" />
          <path d="M600 120 L330 600" className="stroke-chart" strokeWidth="0.5" />
          <path d="M520 0 L180 600" className="stroke-muted-foreground" strokeWidth="0.4" />
        </svg>
        <div className="relative mx-auto max-w-7xl px-6 pb-24 pt-20 md:pt-28">
          <div className="eyebrow mb-6 flex items-center gap-3"><span className="h-px w-10 bg-primary" />Discover your Ego. Enter the Flow State.</div>
          <h1 className="max-w-4xl text-5xl font-extrabold leading-[0.95] tracking-tighter md:text-7xl lg:text-8xl">
            See Beyond <br />the <span className="text-chart">Stock Price.</span>
          </h1>
          <p className="mt-8 max-w-xl text-lg text-muted-foreground">
            Powerful fundamental analysis to understand businesses, uncover financial insights, and make more informed investment decisions.
          </p>
          <div className="mt-10 flex flex-wrap gap-3">
            <Link to="/dashboard" className="inline-flex items-center gap-2 rounded-md bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground transition-shadow hover:glow-primary">
              Start Analyzing <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to="/company/$ticker" params={{ ticker: "CRDO" }} className="inline-flex items-center rounded-md border px-6 py-3 text-sm font-semibold text-foreground hover:border-primary">
              Explore the Platform
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="mb-8 flex items-end justify-between">
          <div>
            <div className="eyebrow mb-2">Product preview</div>
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl">Institutional depth. Calm clarity.</h2>
          </div>
          <DataLabel kind="Illustrative" />
        </div>
        <div className="grid gap-4 rounded-xl border bg-surface/50 p-4 md:grid-cols-3 md:p-6">
          <MetricCard label={`${c.ticker} revenue`} value={fmtMoney(last.revenue)} date={`FY${last.fiscalYear}`} change={growth(last.revenue, prev.revenue)} />
          <MetricCard label="Free cash flow" value={fmtMoney(freeCashFlow(last))} date={`FY${last.fiscalYear}`} />
          <MetricCard label="Market cap" value={fmtMoney(c.marketCap)} date={`Observed ${c.priceDate}`} />
          <div className="rounded-lg border bg-surface p-5 md:col-span-3">
            <div className="eyebrow mb-3">{c.ticker} · Annual revenue</div>
            <FinancialBarChart data={c.annual.map((r) => ({ period: `FY${r.fiscalYear}`, revenue: r.revenue }))} dataKey="revenue" label="Revenue" />
          </div>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto grid max-w-7xl gap-px bg-border px-0 md:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.t} className="bg-background p-8 transition-colors hover:bg-surface">
              <f.icon className="h-5 w-5 text-chart" />
              <h3 className="mt-5 text-lg font-semibold">{f.t}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{f.d}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-xs text-muted-foreground">
          <Logo />
          <span>Research tool, not financial advice. Stored observations are not live market data.</span>
        </div>
      </footer>
    </div>
  );
}
