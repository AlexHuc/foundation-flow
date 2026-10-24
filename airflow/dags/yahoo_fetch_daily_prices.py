from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
from airflow import DAG
import sys

sys.path.insert(0, '/opt/airflow/operators')
from yahoo_finance_operators import FetchYahooFinancePricesOperator

# Global variables
TICKERS = ['CRDO']
PERIOD = '5d'      # Daily data
INTERVAL = '1d'    # Daily interval

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
    'yahoo_fetch_daily_prices',
    default_args=default_args,
    description='Fetch daily OHLCV prices from Yahoo Finance',
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=['data-ingestion', 'yahoo-finance', 'prices'],
)

# Fetch prices
fetch_tasks = []
for ticker in TICKERS:
    fetch_task = FetchYahooFinancePricesOperator(
        task_id=f'fetch_prices_{ticker}',
        ticker=ticker,
        period=PERIOD,
        interval=INTERVAL,
        postgres_conn_id='postgres_raw',
        dag=dag,
    )
    fetch_tasks.append(fetch_task)

fetch_tasks