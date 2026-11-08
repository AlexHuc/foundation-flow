"""Custom Airflow operators for Yahoo Finance ingestion."""

from .base import YahooFinanceBaseOperator
from .history import FetchYahooFinanceHistory
from .info import FetchYahooFinanceTickerInfo
from .fast_info import FetchYahooFinanceTickerFastInfo
from .income_statement import FetchYahooFinanceIncomeStatement
from .quarterly_income_statement import FetchYahooFinanceQuarterlyIncomeStatement
from .ttm_income_statement import FetchYahooFinanceTTMIncomeStatement
from .balance_sheet import FetchYahooFinanceBalanceSheet
from .quarterly_balance_sheet import FetchYahooFinanceQuarterlyBalanceSheet
from .cashflow import FetchYahooFinanceCashFlow
from .quarterly_cashflow import FetchYahooFinanceQuarterlyCashFlow
from .ttm_cashflow import FetchYahooFinanceTTMCashFlow
from .earnings_dates import FetchYahooFinanceEarningsDates
from .calendar import FetchYahooFinanceCalendar
from .earnings_history import FetchYahooFinanceEarningsHistory
from .earnings_estimate import FetchYahooFinanceEarningsEstimate
from .revenue_estimate import FetchYahooFinanceRevenueEstimate
from .eps_trend import FetchYahooFinanceEPSTrend
from .eps_revisions import FetchYahooFinanceEPSRevisions
from .growth_estimates import FetchYahooFinanceGrowthEstimates
from .recommendations import FetchYahooFinanceRecommendations
from .upgrades_downgrades import FetchYahooFinanceUpgradesDowngrades
from .option_chain import FetchYahooFinanceOptionChain
from .major_holders import FetchYahooFinanceMajorHolders
from .institutional_holders import FetchYahooFinanceInstitutionalHolders
from .mutualfund_holders import FetchYahooFinanceMutualFundHolders
from .insider_transactions import FetchYahooFinanceInsiderTransactions
from .insider_purchases import FetchYahooFinanceInsiderPurchases
from .insider_roster_holders import FetchYahooFinanceInsiderRosterHolders
from .sec_filings import FetchYahooFinanceSECFilings

__all__ = [
    "YahooFinanceBaseOperator",
    "FetchYahooFinanceHistory",
    "FetchYahooFinanceTickerInfo",
    "FetchYahooFinanceTickerFastInfo",
    "FetchYahooFinanceIncomeStatement",
    "FetchYahooFinanceQuarterlyIncomeStatement",
    "FetchYahooFinanceTTMIncomeStatement",
    "FetchYahooFinanceBalanceSheet",
    "FetchYahooFinanceQuarterlyBalanceSheet",
    "FetchYahooFinanceCashFlow",
    "FetchYahooFinanceQuarterlyCashFlow",
    "FetchYahooFinanceTTMCashFlow",
    "FetchYahooFinanceEarningsDates",
    "FetchYahooFinanceCalendar",
    "FetchYahooFinanceEarningsHistory",
    "FetchYahooFinanceEarningsEstimate",
    "FetchYahooFinanceRevenueEstimate",
    "FetchYahooFinanceEPSTrend",
    "FetchYahooFinanceEPSRevisions",
    "FetchYahooFinanceGrowthEstimates",
    "FetchYahooFinanceRecommendations",
    "FetchYahooFinanceUpgradesDowngrades",
    "FetchYahooFinanceOptionChain",
    "FetchYahooFinanceMajorHolders",
    "FetchYahooFinanceInstitutionalHolders",
    "FetchYahooFinanceMutualFundHolders",
    "FetchYahooFinanceInsiderTransactions",
    "FetchYahooFinanceInsiderPurchases",
    "FetchYahooFinanceInsiderRosterHolders",
    "FetchYahooFinanceSECFilings"
]