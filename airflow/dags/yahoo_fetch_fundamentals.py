from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow import DAG
import sys

sys.path.insert(0, '/opt/airflow/operators')
from yahoo_finance_operators import FetchYahooFinanceFundamentalsOperator

# Global variables
TICKERS = ['CRDO', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'BRK-B', 'JPM']

# Default arguments
default_args = {
    'owner': 'data-engineering',
    'retries': 0,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_base': 2,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'depends_on_past': False,
}

# DAG definition
dag = DAG(
    'yahoo_fetch_fundamentals',
    default_args=default_args,
    description='Fetch fundamental metrics from Yahoo Finance',
    schedule='0 8 * * 1',  # Weekly Monday 8 AM UTC (3 AM ET)
    catchup=False,
    max_active_runs=1,
    tags=['data-ingestion', 'yahoo-finance', 'fundamentals'],
)

# Fetch fundamentals
fetch_tasks = []
for ticker in TICKERS:
    fetch_task = FetchYahooFinanceFundamentalsOperator(
        task_id=f'fetch_fundamentals_{ticker}',
        ticker=ticker,
        postgres_conn_id='postgres_raw',
        dag=dag,
    )
    fetch_tasks.append(fetch_task)

fetch_tasks