import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtMoney } from "@/lib/metrics";

const axis = { stroke: "var(--muted-foreground)", fontSize: 11, tickLine: false, axisLine: false } as const;
const tooltipStyle = {
  contentStyle: { background: "var(--surface-raised)", border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 },
  labelStyle: { color: "var(--muted-foreground)" },
  itemStyle: { color: "var(--foreground)" },
};

export function PriceChart({ data }: { data: { date: string; close: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
        <defs>
          <linearGradient id="pc" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--chart)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--chart)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis dataKey="date" {...axis} tickFormatter={(d: string) => d.slice(0, 7)} minTickGap={40} />
        <YAxis {...axis} width={48} domain={["auto", "auto"]} />
        <Tooltip {...tooltipStyle} formatter={(v: number) => [`$${v.toFixed(2)}`, "Close"]} />
        <Area type="monotone" dataKey="close" stroke="var(--chart)" strokeWidth={2} fill="url(#pc)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function FinancialBarChart({ data, dataKey, label }: { data: Record<string, number | string | null>[]; dataKey: string; label: string }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ left: 0, right: 8, top: 8 }}>
        <CartesianGrid stroke="var(--border)" vertical={false} />
        <XAxis dataKey="period" {...axis} />
        <YAxis {...axis} width={56} tickFormatter={(v: number) => fmtMoney(v)} />
        <Tooltip {...tooltipStyle} cursor={{ fill: "var(--accent)" }} formatter={(v: number) => [fmtMoney(v), label]} />
        <Bar dataKey={dataKey} fill="var(--chart)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
