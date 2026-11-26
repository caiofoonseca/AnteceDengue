"""Inferência ao vivo (DEMONSTRAÇÃO): o modelo consome o clima da estação simulada (python -m src.predict_live).

Fluxo: leituras da estação simulada (API Open-Meteo -> MQTT -> Postgres -> sensor_weekly) viram uma série
semanal do município; dela saem as features de clima do modelo (lags 1/2/4/8 de temperatura e umidade e chuva
acumulada 2/4/8); as features de casos vêm da última semana do painel real (hoje PANEL_END); o champion prevê
a classe de risco e o risk_score.

Limitações (por isso é só demonstração do pipeline, não previsão operacional):
- Os casos têm atraso e param em PANEL_END, então a semana base dos casos NÃO é a semana do clima.
- O clima do treino é InfoDengue + ERA5 (reanálise); o da estação é Open-Meteo em ponto, em escala diferente
  (a chuva, em especial). O modelo nunca foi treinado nem avaliado com esses dados.
- Só semanas completas (domingo a sábado, fuso de Recife) entram; o clima do município é a média das estações,
  e a chuva é a média, entre estações, da soma semanal.
O resultado vai para data/processed/predictions_live.csv e para a tabela predictions_live. NÃO substitui
predictions_latest.csv (inferência em lote), que continua sendo a previsão oficial do projeto.
"""
import argparse
import datetime as dt

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from src import config
from src.db import get_engine, init_db, save_live_predictions, sensor_weekly
from src.features import climate_features, load_inputs
from src.predict_batch import (OUTPUT_COLUMNS, check_sklearn_version, latest_features, load_meta, load_model,
                               select_features)
from src.reporting import predict_proba_full

CLIMATE_FEATURE_PREFIXES = ("temp_media_lag", "umid_media_lag", "chuva_acum")
LIVE_OUTPUT_COLUMNS = OUTPUT_COLUMNS + ["semana_clima", "n_semanas_clima"]
MIN_WEEKS = max(config.CLIMATE_LAGS) + 1


class LiveClimateUnavailable(RuntimeError):
    pass


def weekly_city_climate(sensor: pd.DataFrame, now: dt.datetime | None = None) -> pd.DataFrame:
    """Série semanal do município (week_start, temp_media, umid_media, chuva_mm) só com semanas completas.

    sensor: linhas de sensor_weekly (bairro, week_start, temp_media, umid_media, chuva_mm, n_leituras).
    Temperatura e umidade: média ponderada pelo número de leituras. Chuva: média entre bairros da soma semanal.
    Semanas sem nenhuma leitura entram como nulas, para os lags não encostarem semanas distantes.
    """
    if sensor.empty:
        raise LiveClimateUnavailable("sensor_weekly está vazio: suba a estação simulada e rode python -m src.sensor_agg.")
    agora = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz=config.SENSOR_TIMEZONE).tz_localize(None)
    df = sensor.copy()
    df["week_start"] = pd.to_datetime(df["week_start"])
    df = df[df["week_start"] + pd.Timedelta(days=7) <= agora.normalize()]
    if df.empty:
        raise LiveClimateUnavailable("ainda não há nenhuma semana completa (domingo a sábado) de leituras da estação.")
    peso = df["n_leituras"].astype(float)
    df = df.assign(_t=df["temp_media"] * peso, _u=df["umid_media"] * peso)
    por_semana = df.groupby("week_start").agg(_t=("_t", "sum"), _u=("_u", "sum"), peso=("n_leituras", "sum"),
                                              chuva_mm=("chuva_mm", "mean"))
    por_semana["temp_media"] = por_semana["_t"] / por_semana["peso"]
    por_semana["umid_media"] = por_semana["_u"] / por_semana["peso"]
    completo = pd.date_range(por_semana.index.min(), por_semana.index.max(), freq="7D")
    serie = por_semana.reindex(completo)[["temp_media", "umid_media", "chuva_mm"]]
    serie.index.name = "week_start"
    return serie.reset_index()


