import json
import random
import re
from pathlib import Path

import pandas as pd
import yaml

from scripts import seed_mlflow, sim_publisher
from src import config
from src.ingest_mqtt import parse_payload

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_sklearn_do_runtime_igual_ao_do_modelo():
    meta = json.loads(config.MODEL_META_PATH.read_text(encoding="utf-8"))
    pins = re.findall(r"^scikit-learn==(\S+)$", (ROOT / "requirements-runtime.txt").read_text(), flags=re.M)
    assert pins == [meta["sklearn_version"]]


def test_runtime_nao_traz_ferramentas_de_desenvolvimento():
    texto = (ROOT / "requirements-runtime.txt").read_text().lower()
    for pacote in ("jupyter", "nbconvert", "pytest", "ipykernel"):
        assert pacote not in texto


def test_servicos_do_compose_e_perfis():
    servicos = COMPOSE["services"]
    base = {"mosquitto", "postgres", "mlflow", "ingestor", "api", "dashboard"}
    assert base <= set(servicos)
    assert servicos["sensor-sim"]["profiles"] == ["demo"]
    assert servicos["seed-mlflow"]["profiles"] == ["init"]
    assert servicos["trainer"]["profiles"] == ["train"]
    for nome in base:
        assert "healthcheck" in servicos[nome], nome
    assert "--final" not in json.dumps(servicos["trainer"]["command"])


def test_dependencias_esperam_servico_saudavel():
    for servico in COMPOSE["services"].values():
        for nome, dep in servico.get("depends_on", {}).items():
            esperado = "service_completed_successfully" if nome == "airflow-init" else "service_healthy"
            assert dep["condition"] == esperado


def test_postgres_e_mlflow_so_no_localhost_e_dados_so_leitura():
    servicos = COMPOSE["services"]
    assert all(p.startswith("127.0.0.1:") for p in servicos["postgres"]["ports"])
    assert all(p.startswith("127.0.0.1:") for p in servicos["mlflow"]["ports"])
    montagens = servicos["api"]["volumes"]
    assert all(v.endswith(":ro") for v in montagens)
    assert not any("mlflow.db" in v for s in servicos.values() for v in s.get("volumes", []))


def test_leitura_simulada_valida_e_invalida_passam_pelo_parser():
    rng = random.Random(1)
    quando = pd.Timestamp("2026-11-24T12:00:00Z").to_pydatetime()
    topico = sim_publisher.TOPIC.format("recife-001")
    ok = parse_payload(topico, json.dumps(sim_publisher.make_reading(rng, "recife-001", quando)).encode())
    ruim = parse_payload(topico, json.dumps(sim_publisher.make_reading(rng, "recife-001", quando, True)).encode())
    assert ok["is_valid"] is True and ruim["is_valid"] is False


def test_seed_so_registra_linhas_do_experimento_03(tmp_path):
    csv = tmp_path / "m.csv"
    pd.DataFrame({"modelo": ["A", "B (otimizado)"], "experimento": ["02", "03"],
                  "f1_macro_val": [0.5, 0.6]}).to_csv(csv, index=False)

    class Falso:
        def __init__(self):
            self.runs = []

        def run(self, nome, tags=None):
            from contextlib import nullcontext
            self.runs.append(nome)
            return nullcontext()

        def log_params(self, *a):
            pass

        def log_metrics(self, *a):
            pass

    falso = Falso()
    assert seed_mlflow.seed_comparison(falso, csv) == 1
    assert falso.runs == ["B (otimizado)"]


def test_api_e_dashboard_publicam_so_no_localhost_por_padrao():
    servicos = COMPOSE["services"]
    for nome in ("api", "dashboard"):
        assert all(p.startswith("${BIND_ADDRESS:-127.0.0.1}:") for p in servicos[nome]["ports"])
    assert servicos["mosquitto"]["ports"] == ["${MQTT_HOST_PORT:-1883}:1883"]
    assert "BIND_ADDRESS" in (ROOT / ".env.example").read_text(encoding="utf-8")
