"""Features por (bairro, semana t). Só informação da semana t e do passado.

O alvo da linha t é o número de casos da semana t+1 (coluna target_casos); a classe de risco é
calculada depois, com limiares ajustados só no treino (src/labels.py).
"""
import numpy as np
import pandas as pd

from src import config

CLIMATE_VARS = ("temp_media", "umid_media")


def feature_columns() -> list[str]:
    """Nomes das colunas de entrada do modelo, na ordem em que build_features as cria."""
    cols = ["casos_t"] + [f"casos_lag{k}" for k in config.CASE_LAGS]
    cols += [f"casos_mm{w}" for w in config.ROLLING_WINDOWS] + ["tendencia", "casos_media_hist"]
    for v in CLIMATE_VARS:
        cols += [f"{v}_lag{k}" for k in config.CLIMATE_LAGS]
    cols += [f"chuva_acum{w}" for w in config.RAIN_WINDOWS] + ["sazon_sin", "sazon_cos"]
    return cols


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Lê data/processed/panel.csv e clima_semanal.csv."""
    panel = pd.read_csv(config.DATA_PROCESSED / "panel.csv", parse_dates=["week_start"])
    clima = pd.read_csv(config.DATA_PROCESSED / "clima_semanal.csv", parse_dates=["week_start"])
    return panel, clima


def climate_features(clima: pd.DataFrame) -> pd.DataFrame:
    """Features de clima por semana (uma série para o município todo), só com passado/presente.

    1) forward fill causal (limite CLIMATE_FFILL_LIMIT semanas) em temperatura e umidade;
    2) lags de temperatura e umidade; 3) chuva acumulada nas últimas w semanas, incluindo a semana t.
    Nulos que sobrarem ficam para o SimpleImputer do Pipeline.
    """
    c = clima.sort_values("week_start").drop_duplicates("week_start").reset_index(drop=True)
    out = pd.DataFrame({"week_start": c["week_start"]})
    for v in CLIMATE_VARS:
        serie = c[v].ffill(limit=config.CLIMATE_FFILL_LIMIT)
        for k in config.CLIMATE_LAGS:
            out[f"{v}_lag{k}"] = serie.shift(k)
    for w in config.RAIN_WINDOWS:
        out[f"chuva_acum{w}"] = c["chuva_mm"].rolling(w, min_periods=w).sum()
    return out


def build_features(panel: pd.DataFrame, clima: pd.DataFrame, keep_last: bool = False) -> pd.DataFrame:
    """Uma linha por (bairro, week_start = t), com features de t e target_casos = casos(t+1).

    keep_last=False: descarta a última semana do painel (não tem alvo).
    keep_last=True: mantém essa linha (target_casos nulo), para inferência.
    Sempre descarta as primeiras MAX_HISTORY_WEEKS semanas de cada bairro (histórico incompleto).
    """
    p = panel.sort_values(["bairro", "week_start"]).reset_index(drop=True)
    g = p.groupby("bairro")["casos"]

    out = pd.DataFrame({"bairro": p["bairro"], "week_start": p["week_start"], "casos_t": p["casos"]})
    for k in config.CASE_LAGS:
        out[f"casos_lag{k}"] = g.shift(k)
    for w in config.ROLLING_WINDOWS:
        out[f"casos_mm{w}"] = g.transform(lambda s, w=w: s.rolling(w, min_periods=w).mean())
    out["tendencia"] = out[f"casos_mm{config.ROLLING_WINDOWS[0]}"] - out[f"casos_mm{config.ROLLING_WINDOWS[-1]}"]
    out["casos_media_hist"] = g.transform(lambda s: s.shift(1).expanding().mean())

    out = out.merge(climate_features(clima), on="week_start", how="left")

    meio = out["week_start"] + pd.Timedelta(days=3)
    ang = 2 * np.pi * meio.dt.dayofyear / 365.25
    out["sazon_sin"], out["sazon_cos"] = np.sin(ang), np.cos(ang)

    out["target_casos"] = g.shift(-1)
    out["_pos"] = p.groupby("bairro").cumcount()
    out = out[out["_pos"] >= config.MAX_HISTORY_WEEKS].drop(columns="_pos")
    if not keep_last:
        out = out[out["target_casos"].notna()]
    return out.reset_index(drop=True)[["bairro", "week_start"] + feature_columns() + ["target_casos"]]
