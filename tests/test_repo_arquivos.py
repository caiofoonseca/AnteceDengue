"""O clone do repositório precisa trazer o mínimo para rodar sem regenerar dados nem retreinar o modelo."""
import subprocess

import pytest

from src import config

MINIMOS = [
    "models/best_model.joblib", "models/model_meta.json",
    "data/processed/panel.csv", "data/processed/clima_semanal.csv", "data/processed/predictions_latest.csv",
    "reports/teste_final.json", "app/assets/bairros.geojson", "app/assets/logo.svg", ".env.example",
    "config/stations_bairros.json", ".streamlit/config.toml",
]
NAO_VERSIONADOS = ["data/processed/manifest.json", ".env", "mlflow.db"]


@pytest.fixture(scope="module")
def versionados():
    try:
        saida = subprocess.run(["git", "ls-files"], cwd=config.ROOT, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("sem git ou fora de um repositório")
    return set(saida.stdout.split("\n"))


@pytest.mark.parametrize("caminho", MINIMOS)
def test_arquivo_minimo_esta_versionado(versionados, caminho):
    assert caminho in versionados


@pytest.mark.parametrize("caminho", NAO_VERSIONADOS)
def test_segredos_e_temporarios_ficam_fora(versionados, caminho):
    assert caminho not in versionados
    assert not any(c.startswith("data/raw/") and not c.endswith(".gitkeep") for c in versionados)
    assert not any(c.endswith(".bak") for c in versionados)
