"""Registry of the landing-schema datasets exposed by the API.

Table and column names come exclusively from the SQL migrations under
database/migrations/postgres/landing/yfinance/. They are never taken from
request input, which keeps the generic dataset endpoint free of SQL injection.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Dataset:
    slug: str
    table: str
    # Column used for ordering and optional from/to date filtering.
    date_column: str
    description: str


SCHEMA = "landing"

DATASETS: dict[str, Dataset] = {
    d.slug: d
    for d in [
        Dataset("history", "yahoo_history", "date", "Daily OHLCV prices"),
        Dataset("info", "yahoo_info", "date", "Company fundamentals snapshots"),
        Dataset("fast-info", "yahoo_fast_info", "date", "Daily fast_info snapshots"),
        Dataset("income-statement", "yahoo_income_statement", "date", "Annual income statement"),
        Dataset("quarterly-income-statement", "yahoo_quarterly_income_statement", "date", "Quarterly income statement"),
        Dataset("ttm-income-statement", "yahoo_ttm_income_statement", "date", "Trailing-twelve-month income statement"),
        Dataset("balance-sheet", "yahoo_balance_sheet", "date", "Annual balance sheet"),
        Dataset("quarterly-balance-sheet", "yahoo_quarterly_balance_sheet", "date", "Quarterly balance sheet"),
        Dataset("cashflow", "yahoo_cashflow", "date", "Annual cash flow statement"),
        Dataset("quarterly-cashflow", "yahoo_quarterly_cashflow", "date", "Quarterly cash flow statement"),
        Dataset("ttm-cashflow", "yahoo_ttm_cashflow", "date", "Trailing-twelve-month cash flow"),
        Dataset("earnings-dates", "yahoo_earnings_dates", "earnings_date", "Earnings announcements and surprises"),
        Dataset("calendar", "yahoo_calendar", "date", "Dividend and earnings calendar"),
        Dataset("earnings-history", "yahoo_earnings_history", "quarter", "Quarterly earnings results"),
        Dataset("earnings-estimate", "yahoo_earnings_estimate", "date", "Analyst earnings estimates"),
        Dataset("revenue-estimate", "yahoo_revenue_estimate", "date", "Analyst revenue estimates"),
        Dataset("eps-trend", "yahoo_eps_trend", "date", "EPS trend"),
        Dataset("eps-revisions", "yahoo_eps_revisions", "date", "EPS revisions"),
        Dataset("growth-estimates", "yahoo_growth_estimates", "date", "Growth estimates"),
        Dataset("recommendations", "yahoo_recommendations", "date", "Analyst recommendations"),
        Dataset("upgrades-downgrades", "yahoo_upgrades_downgrades", "grade_date", "Analyst upgrades and downgrades"),
        Dataset("option-chain", "yahoo_option_chain", "date", "Options chain snapshots"),
        Dataset("major-holders", "yahoo_major_holders", "date", "Major holders breakdown"),
        Dataset("institutional-holders", "yahoo_institutional_holders", "date", "Institutional holders"),
        Dataset("mutualfund-holders", "yahoo_mutualfund_holders", "date", "Mutual fund holders"),
        Dataset("insider-transactions", "yahoo_insider_transactions", "date", "Insider transactions"),
        Dataset("insider-purchases", "yahoo_insider_purchases", "date", "Insider purchase summary"),
        Dataset("insider-roster-holders", "yahoo_insider_roster_holders", "date", "Insider roster"),
        Dataset("sec-filings", "yahoo_sec_filings", "date", "SEC filings"),
    ]
}

# Financial statements exposed through the dedicated /financials endpoint.
STATEMENT_TABLES: dict[tuple[str, str], str] = {
    ("income", "annual"): "yahoo_income_statement",
    ("income", "quarterly"): "yahoo_quarterly_income_statement",
    ("income", "ttm"): "yahoo_ttm_income_statement",
    ("balance", "annual"): "yahoo_balance_sheet",
    ("balance", "quarterly"): "yahoo_quarterly_balance_sheet",
    ("cashflow", "annual"): "yahoo_cashflow",
    ("cashflow", "quarterly"): "yahoo_quarterly_cashflow",
    ("cashflow", "ttm"): "yahoo_ttm_cashflow",
}
