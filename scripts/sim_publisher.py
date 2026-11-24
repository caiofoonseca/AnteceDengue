"""FERRAMENTA DE DESENVOLVIMENTO: publica leituras SIMULADAS de sensor no Mosquitto.

Os valores são sorteados (SEED 42), não vêm de estação nenhuma. Serve só para demonstrar a infraestrutura
(MQTT, ingestor, banco, API e dashboard). Nunca usar estas leituras em resultado ou relatório.

Uso: python scripts/sim_publisher.py --host mosquitto --backfill-dias 21 --intervalo 5
Publica primeiro um histórico recente (uma leitura a cada 6 h por estação) e depois leituras ao vivo.
Uma leitura em cada 15 sai fora da faixa de propósito, para exercitar a validação do ingestor.
"""
import argparse
import datetime as dt
import json
import logging
import random
import time

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

log = logging.getLogger("sim_publisher")

STATIONS = {"recife-001": (-8.1190, -34.9000), "recife-002": (-8.0460, -34.9340)}
TOPIC = "antecedengue/estacoes/{}/leituras"
INVALID_EVERY = 15


def make_reading(rng: random.Random, station: str, when: dt.datetime, invalid: bool = False) -> dict:
    lat, lon = STATIONS[station]
    reading = {
        "station_id": station, "timestamp": when.strftime("%Y-%m-%dT%H:%M:%SZ"), "latitude": lat, "longitude": lon,
        "temperature_c": round(rng.uniform(24.0, 33.0), 1), "relative_humidity": round(rng.uniform(55.0, 95.0), 1),
        "rainfall_mm": round(rng.choice([0.0, 0.0, 0.0, rng.uniform(0.2, 12.0)]), 1),
        "battery_voltage": round(rng.uniform(3.6, 4.1), 2)}
    if invalid:
        reading["temperature_c"] = 120.0
    return reading


def publish(client: mqtt.Client, reading: dict) -> None:
    info = client.publish(TOPIC.format(reading["station_id"]), json.dumps(reading), qos=1)
    info.wait_for_publish(timeout=10)


def run(host: str, port: int, backfill_days: int, interval: float, max_live: int | None, seed: int) -> None:
    rng = random.Random(seed)
    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="antecedengue-sim-publisher")
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect_async(host, port)
    client.loop_start()
    time.sleep(2)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    sent = 0
    log.warning("DADOS SIMULADOS: estas leituras não vêm de estações reais")
    for hours in range(backfill_days * 24, 0, -6):
        for station in STATIONS:
            sent += 1
            publish(client, make_reading(rng, station, now - dt.timedelta(hours=hours), sent % INVALID_EVERY == 0))
    log.info("histórico simulado publicado: %d leituras", sent)
    live = 0
    while max_live is None or live < max_live:
        for station in STATIONS:
            sent += 1
            publish(client, make_reading(rng, station, dt.datetime.now(dt.timezone.utc).replace(microsecond=0),
                                         sent % INVALID_EVERY == 0))
        live += 1
        log.info("leituras simuladas publicadas até agora: %d", sent)
        time.sleep(interval)
    client.loop_stop()
    client.disconnect()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Publicador de leituras SIMULADAS do AnteceDengue")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--backfill-dias", type=int, default=21)
    parser.add_argument("--intervalo", type=float, default=5.0)
    parser.add_argument("--max-ao-vivo", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(args.host, args.port, args.backfill_dias, args.intervalo, args.max_ao_vivo, args.seed)


if __name__ == "__main__":
    main()
