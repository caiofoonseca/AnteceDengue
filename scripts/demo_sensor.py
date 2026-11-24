"""Demonstração sem broker: mensagens válidas, inválidas e duplicadas entram num SQLite em memória
e a agregação semanal é calculada. Uso: python scripts/demo_sensor.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from sqlalchemy import create_engine, select

from src.db import init_db, sensor_readings
from src.ingest_mqtt import handle_message
from src.sensor_agg import run

pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 60)
TOPIC = "antecedengue/estacoes/recife-001/leituras"


def msg(**mudancas):
    base = {"station_id": "recife-001", "timestamp": "2025-03-03T12:00:00Z", "latitude": -8.12, "longitude": -34.9,
            "temperature_c": 28.5, "relative_humidity": 75.0, "rainfall_mm": 1.2, "battery_voltage": 3.9}
    base.update(mudancas)
    return json.dumps(base).encode()


mensagens = [
    ("válida (sábado 23:30 em Recife = domingo 02:30Z)", TOPIC, msg(timestamp="2025-03-02T02:30:00Z", rainfall_mm=2.0)),
    ("válida (quarta anterior)", TOPIC, msg(timestamp="2025-02-26T15:00:00Z", temperature_c=26, rainfall_mm=1.5)),
    ("válida (domingo 00:30 em Recife)", TOPIC, msg(timestamp="2025-03-02T03:30:00Z", rainfall_mm=4.0, battery_voltage=3.7)),
    ("duplicada da anterior (QoS 1)", TOPIC, msg(timestamp="2025-03-02T03:30:00Z", rainfall_mm=4.0, battery_voltage=3.7)),
    ("inválida: temperatura 120", TOPIC, msg(timestamp="2025-03-04T12:00:00Z", temperature_c=120)),
    ("inválida: umidade como texto", TOPIC, msg(timestamp="2025-03-05T12:00:00Z", relative_humidity="75")),
    ("inválida: timestamp sem Z", TOPIC, msg(timestamp="2025-03-06T12:00:00")),
    ("inválida: station_id diferente do tópico", TOPIC, msg(station_id="outra", timestamp="2025-03-07T12:00:00Z")),
    ("inválida: NaN", TOPIC, b'{"station_id": "recife-001", "timestamp": "2025-03-08T12:00:00Z", "temperature_c": NaN, "relative_humidity": 70, "rainfall_mm": 0}'),
    ("inválida: não é JSON", TOPIC, b"isto nao e json"),
    ("estação sem bairro (ignorada na agregação)", "antecedengue/estacoes/sem-bairro/leituras",
     msg(station_id="sem-bairro", timestamp="2025-03-03T12:00:00Z")),
]

engine = create_engine("sqlite://")
init_db(engine)
print("== Mensagens recebidas ==")
for descricao, topic, corpo in mensagens:
    print(f"{handle_message(engine, topic, corpo):10s} {descricao}")

with engine.connect() as conn:
    tabela = pd.DataFrame(conn.execute(select(sensor_readings)).mappings().all())
print("\n== sensor_readings ==")
print(tabela[["station_id", "ts", "temperature_c", "rainfall_mm", "is_valid", "invalid_reason"]].to_string(index=False))
print(f"\nlinhas: {len(tabela)} | válidas: {int(tabela['is_valid'].sum())} | inválidas: {int((~tabela['is_valid'].astype(bool)).sum())}")

print("\n== sensor_weekly (America/Recife, domingo a sábado) ==")
print(run(engine, {"recife-001": "BOA VIAGEM"}).round(2).to_string(index=False))
