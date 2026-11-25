"""Exporta a agregação semanal da estação simulada (sensor_weekly, no Postgres) para data/processed/sensor_semanal.csv.

Fluxo: API Open-Meteo -> publicador -> MQTT/Mosquitto -> ingestor -> Postgres -> sensor_weekly -> este CSV.
Colunas: bairro, semana_inicio (domingo, America/Recife), temp_media, umid_media, chuva_mm_soma, n_leituras, fonte.
A semana corrente pode estar parcial (n_leituras mostra quantas leituras entraram). Este CSV NÃO entra no
treino do modelo (o histórico é de poucas semanas); serve à ingestão, ao dashboard e à inferência recente.
Dados da Open-Meteo (Weather data by Open-Meteo.com): precipitação modelada, não medida; API só para uso não comercial.
A escrita é atômica (arquivo temporário e rename) e determinística: rodar duas vezes gera o mesmo arquivo.
"""
import argparse
import logging
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.engine import Engine

from src import config
from src.db import get_engine, init_db, sensor_weekly

log = logging.getLogger("export_sensor_csv")

OUTPUT_PATH = config.DATA_PROCESSED / "sensor_semanal.csv"
SOURCE_LABEL = "api_open_meteo_via_mqtt"
COLUMNS = ["bairro", "semana_inicio", "temp_media", "umid_media", "chuva_mm_soma", "n_leituras", "fonte"]


def weekly_frame(engine: Engine, fonte: str = SOURCE_LABEL) -> pd.DataFrame:
    with engine.connect() as conn:
        bruto = pd.read_sql(select(sensor_weekly).order_by(sensor_weekly.c.bairro, sensor_weekly.c.week_start), conn)
    if bruto.empty:
        return pd.DataFrame(columns=COLUMNS)
    saida = pd.DataFrame({
        "bairro": bruto["bairro"], "semana_inicio": pd.to_datetime(bruto["week_start"]).dt.strftime("%Y-%m-%d"),
        "temp_media": bruto["temp_media"].round(2), "umid_media": bruto["umid_media"].round(2),
        "chuva_mm_soma": bruto["chuva_mm"].round(2), "n_leituras": bruto["n_leituras"].astype(int), "fonte": fonte})
    return saida.sort_values(["bairro", "semana_inicio"]).reset_index(drop=True)[COLUMNS]


def export_sensor_csv(engine: Engine, output: Path = OUTPUT_PATH, fonte: str = SOURCE_LABEL) -> int:
    """Grava o CSV e devolve o número de linhas de dados. Banco vazio gera só o cabeçalho (com aviso no log)."""
    frame = weekly_frame(engine, fonte)
    if frame.empty:
        log.warning("sensor_weekly está vazia: gerando %s só com o cabeçalho", Path(output).name)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporario = output.with_name(output.name + ".tmp")
    frame.to_csv(temporario, index=False, lineterminator="\n")
    os.replace(temporario, output)
    log.info("%d linhas gravadas em %s", len(frame), output)
    return len(frame)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Exporta sensor_weekly para data/processed/sensor_semanal.csv")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    engine = get_engine()
    init_db(engine)
    return export_sensor_csv(engine, Path(args.output))


if __name__ == "__main__":
    main()
