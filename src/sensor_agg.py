"""Agregação semanal das leituras VÁLIDAS do sensor por bairro (python -m src.sensor_agg).

A semana é calculada no fuso America/Recife (domingo a sábado), embora o timestamp chegue em UTC.
Por (bairro, semana): temperatura média, umidade média, chuva total (soma de rainfall_mm), número de
leituras e menor tensão de bateria. Idempotente: as semanas afetadas são apagadas e recalculadas.
Estações sem bairro em config/stations_bairros.json são ignoradas com aviso.
As leituras do sensor NÃO alimentam o modelo.
"""
import argparse
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, insert, select
from sqlalchemy.engine import Engine

from src import config
from src.db import get_engine, init_db, sensor_readings, sensor_weekly
from src.stations import load_station_map, panel_bairros, validate_station_map

log = logging.getLogger("sensor_agg")

WEEKLY_COLUMNS = ["bairro", "week_start", "temp_media", "umid_media", "chuva_mm", "n_leituras", "bateria_min"]


def week_start_recife(ts_utc: pd.Series) -> pd.Series:
    """Domingo (data local de Recife) da semana de cada timestamp UTC ingênuo."""
    local = ts_utc.dt.tz_localize("UTC").dt.tz_convert(config.SENSOR_TIMEZONE).dt.tz_localize(None)
    dias_desde_domingo = (local.dt.weekday + 1) % 7
    return (local.dt.normalize() - pd.to_timedelta(dias_desde_domingo, unit="D")).dt.date


def aggregate_weekly(readings: pd.DataFrame, station_map: dict[str, str]) -> pd.DataFrame:
    """readings: leituras válidas (station_id, ts, temperature_c, relative_humidity, rainfall_mm, battery_voltage)."""
    if readings.empty:
        return pd.DataFrame(columns=WEEKLY_COLUMNS)
    df = readings.copy()
    df["bairro"] = df["station_id"].map(station_map)
    for estacao in sorted(df.loc[df["bairro"].isna(), "station_id"].unique()):
        log.warning("estação %s sem bairro mapeado em %s: leituras ignoradas", estacao, config.STATIONS_PATH.name)
    df = df[df["bairro"].notna()]
    if df.empty:
        return pd.DataFrame(columns=WEEKLY_COLUMNS)
    df["week_start"] = week_start_recife(pd.to_datetime(df["ts"]))
    out = df.groupby(["bairro", "week_start"], as_index=False).agg(
        temp_media=("temperature_c", "mean"), umid_media=("relative_humidity", "mean"),
        chuva_mm=("rainfall_mm", "sum"), n_leituras=("ts", "size"), bateria_min=("battery_voltage", "min"))
    return out[WEEKLY_COLUMNS]


def run(engine: Engine, station_map: dict[str, str]) -> pd.DataFrame:
    """Recalcula sensor_weekly a partir das leituras válidas; devolve as linhas gravadas."""
    init_db(engine)
    consulta = select(sensor_readings).where(sensor_readings.c.is_valid.is_(True), sensor_readings.c.ts.is_not(None))
    with engine.connect() as conn:
        leituras = pd.DataFrame(conn.execute(consulta).mappings().all())
    semanal = aggregate_weekly(leituras, station_map)
    registros = semanal.astype(object).where(semanal.notna(), None).to_dict("records")
    with engine.begin() as conn:
        for r in registros:
            conn.execute(delete(sensor_weekly).where(sensor_weekly.c.bairro == r["bairro"],
                                                     sensor_weekly.c.week_start == r["week_start"]))
        if registros:
            conn.execute(insert(sensor_weekly), registros)
    log.info("%d semanas de bairro gravadas em sensor_weekly", len(semanal))
    return semanal


def main(argv=None) -> pd.DataFrame:
    parser = argparse.ArgumentParser(description="Agregação semanal do sensor por bairro")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--stations", type=Path, default=config.STATIONS_PATH)
    parser.add_argument("--sem-validar-bairros", action="store_true", help="não confere os bairros contra o painel")
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    mapa = load_station_map(args.stations)
    if not args.sem_validar_bairros:
        validate_station_map(mapa, panel_bairros())
    semanal = run(get_engine(args.database_url), mapa)
    print(semanal.round(3).to_string(index=False))
    return semanal


if __name__ == "__main__":
    main()
