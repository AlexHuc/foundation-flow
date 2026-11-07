from operators.yahoo_finance import FetchYahooFinanceHistory
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
}


with DAG(
    dag_id="yahoo_fetch_history",
    description="Fetch daily OHLCV history from Yahoo Finance",
    start_date=pendulum.datetime(2026, 10, 28, tz="UTC"),
    schedule="0 8 * * 1",  # Weekly Monday 8 AM UTC (3 AM ET)
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["data-ingestion", "yahoo-finance", "history"],
) as dag:

    for ticker in TICKERS:
        FetchYahooFinanceHistory(
            task_id=f"fetch_history_{ticker.lower().replace('.', '_')}",
            ticker=ticker,
            period="max",
            interval="1d",
            postgres_conn_id="postgres_landing",
        )