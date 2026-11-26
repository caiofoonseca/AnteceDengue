import datetime as dt
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from src import config, predict_live as pl
from src.db import get_engine, init_db, load_live_predictions, save_live_predictions, sensor_weekly
from src.features import build_features, feature_columns
from src.labels import apply_thresholds
from src.models import build_model
from tests.conftest import make_clima, make_panel

BAIRROS = tuple(f"B{i:02d}" for i in range(12))
AGORA = dt.datetime(2026, 11, 26, 10, 0)


def sensor_frame(n_semanas=10, estacoes=("B00", "B01")):
    semanas = pd.date_range(end=pd.Timestamp("2026-11-15"), periods=n_semanas, freq="7D")
    linhas = []
    for i, bairro in enumerate(estacoes):
        for k, semana in enumerate(semanas):
            linhas.append({"bairro": bairro, "week_start": semana, "temp_media": 26.0 + k + i, "umid_media": 70.0 + k,
                           "chuva_mm": 10.0 * (k + 1) + i, "n_leituras": 100 + i * 100, "bateria_min": 4.0})
    return pd.DataFrame(linhas)


def test_serie_do_municipio_so_com_semanas_completas():
    sensor = pd.concat([sensor_frame(3), sensor_frame(1).assign(week_start=pd.Timestamp("2026-11-22"))])
    serie = pl.weekly_city_climate(sensor, AGORA)
    assert serie["week_start"].max() == pd.Timestamp("2026-11-15")
    assert list(serie.columns) == ["week_start", "temp_media", "umid_media", "chuva_mm"]


def test_semana_em_andamento_fica_de_fora():
    sensor = sensor_frame(3).assign(week_start=lambda d: d["week_start"] + pd.Timedelta(days=7))
    serie = pl.weekly_city_climate(sensor, AGORA)
    assert serie["week_start"].max() == pd.Timestamp("2026-11-15")


def test_temperatura_ponderada_por_leituras_e_chuva_media_entre_estacoes():
    serie = pl.weekly_city_climate(sensor_frame(1), AGORA).iloc[0]
    assert serie["temp_media"] == pytest.approx((26.0 * 100 + 27.0 * 200) / 300)
    assert serie["chuva_mm"] == pytest.approx((10.0 + 11.0) / 2)


def test_semana_faltando_vira_nula_e_nao_aproxima_lags():
    sensor = sensor_frame(5)
    sensor = sensor[sensor["week_start"] != sensor["week_start"].unique()[2]]
    serie = pl.weekly_city_climate(sensor, AGORA)
    assert len(serie) == 5 and serie["chuva_mm"].isna().sum() == 1 and serie["temp_media"].isna().sum() == 1


def test_sem_leituras_ou_sem_semana_completa_levanta_erro_claro():
    with pytest.raises(pl.LiveClimateUnavailable, match="vazio"):
        pl.weekly_city_climate(pd.DataFrame(), AGORA)
    so_atual = sensor_frame(1).assign(week_start=pd.Timestamp("2026-11-22"))
    with pytest.raises(pl.LiveClimateUnavailable, match="semana completa"):
        pl.weekly_city_climate(so_atual, AGORA)


def test_features_de_clima_da_ultima_semana():
    serie = pl.weekly_city_climate(sensor_frame(10), AGORA)
    valores, semana, n = pl.live_climate_values(serie)
    assert semana == pd.Timestamp("2026-11-15") and n == 10
    assert valores["temp_media_lag1"] == serie["temp_media"].iloc[-2]
    assert valores["chuva_acum2"] == pytest.approx(serie["chuva_mm"].iloc[-2:].sum())
    assert valores["chuva_acum8"] == pytest.approx(serie["chuva_mm"].iloc[-8:].sum())
    assert not np.isnan(list(valores.values())).any()


