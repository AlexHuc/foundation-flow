from datetime import datetime, timedelta
from airflow import DAG
import sys

sys.path.insert(0, '/opt/airflow/operators')
from yahoo_finance_operators import FetchYahooFinanceTickerInfo

# Global variables
TICKERS = ['CRDO']

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
    'yahoo_fetch_info',
    default_args=default_args,
    description='Fetch fundamental info metrics from Yahoo Finance',
    schedule='0 8 * * 1',  # Weekly Monday 8 AM UTC (3 AM ET)
    catchup=False,
    max_active_runs=1,
    tags=['data-ingestion', 'yahoo-finance', 'fundamentals', 'info'],
)

# Fetch fundamentals
fetch_tasks = []
for ticker in TICKERS:
    fetch_task = FetchYahooFinanceTickerInfo(
        task_id=f'fetch_info_{ticker}',
        ticker=ticker,
        postgres_conn_id='postgres_landing',
        dag=dag,
    )
    fetch_tasks.append(fetch_task)

fetch_tasks