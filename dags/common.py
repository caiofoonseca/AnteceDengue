"""Configuração comum dos DAGs do AnteceDengue. Os DAGs só chamam módulos do projeto (python -m src...)."""
import os
from datetime import timedelta

import pendulum

TZ = pendulum.timezone("America/Recife")
START_DATE = pendulum.datetime(2026, 1, 1, tz=TZ)
PROJECT_DIR = os.getenv("PROJECT_DIR", "/opt/airflow/project")
PYTHON = os.getenv("PIPELINE_PYTHON", "python")

DEFAULT_ARGS = {
    "owner": "antecedengue",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

DAG_KWARGS = {
    "start_date": START_DATE,
    "catchup": False,
    "default_args": DEFAULT_ARGS,
    "max_active_runs": 1,
}


def py(args: str) -> str:
    return f"{PYTHON} {args}"
