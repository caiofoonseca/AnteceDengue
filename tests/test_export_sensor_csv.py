import datetime as dt

import pandas as pd
import pytest
from sqlalchemy import create_engine, insert

from src import export_sensor_csv as ex
from src.db import init_db, sensor_weekly


@pytest.fixture
def engine():
    eng = create_engine("sqlite://")
    init_db(eng)
    return eng


def gravar(engine, linhas):
    with engine.begin() as conn:
        conn.execute(insert(sensor_weekly), linhas)


LINHAS = [
    {"bairro": "VARZEA", "week_start": dt.date(2026, 11, 22), "temp_media": 27.333, "umid_media": 71.5,
     "chuva_mm": 1.25, "n_leituras": 12, "bateria_min": 4.0},
    {"bairro": "BOA VIAGEM", "week_start": dt.date(2026, 11, 22), "temp_media": 28.0, "umid_media": 75.0,
     "chuva_mm": 0.0, "n_leituras": 12, "bateria_min": 4.0},
    {"bairro": "BOA VIAGEM", "week_start": dt.date(2026, 11, 15), "temp_media": 29.1, "umid_media": 70.0,
     "chuva_mm": 3.0, "n_leituras": 168, "bateria_min": 4.0},
]


def test_banco_vazio_gera_so_o_cabecalho_e_avisa(engine, tmp_path, caplog):
    saida = tmp_path / "sensor_semanal.csv"
    with caplog.at_level("WARNING"):
        assert ex.export_sensor_csv(engine, saida) == 0
    assert saida.read_text(encoding="utf-8").strip() == ",".join(ex.COLUMNS)
    assert "vazia" in caplog.text


def test_colunas_ordem_e_fonte(engine, tmp_path):
    gravar(engine, LINHAS)
    saida = tmp_path / "s.csv"
    assert ex.export_sensor_csv(engine, saida) == 3
    df = pd.read_csv(saida)
    assert list(df.columns) == ["bairro", "semana_inicio", "temp_media", "umid_media", "chuva_mm_soma",
                                "n_leituras", "fonte"]
    assert list(df["bairro"]) == ["BOA VIAGEM", "BOA VIAGEM", "VARZEA"]
    assert list(df["semana_inicio"]) == ["2026-11-15", "2026-11-22", "2026-11-22"]
    assert set(df["fonte"]) == {"api_open_meteo_via_mqtt"}
    assert df.loc[2, "temp_media"] == 27.33 and df.loc[2, "chuva_mm_soma"] == 1.25


def test_semana_parcial_aparece_com_o_numero_de_leituras(engine, tmp_path):
    gravar(engine, LINHAS)
    saida = tmp_path / "s.csv"
    ex.export_sensor_csv(engine, saida)
    atual = pd.read_csv(saida).query("semana_inicio == '2026-11-22' and bairro == 'BOA VIAGEM'")
    assert int(atual["n_leituras"].iloc[0]) == 12


def test_idempotente_e_sem_arquivo_temporario(engine, tmp_path):
    gravar(engine, LINHAS)
    saida = tmp_path / "s.csv"
    ex.export_sensor_csv(engine, saida)
    primeiro = saida.read_bytes()
    ex.export_sensor_csv(engine, saida)
    assert saida.read_bytes() == primeiro
    assert [p.name for p in tmp_path.iterdir()] == ["s.csv"]


def test_substitui_o_arquivo_anterior(engine, tmp_path):
    saida = tmp_path / "s.csv"
    saida.write_text("lixo", encoding="utf-8")
    gravar(engine, LINHAS[:1])
    ex.export_sensor_csv(engine, saida)
    assert "lixo" not in saida.read_text(encoding="utf-8")
