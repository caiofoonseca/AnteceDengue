"""Banco do sensor (SQLAlchemy 2.x): leituras brutas e agregação semanal por bairro.

DATABASE_URL vem de src/config.py (Postgres em produção; SQLite nos testes). Os horários são
guardados em UTC, sem fuso no banco (datetime ingênuo que representa UTC).

A restrição única (station_id, ts) torna idempotente o reenvio de mensagens (QoS 1 pode duplicar):
inserir de novo não duplica nem gera erro, e a primeira gravação prevalece. Leituras inválidas sem
timestamp reconhecível (ts nulo) não entram nessa deduplicação.
"""
import datetime as dt

import pandas as pd
from sqlalchemy import (Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text,
                        UniqueConstraint, create_engine, delete, insert, select)
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Engine

from src import config

metadata = MetaData()

sensor_readings = Table(
    "sensor_readings", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("station_id", String(100), nullable=False),
    Column("ts", DateTime, nullable=True),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("temperature_c", Float),
    Column("relative_humidity", Float),
    Column("rainfall_mm", Float),
    Column("battery_voltage", Float),
    Column("is_valid", Boolean, nullable=False),
    Column("invalid_reason", Text),
    Column("received_at", DateTime, nullable=False),
    Column("raw_payload", Text),
    UniqueConstraint("station_id", "ts", name="uq_sensor_readings_station_ts"),
)

sensor_weekly = Table(
    "sensor_weekly", metadata,
    Column("bairro", String(100), primary_key=True),
    Column("week_start", Date, primary_key=True),
    Column("temp_media", Float),
    Column("umid_media", Float),
    Column("chuva_mm", Float),
    Column("n_leituras", Integer, nullable=False),
    Column("bateria_min", Float),
)

predictions = Table(
    "predictions", metadata,
    Column("bairro", String(100), primary_key=True),
    Column("week_start", Date, primary_key=True),
    Column("target_week", Date, nullable=False),
    Column("classe_prevista", Integer, nullable=False),
    Column("rotulo_previsto", String(10), nullable=False),
    Column("prob_baixo", Float, nullable=False),
    Column("prob_medio", Float, nullable=False),
    Column("prob_alto", Float, nullable=False),
    Column("risk_score", Float, nullable=False),
    Column("rank", Integer, nullable=False),
    Column("generated_at", DateTime, nullable=False),
)

PREDICTION_COLUMNS = ("bairro", "week_start", "target_week", "classe_prevista", "rotulo_previsto", "prob_baixo",
                      "prob_medio", "prob_alto", "risk_score", "rank")

predictions_live = Table(
    "predictions_live", metadata,
    Column("bairro", String(100), primary_key=True),
    Column("week_start", Date, primary_key=True),
    Column("target_week", Date, nullable=False),
    Column("classe_prevista", Integer, nullable=False),
    Column("rotulo_previsto", String(10), nullable=False),
    Column("prob_baixo", Float, nullable=False),
    Column("prob_medio", Float, nullable=False),
    Column("prob_alto", Float, nullable=False),
    Column("risk_score", Float, nullable=False),
    Column("rank", Integer, nullable=False),
    Column("semana_clima", Date, nullable=False),
    Column("n_semanas_clima", Integer, nullable=False),
    Column("generated_at", DateTime, nullable=False),
)

LIVE_COLUMNS = PREDICTION_COLUMNS + ("semana_clima", "n_semanas_clima")

READING_COLUMNS = ("station_id", "ts", "latitude", "longitude", "temperature_c", "relative_humidity",
                   "rainfall_mm", "battery_voltage", "is_valid", "invalid_reason", "raw_payload")


def normalize_database_url(url: str) -> str:
    """postgresql:// vira postgresql+psycopg2:// (o SQLAlchemy 2.1 usaria psycopg 3 por padrão)."""
    if url.startswith("postgresql://"):
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_engine(url: str | None = None) -> Engine:
    return create_engine(normalize_database_url(url or config.DATABASE_URL), future=True)


