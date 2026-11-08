from operators.yahoo_finance import FetchYahooFinanceGrowthEstimates
from datetime import timedelta
from airflow import DAG
import pendulum


TICKERS = ["CRDO"]

DEFAULT_ARGS = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "email_on_failure": False,
    "email_on_retry": False,
    "depends_on_past": False,
}


with DAG(
    dag_id="yahoo_fetch_growth_estimates",
    description="Fetch stock and index growth estimates from Yahoo Finance",
    start_date=pendulum.datetime(2026, 10, 28, tz="UTC"),
    schedule="0 8 * * 1",
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=[
        "data-ingestion",
        "yahoo-finance",
        "fundamentals",
        "growth-estimates",
    ],
) as dag:

    for ticker in TICKERS:
        FetchYahooFinanceGrowthEstimates(
            task_id=f"fetch_growth_estimates_{ticker.lower().replace('.', '_')}",
            ticker=ticker,
            postgres_conn_id="postgres_landing",
        )