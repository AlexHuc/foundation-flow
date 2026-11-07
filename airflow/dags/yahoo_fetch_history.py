from datetime import datetime, timedelta
from airflow import DAG
import sys

sys.path.insert(0, '/opt/airflow/operators')
from yahoo_finance_operators import FetchYahooFinanceHistory

# Global variables
TICKERS = ['CRDO']
PERIOD = 'max'      # Daily data
INTERVAL = '1d'     # Daily interval

# Default arguments
default_args = {
    'owner': 'data-engineering',
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_base': 2,
    'start_date': datetime(2026, 10, 28),
    'email_on_failure': False,
    'email_on_retry': False,
    'depends_on_past': False,
}

# DAG definition
dag = DAG(
    'yahoo_fetch_history',
    default_args=default_args,
    description='Fetch history OHLCV prices from Yahoo Finance',
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=['data-ingestion', 'yahoo-finance', 'history prices'],
)

# Fetch history
fetch_tasks = []
for ticker in TICKERS:
    fetch_task = FetchYahooFinanceHistory(
        task_id=f'fetch_history_{ticker}',
        ticker=ticker,
        period=PERIOD,
        interval=INTERVAL,
        postgres_conn_id='postgres_landing',
        dag=dag,
    )
    fetch_tasks.append(fetch_task)

fetch_tasks