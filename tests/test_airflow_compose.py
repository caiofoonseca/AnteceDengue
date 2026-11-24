import json
from pathlib import Path

import yaml

from src import config

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_servicos_do_airflow_no_perfil_proprio():
    servicos = COMPOSE["services"]
    for nome in ("airflow-init", "airflow-webserver", "airflow-scheduler"):
        assert servicos[nome]["profiles"] == ["airflow"], nome
    assert "healthcheck" in servicos["airflow-webserver"] and "healthcheck" in servicos["airflow-scheduler"]
    assert all(p.startswith("127.0.0.1:") for p in servicos["airflow-webserver"]["ports"])
    ambiente = servicos["airflow-webserver"]["environment"]
    assert ambiente["AIRFLOW__CORE__EXECUTOR"] == "LocalExecutor"
    assert ambiente["AIRFLOW__CORE__DEFAULT_TIMEZONE"] == "America/Recife"
    assert ambiente["AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"].endswith("/${AIRFLOW_DB_NAME:-airflow}")
    montagens = " ".join(servicos["airflow-scheduler"]["volumes"])
    for pasta in ("dags", "src", "data", "models"):
        assert f"./{pasta}:" in montagens
    assert "./models:/opt/airflow/project/models:ro" in montagens


def test_admin_do_airflow_vem_do_env_sem_senha_padrao():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "${AIRFLOW_ADMIN_PASSWORD:-}" in compose
    exemplo = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "AIRFLOW_ADMIN_PASSWORD=" in exemplo and "AIRFLOW_FERNET_KEY=" in exemplo
    init = (ROOT / "docker" / "airflow_init.py").read_text(encoding="utf-8")
    assert "sys.exit" in init and "AIRFLOW_ADMIN_PASSWORD" in init


def test_airflow_usa_constraints_oficiais_e_versao_do_sklearn_fixa():
    dockerfile = (ROOT / "Dockerfile.airflow").read_text(encoding="utf-8")
    assert "apache/airflow:2.10." in dockerfile and "python3.11" in dockerfile
    assert "constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt" in dockerfile
    meta = json.loads(config.MODEL_META_PATH.read_text(encoding="utf-8"))
    assert f"scikit-learn=={meta['sklearn_version']}" in (ROOT / "requirements-pipeline.txt").read_text()
