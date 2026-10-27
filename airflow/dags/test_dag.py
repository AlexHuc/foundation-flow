from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from airflow import DAG

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2023, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="test_dag",
    default_args=default_args,
    description="A simple test DAG",
    schedule=timedelta(days=1),
    catchup=False,
) as dag:
    task1 = BashOperator(
        task_id="print_hello",
        bash_command='echo "Hello World!"',
    )