@pytest.fixture(scope="module")
def ambiente():
    panel, clima = make_panel(n_weeks=45, bairros=BAIRROS), make_clima(45)
    df = build_features(panel, clima, city=True)
    y = apply_thresholds(df["target_casos"], (1.0, 4.0))
    features = feature_columns(True)
    modelo = build_model("rf", {"clf__n_estimators": 20}).fit(df[features], y)
    meta = {"sklearn_version": __import__("sklearn").__version__, "model_name": "RandomForest", "features": features}
    return modelo, meta, panel, clima


def test_previsao_ao_vivo_formato_e_clima_vindo_da_estacao(ambiente):
    modelo, meta, panel, clima = ambiente
    serie = pl.weekly_city_climate(sensor_frame(10), AGORA)
    out = pl.predict_live(modelo, meta, panel, clima, serie)
    assert list(out.columns) == pl.LIVE_OUTPUT_COLUMNS
    assert len(out) == len(BAIRROS) and out["bairro"].is_unique
    assert np.allclose(out[["prob_baixo", "prob_medio", "prob_alto"]].sum(axis=1), 1.0)
    assert out["risk_score"].between(0, 100).all() and sorted(out["rank"]) == list(range(1, len(BAIRROS) + 1))
    assert out["week_start"].iloc[0] == panel["week_start"].max()
    assert out["semana_clima"].iloc[0] == pd.Timestamp("2026-11-15") and out["n_semanas_clima"].iloc[0] == 10


def test_clima_da_estacao_muda_a_previsao_mas_casos_nao_sao_alterados(ambiente):
    modelo, meta, panel, clima = ambiente
    seco = sensor_frame(10).assign(chuva_mm=0.0)
    chuvoso = sensor_frame(10).assign(chuva_mm=900.0, temp_media=40.0)
    a = pl.predict_live(modelo, meta, panel, clima, pl.weekly_city_climate(seco, AGORA))
    b = pl.predict_live(modelo, meta, panel, clima, pl.weekly_city_climate(chuvoso, AGORA))
    assert not np.allclose(a.sort_values("bairro")["risk_score"], b.sort_values("bairro")["risk_score"])
    assert (a["week_start"] == b["week_start"]).all()


def test_tabela_predictions_live_guarda_so_a_ultima_execucao(ambiente, tmp_path):
    modelo, meta, panel, clima = ambiente
    out = pl.predict_live(modelo, meta, panel, clima, pl.weekly_city_climate(sensor_frame(10), AGORA))
    engine = get_engine(f"sqlite:///{tmp_path / 'b.db'}")
    init_db(engine)
    assert save_live_predictions(engine, out) == len(BAIRROS)
    assert save_live_predictions(engine, out.head(5)) == 5
    lido = load_live_predictions(engine)
    assert len(lido) == 5 and list(lido["rank"]) == sorted(lido["rank"])
    engine.dispose()


def test_run_de_ponta_a_ponta_sem_internet(ambiente, tmp_path, monkeypatch):
    modelo, meta, panel, clima = ambiente
    joblib.dump(modelo, tmp_path / "m.joblib")
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    url = f"sqlite:///{tmp_path / 'b.db'}"
    engine = get_engine(url)
    init_db(engine)
    with engine.begin() as conn:
        conn.execute(sensor_weekly.insert(), [
            {**r, "week_start": r["week_start"].date()} for r in sensor_frame(10).to_dict("records")])
    engine.dispose()
    monkeypatch.setattr(pl, "load_meta", lambda: meta)
    monkeypatch.setattr(pl, "load_model", lambda use_registry=True: (modelo, "teste"))
    monkeypatch.setattr(pl, "load_inputs", lambda: (panel, clima))
    saida = tmp_path / "live.csv"
    out = pl.run(output_path=saida, database_url=url, use_registry=False, now=AGORA)
    assert saida.exists() and len(pd.read_csv(saida)) == len(out) == len(BAIRROS)
    engine = get_engine(url)
    assert len(load_live_predictions(engine)) == len(BAIRROS)
    engine.dispose()


def test_modulo_nao_altera_arquivos_do_projeto():
    assert pl.config.LIVE_PREDICTIONS_PATH != config.PREDICTIONS_PATH
