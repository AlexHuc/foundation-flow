import { Info } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="h-7 w-7 shrink-0" aria-hidden>
        <rect width="32" height="32" rx="7" className="fill-primary" />
        <path d="M9 23 L15 9 H24 L22.5 12.5 H17.5 L16.3 15.5 H21 L19.6 19 H14.8 L13 23 Z" className="fill-primary-foreground" />
      </svg>
      {!compact && (
        <span className="text-[15px] font-bold tracking-tight text-foreground">
          Foundation<span className="text-chart">Flow</span>
        </span>
      )}
    </div>
  );
}

export function DataLabel({ kind }: { kind: "Illustrative" | "Reported" | "Calculated" | "Latest Available" | "Data Unavailable" }) {
  const tone =
    kind === "Illustrative"
      ? "border-chart/40 text-chart"
      : kind === "Data Unavailable"
        ? "border-border text-muted-foreground"
        : "border-border text-muted-foreground";
  return (
    <span className={cn("inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider", tone)}>
      {kind}
    </span>
  );
}

export function Panel({ title, eyebrow, actions, children, className }: { title?: string; eyebrow?: string; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-lg border bg-surface", className)}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div>
            {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
            {title && <h3 className="text-[15px] font-semibold text-foreground">{title}</h3>}
          </div>
          {actions}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function MetricCard({
  label, value, unit, date, change, changeMeaningful = true, hint, label2 = "Illustrative",
}: {
  label: string; value: string; unit?: string; date?: string; change?: number | null;
  changeMeaningful?: boolean; hint?: string; label2?: Parameters<typeof DataLabel>[0]["kind"];
}) {
  const dir = change == null ? null : change >= 0 ? "up" : "down";
  return (
    <div className="group relative overflow-hidden rounded-lg border bg-surface p-5 transition-colors hover:border-primary/50">
      <div className="flex items-center justify-between">
        <span className="eyebrow flex items-center gap-1.5">
          {label}
          {hint && (
            <span title={hint} className="cursor-help"><Info className="h-3 w-3" /></span>
          )}
        </span>
        <DataLabel kind={label2} />
      </div>
      <div className="num mt-4 text-3xl font-bold tracking-tight text-foreground">
        {value}
        {unit && <span className="ml-1 text-sm font-medium text-muted-foreground">{unit}</span>}
      </div>
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span className="num">{date ?? ""}</span>
        {change != null && (
          <span className={cn("num font-semibold", !changeMeaningful ? "text-muted-foreground" : dir === "up" ? "text-positive" : "text-negative")}>
            {change >= 0 ? "▲" : "▼"} {Math.abs(change * 100).toFixed(1)}% YoY
          </span>
        )}
      </div>
    </div>
  );
}

export function EmptyDataState({ title, body }: { title: string; body: string }) {
  return (
    <div className="diagonal-lines flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-16 text-center">
      <div className="eyebrow mb-2">Data Unavailable</div>
      <h3 className="text-lg font-semibold text-foreground">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{body}</p>
    </div>
  );
}

export function DataFreshnessIndicator({ date }: { date: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span className="h-1.5 w-1.5 rounded-full bg-chart" />
      Snapshot date <span className="num text-foreground">{date}</span>
      <DataLabel kind="Illustrative" />
    </div>
  );
}