def live_climate_values(city_climate: pd.DataFrame) -> tuple[dict[str, float], pd.Timestamp, int]:
    """Features de clima da última semana completa da série, a semana usada e quantas semanas existem."""
    feats = climate_features(city_climate)
    ultima = feats.iloc[-1]
    colunas = [c for c in feats.columns if c.startswith(CLIMATE_FEATURE_PREFIXES)]
    return {c: ultima[c] for c in colunas}, pd.Timestamp(ultima["week_start"]), len(city_climate)


def predict_live(model, meta: dict, panel: pd.DataFrame, clima_historico: pd.DataFrame,
                 city_climate: pd.DataFrame) -> pd.DataFrame:
    """Casos da última semana do painel + clima da estação simulada -> previsão por bairro."""
    features = meta["features"]
    base = latest_features(panel, clima_historico, features)
    valores, semana_clima, n_semanas = live_climate_values(city_climate)
    for coluna, valor in valores.items():
        if coluna in base.columns:
            base[coluna] = valor
    X = select_features(base, features)
    proba = predict_proba_full(model, X)
    classe = proba.argmax(axis=1)
    out = pd.DataFrame({
        "bairro": base["bairro"], "week_start": base["week_start"],
        "target_week": base["week_start"] + pd.Timedelta(weeks=1),
        "classe_prevista": classe, "rotulo_previsto": [config.CLASSES[c] for c in classe],
        "prob_baixo": proba[:, 0], "prob_medio": proba[:, 1], "prob_alto": proba[:, 2],
    })
    out["risk_score"] = 50 * out["prob_medio"] + 100 * out["prob_alto"]
    ordem = out.sort_values(["risk_score", "prob_alto", "bairro"], ascending=[False, False, True]).index
    out["rank"] = pd.Series(np.arange(1, len(out) + 1), index=ordem)
    out["semana_clima"] = semana_clima
    out["n_semanas_clima"] = n_semanas
    return out.sort_values("rank").reset_index(drop=True)[LIVE_OUTPUT_COLUMNS]


def read_sensor_weekly(engine: Engine) -> pd.DataFrame:
    init_db(engine)
    with engine.connect() as conn:
        linhas = conn.execute(select(sensor_weekly)).mappings().all()
    return pd.DataFrame([dict(l) for l in linhas])


def run(output_path=config.LIVE_PREDICTIONS_PATH, database_url: str | None = None, use_registry: bool = True,
        now: dt.datetime | None = None, write_db: bool = True) -> pd.DataFrame:
    meta = load_meta()
    check_sklearn_version(meta)
    model, origem = load_model(use_registry=use_registry)
    panel, clima = load_inputs()
    engine = get_engine(database_url)
    try:
        sensor = read_sensor_weekly(engine)
        serie = weekly_city_climate(sensor, now)
        out = predict_live(model, meta, panel, clima, serie)
        if write_db:
            save_live_predictions(engine, out)
    finally:
        engine.dispose()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    n_alto = int((out["classe_prevista"] == 2).sum())
    print("DEMONSTRAÇÃO: casos do painel real + clima da estação simulada (Open-Meteo); não é previsão operacional.")
    print(f"Modelo: {meta['model_name']} (origem: {origem})")
    print(f"Semana base dos casos = {out['week_start'].iloc[0].date()}; clima da estação até a semana "
          f"{out['semana_clima'].iloc[0].date()} ({out['n_semanas_clima'].iloc[0]} semanas completas)")
    print(f"{len(out)} bairros gravados em {output_path}; classe alto em {n_alto}")
    return out


def main(argv=None) -> pd.DataFrame:
    parser = argparse.ArgumentParser(description="Inferência ao vivo (demonstração) com o clima da estação simulada")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--no-registry", action="store_true", help="usa só models/best_model.joblib")
    parser.add_argument("--sem-banco", action="store_true", help="não grava a tabela predictions_live")
    args = parser.parse_args(argv)
    return run(database_url=args.database_url, use_registry=not args.no_registry, write_db=not args.sem_banco)


if __name__ == "__main__":
    main()