def init_db(engine: Engine) -> None:
    metadata.create_all(engine)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _insert_ignoring_duplicates(engine: Engine, values: dict):
    nome = engine.dialect.name
    if nome == "postgresql":
        return postgresql.insert(sensor_readings).values(**values).on_conflict_do_nothing(
            index_elements=["station_id", "ts"])
    if nome == "sqlite":
        return sqlite.insert(sensor_readings).values(**values).on_conflict_do_nothing(
            index_elements=["station_id", "ts"])
    raise NotImplementedError(f"dialeto sem suporte: {nome}")


def insert_reading(engine: Engine, reading: dict, received_at: dt.datetime | None = None) -> bool:
    """Grava uma leitura. Devolve True se inseriu e False se já existia (station_id, ts)."""
    valores = {k: reading.get(k) for k in READING_COLUMNS}
    valores["received_at"] = received_at or utcnow()
    with engine.begin() as conn:
        resultado = conn.execute(_insert_ignoring_duplicates(engine, valores))
    return resultado.rowcount == 1


def save_predictions(engine: Engine, frame: pd.DataFrame, generated_at: dt.datetime | None = None) -> int:
    """Grava as previsões em lote; reexecutar para a mesma semana base substitui as linhas (idempotente)."""
    registros = []
    agora = generated_at or utcnow()
    for linha in frame[list(PREDICTION_COLUMNS)].to_dict("records"):
        linha["week_start"] = pd.Timestamp(linha["week_start"]).date()
        linha["target_week"] = pd.Timestamp(linha["target_week"]).date()
        for coluna in ("classe_prevista", "rank"):
            linha[coluna] = int(linha[coluna])
        for coluna in ("prob_baixo", "prob_medio", "prob_alto", "risk_score"):
            linha[coluna] = float(linha[coluna])
        registros.append({**linha, "generated_at": agora})
    semanas = {r["week_start"] for r in registros}
    with engine.begin() as conn:
        conn.execute(delete(predictions).where(predictions.c.week_start.in_(semanas)))
        if registros:
            conn.execute(insert(predictions), registros)
    return len(registros)


def load_latest_predictions(engine: Engine) -> pd.DataFrame:
    """Previsões da semana base mais recente gravada no banco, ordenadas por rank (vazio se não houver)."""
    with engine.connect() as conn:
        ultima = conn.execute(select(predictions.c.week_start).order_by(predictions.c.week_start.desc()).limit(1)).scalar()
        if ultima is None:
            return pd.DataFrame(columns=list(PREDICTION_COLUMNS))
        linhas = conn.execute(select(*[predictions.c[c] for c in PREDICTION_COLUMNS]).where(
            predictions.c.week_start == ultima).order_by(predictions.c["rank"])).mappings().all()
    return pd.DataFrame([dict(l) for l in linhas], columns=list(PREDICTION_COLUMNS))


def save_live_predictions(engine: Engine, frame: pd.DataFrame, generated_at: dt.datetime | None = None) -> int:
    """Grava a inferência ao vivo; a tabela guarda só a execução mais recente (reexecutar substitui tudo)."""
    agora = generated_at or utcnow()
    registros = []
    for linha in frame[list(LIVE_COLUMNS)].to_dict("records"):
        for coluna in ("week_start", "target_week", "semana_clima"):
            linha[coluna] = pd.Timestamp(linha[coluna]).date()
        for coluna in ("classe_prevista", "rank", "n_semanas_clima"):
            linha[coluna] = int(linha[coluna])
        for coluna in ("prob_baixo", "prob_medio", "prob_alto", "risk_score"):
            linha[coluna] = float(linha[coluna])
        registros.append({**linha, "generated_at": agora})
    with engine.begin() as conn:
        conn.execute(delete(predictions_live))
        if registros:
            conn.execute(insert(predictions_live), registros)
    return len(registros)


def load_live_predictions(engine: Engine) -> pd.DataFrame:
    """Última inferência ao vivo gravada, ordenada por rank (vazio se não houver)."""
    with engine.connect() as conn:
        linhas = conn.execute(select(*[predictions_live.c[c] for c in LIVE_COLUMNS]).order_by(
            predictions_live.c["rank"])).mappings().all()
    return pd.DataFrame([dict(l) for l in linhas], columns=list(LIVE_COLUMNS))
