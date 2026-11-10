import {
  BarChart3, Bell, Briefcase, Building2, FileText, Filter, GitCompare, LayoutDashboard,
  Landmark, Layers, Settings, Star, Calculator, Users,
} from "lucide-react";

export const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/company/$ticker", label: "Company Explorer", icon: Building2, params: { ticker: "CRDO" } },
  { to: "/statements", label: "Financial Statements", icon: FileText },
  { to: "/screener", label: "Stock Screener", icon: Filter },
  { to: "/compare", label: "Compare Companies", icon: GitCompare },
  { to: "/analysts", label: "Analyst Research", icon: BarChart3 },
  { to: "/ownership", label: "Ownership & Insiders", icon: Users },
  { to: "/options", label: "Options Explorer", icon: Layers },
  { to: "/filings", label: "SEC Filings", icon: Landmark },
  { to: "/valuation", label: "Valuation Models", icon: Calculator },
  { to: "/watchlists", label: "Watchlists", icon: Star },
  { to: "/portfolio", label: "Portfolio", icon: Briefcase },
  { to: "/settings", label: "Settings", icon: Settings },
] as const;

export { Bell };
