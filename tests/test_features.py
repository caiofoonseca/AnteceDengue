import numpy as np
import pandas as pd

from src import config
from src.features import build_features, climate_features, feature_columns
from tests.conftest import make_clima, make_panel


def test_colunas_e_alvo(panel, clima):
    df = build_features(panel, clima)
    assert list(df.columns) == ["bairro", "week_start"] + feature_columns() + ["target_casos"]
    assert df["target_casos"].notna().all()
    assert df["week_start"].min() == panel["week_start"].min() + pd.Timedelta(weeks=config.MAX_HISTORY_WEEKS)
    assert df["week_start"].max() == panel["week_start"].max() - pd.Timedelta(weeks=1)


def test_keep_last_mantem_ultima_semana_sem_alvo(panel, clima):
    df = build_features(panel, clima, keep_last=True)
    ultima = df[df["week_start"] == panel["week_start"].max()]
    assert len(ultima) == panel["bairro"].nunique()
    assert ultima["target_casos"].isna().all()
    assert df[df["week_start"] < panel["week_start"].max()]["target_casos"].notna().all()


def test_alvo_e_casos_da_semana_seguinte(panel, clima):
    df = build_features(panel, clima)
    chave = panel.set_index(["bairro", "week_start"])["casos"]
    esperado = [chave[(b, w + pd.Timedelta(weeks=1))] for b, w in zip(df["bairro"], df["week_start"])]
    assert list(df["target_casos"]) == esperado


def test_lag_calculado_por_bairro_sem_misturar():
    p = make_panel(n_weeks=20, bairros=("A", "B"))
    p.loc[p["bairro"] == "A", "casos"] = np.arange(20)
    p.loc[p["bairro"] == "B", "casos"] = 1000 + np.arange(20)
    df = build_features(p, make_clima(20))
    for b, base in (("A", 0), ("B", 1000)):
        sub = df[df["bairro"] == b]
        assert (sub["casos_lag1"] == sub["casos_t"] - 1).all()
        assert (sub["casos_lag3"] == sub["casos_t"] - 3).all()
        assert sub["casos_lag3"].min() >= base


def test_media_movel_e_historica_usam_so_passado_e_presente():
    p = make_panel(n_weeks=20, bairros=("A",))
    p["casos"] = np.arange(20)
    df = build_features(p, make_clima(20))
    linha = df[df["casos_t"] == 12].iloc[0]
    assert linha["casos_mm4"] == np.mean([9, 10, 11, 12])
    assert linha["casos_mm8"] == np.mean(range(5, 13))
    assert linha["tendencia"] == linha["casos_mm4"] - linha["casos_mm8"]
    assert linha["casos_media_hist"] == np.mean(range(0, 12))


def test_vazamento_casos_futuros_nao_mudam_features_anteriores(panel, clima):
    base = build_features(panel, clima)
    semana_futura = panel["week_start"].min() + pd.Timedelta(weeks=35)
    alterado = panel.copy()
    alterado.loc[(alterado["bairro"] == "A") & (alterado["week_start"] >= semana_futura), "casos"] = 9999
    novo = build_features(alterado, clima)
    antes_base = base[base["week_start"] < semana_futura].reset_index(drop=True)
    antes_novo = novo[novo["week_start"] < semana_futura].reset_index(drop=True)
    pd.testing.assert_frame_equal(antes_base[feature_columns()], antes_novo[feature_columns()])
    pd.testing.assert_frame_equal(antes_base[["bairro", "week_start"]], antes_novo[["bairro", "week_start"]])


def test_vazamento_clima_futuro_nao_muda_features_anteriores(panel, clima):
    base = build_features(panel, clima)
    semana_futura = clima["week_start"].min() + pd.Timedelta(weeks=35)
    c2 = clima.copy()
    c2.loc[c2["week_start"] >= semana_futura, ["temp_media", "umid_media", "chuva_mm"]] = 500.0
    novo = build_features(panel, c2)
    cols = feature_columns()
    pd.testing.assert_frame_equal(base[base["week_start"] < semana_futura][cols].reset_index(drop=True),
                                  novo[novo["week_start"] < semana_futura][cols].reset_index(drop=True))


def test_ffill_causal_limite_de_duas_semanas():
    c = make_clima(20)
    c.loc[5:9, "temp_media"] = np.nan
    f = climate_features(c)
    lag1 = f["temp_media_lag1"].to_numpy()
    assert not np.isnan(lag1[6]) and not np.isnan(lag1[7])
    assert np.isnan(lag1[8]) and np.isnan(lag1[9]) and np.isnan(lag1[10])
    assert c["temp_media"].iloc[4] == lag1[5]


def test_chuva_acumulada_inclui_semana_atual():
    c = make_clima(20)
    c["chuva_mm"] = np.arange(20, dtype=float)
    f = climate_features(c)
    assert f["chuva_acum4"].iloc[10] == 7 + 8 + 9 + 10
    assert np.isnan(f["chuva_acum4"].iloc[2])


def test_sazonalidade_no_circulo_unitario(panel, clima):
    df = build_features(panel, clima)
    assert np.allclose(df["sazon_sin"] ** 2 + df["sazon_cos"] ** 2, 1.0)
