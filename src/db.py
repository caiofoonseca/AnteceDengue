"""Banco do sensor (SQLAlchemy 2.x): leituras brutas e agregação semanal por bairro.

DATABASE_URL vem de src/config.py (Postgres em produção; SQLite nos testes). Os horários são
guardados em UTC, sem fuso no banco (datetime ingênuo que representa UTC).

A restrição única (station_id, ts) torna idempotente o reenvio de mensagens (QoS 1 pode duplicar):
inserir de novo não duplica nem gera erro, e a primeira gravação prevalece. Leituras inválidas sem
timestamp reconhecível (ts nulo) não entram nessa deduplicação.
"""
import datetime as dt

from sqlalchemy import (Boolean, Column, Date, DateTime, Float, Integer, MetaData, String, Table, Text,
                        UniqueConstraint, create_engine)
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

READING_COLUMNS = ("station_id", "ts", "latitude", "longitude", "temperature_c", "relative_humidity",
                   "rainfall_mm", "battery_voltage", "is_valid", "invalid_reason", "raw_payload")


def get_engine(url: str | None = None) -> Engine:
    return create_engine(url or config.DATABASE_URL, future=True)


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
