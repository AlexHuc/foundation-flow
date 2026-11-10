import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link, Outlet, useNavigate } from "@tanstack/react-router";
import { Bell, ChevronsLeft, ChevronsRight, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Logo } from "@/components/ff/primitives";
import { NAV } from "@/components/ff/nav";
import { companiesQueryOptions } from "@/lib/api";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/_workspace")({
  component: WorkspaceLayout,
});

function WorkspaceLayout() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="flex min-h-screen bg-background">
      <aside className={cn("sticky top-0 hidden h-screen shrink-0 flex-col border-r bg-sidebar transition-[width] md:flex", collapsed ? "w-16" : "w-60")}>
        <div className="flex h-14 items-center justify-between border-b px-4">
          <Link to="/"><Logo compact={collapsed} /></Link>
        </div>
        <nav className="flex-1 space-y-0.5 overflow-y-auto p-2">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              {...("params" in item ? { params: item.params } : {})}
              title={item.label}
              className="group relative flex items-center gap-3 rounded-md px-3 py-2 text-[13px] font-medium text-sidebar-foreground transition-colors hover:bg-accent hover:text-foreground"
              activeProps={{ className: "bg-sidebar-accent !text-foreground before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] before:rounded-full before:bg-primary" }}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          ))}
        </nav>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex h-11 items-center gap-2 border-t px-5 text-xs text-muted-foreground hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <><ChevronsLeft className="h-4 w-4" /> Collapse</>}
        </button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <TopNavigation />
        <main className="flex-1 px-4 py-8 md:px-8"><Outlet /></main>
      </div>
    </div>
  );
}

function TopNavigation() {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { data } = useQuery(companiesQueryOptions);
  const companies = data?.companies ?? [];
  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return companies;
    return companies.filter((c) => c.ticker.toLowerCase().includes(s) || c.name.toLowerCase().includes(s));
  }, [q, companies]);
  const go = (ticker: string) => {
    setOpen(false); setQ("");
    navigate({ to: "/company/$ticker", params: { ticker } });
  };
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-4 border-b bg-background/85 px-4 backdrop-blur md:px-8">
      <div className="md:hidden"><Link to="/"><Logo compact /></Link></div>
      <div className="relative w-full max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          onKeyDown={(e) => { if (e.key === "Enter" && results[0]) go(results[0].ticker); }}
          placeholder="Search ticker or company…"
          aria-label="Search companies"
          className="h-9 w-full rounded-md border bg-surface pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
        />
        {open && (
          <div className="absolute left-0 right-0 top-11 overflow-hidden rounded-md border bg-popover shadow-2xl">
            {results.length === 0 && <div className="px-3 py-3 text-sm text-muted-foreground">No matching companies</div>}
            {results.map((c) => (
              <button key={c.ticker} onMouseDown={() => go(c.ticker)} className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-accent">
                <span className="num w-14 text-sm font-bold text-chart">{c.ticker}</span>
                <span className="truncate text-sm text-foreground">{c.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">{c.exchange}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="ml-auto flex items-center gap-3">
        <button aria-label="Notifications" className="rounded-md p-2 text-muted-foreground hover:bg-accent hover:text-foreground"><Bell className="h-4 w-4" /></button>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">FF</div>
      </div>
    </header>
  );
}
