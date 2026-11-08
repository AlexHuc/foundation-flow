from operators.yahoo_finance import FetchYahooFinanceInsiderRosterHolders
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
    dag_id="yahoo_fetch_insider_roster_holders",
    description="Fetch insider roster and direct share ownership from Yahoo Finance",
    start_date=pendulum.datetime(2026, 10, 28, tz="UTC"),
    schedule="0 8 * * 1",  # Weekly Monday 8 AM UTC (3 AM ET)
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=[
        "data-ingestion",
        "yahoo-finance",
        "ownership",
        "insider-roster-holders",
    ],
) as dag:

    for ticker in TICKERS:
        FetchYahooFinanceInsiderRosterHolders(
            task_id=f"fetch_insider_roster_holders_{ticker.lower().replace('.', '_')}",
            ticker=ticker,
            postgres_conn_id="postgres_landing",
        )