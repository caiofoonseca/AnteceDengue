"""Ingestor MQTT: assina antecedengue/estacoes/+/leituras (QoS 1) e grava as leituras no banco.

parse_payload é uma função pura: nunca levanta exceção; leitura inválida vira um registro com
is_valid=False e o motivo em invalid_reason. Payload que não é JSON vai como texto em raw_payload.
As leituras NÃO entram no treino nem na previsão oficial (só dashboard e inferência ao vivo de demonstração).
"""
import argparse
import datetime as dt
import json
import logging
import math
import re
import signal

from src import config
from src.db import get_engine, init_db, insert_reading

log = logging.getLogger("ingest_mqtt")

REQUIRED = ("station_id", "timestamp", "temperature_c", "relative_humidity", "rainfall_mm")
OPTIONAL_NUMBERS = ("latitude", "longitude", "battery_voltage")
UNKNOWN_STATION = "desconhecida"


class _NonFinite(ValueError):
    pass


def _reject_constant(nome: str):
    raise _NonFinite(nome)


def _is_number(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def station_from_topic(topic: str) -> str | None:
    m = re.match(config.MQTT_TOPIC_PATTERN, topic or "")
    return m.group(1) if m else None


def parse_timestamp(texto) -> dt.datetime:
    """ISO 8601 em UTC com sufixo Z; devolve datetime ingênuo em UTC."""
    if not isinstance(texto, str) or not texto.endswith("Z"):
        raise ValueError("deve ser texto ISO 8601 em UTC terminado em Z")
    return dt.datetime.fromisoformat(texto).astimezone(dt.timezone.utc).replace(tzinfo=None)


def parse_payload(topic: str, payload_bytes: bytes) -> dict:
    """Valida uma mensagem e devolve o registro (dict com as colunas de sensor_readings)."""
    station = station_from_topic(topic)
    registro = {k: None for k in ("ts", "latitude", "longitude", "temperature_c", "relative_humidity",
                                  "rainfall_mm", "battery_voltage")}
    registro["station_id"] = station or UNKNOWN_STATION
    motivos = []
    if station is None:
        motivos.append(f"tópico inesperado: {topic}")

    try:
        texto = payload_bytes.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        texto = bytes(payload_bytes or b"").decode("utf-8", errors="replace")
        motivos.append("payload não é UTF-8")
    registro["raw_payload"] = texto

    try:
        dados = json.loads(texto, parse_constant=_reject_constant)
    except _NonFinite as erro:
        return _finish(registro, motivos + [f"valor não finito no JSON: {erro}"])
    except ValueError:
        return _finish(registro, motivos + ["payload não é JSON válido"])
    if not isinstance(dados, dict):
        return _finish(registro, motivos + ["JSON deve ser um objeto"])

    for campo in REQUIRED:
        if campo not in dados or dados[campo] is None:
            motivos.append(f"campo obrigatório ausente: {campo}")

    sid = dados.get("station_id")
    if sid is not None:
        if not isinstance(sid, str):
            motivos.append("station_id deve ser texto")
        elif station is not None and sid != station:
            motivos.append(f"station_id ({sid}) difere do tópico ({station})")

    if dados.get("timestamp") is not None:
        try:
            registro["ts"] = parse_timestamp(dados["timestamp"])
        except (ValueError, TypeError) as erro:
            motivos.append(f"timestamp inválido: {erro}")

    faixas = {"temperature_c": config.TEMP_RANGE, "relative_humidity": config.HUMIDITY_RANGE,
              "rainfall_mm": (0.0, math.inf), "latitude": (-90.0, 90.0), "longitude": (-180.0, 180.0),
              "battery_voltage": (0.0, math.inf)}
    for campo in ("temperature_c", "relative_humidity", "rainfall_mm") + OPTIONAL_NUMBERS:
        valor = dados.get(campo)
        if valor is None:
            continue
        if not _is_number(valor):
            motivos.append(f"{campo} deve ser número, não {type(valor).__name__}")
            continue
        if not math.isfinite(valor):
            motivos.append(f"{campo} não é finito")
            continue
        registro[campo] = float(valor)
        minimo, maximo = faixas[campo]
        if not minimo <= valor <= maximo:
            motivos.append(f"{campo} fora da faixa válida: {valor}")
    return _finish(registro, motivos)


def _finish(registro: dict, motivos: list[str]) -> dict:
    registro["is_valid"] = not motivos
    registro["invalid_reason"] = "; ".join(motivos) if motivos else None
    return registro


def handle_message(engine, topic: str, payload_bytes: bytes) -> str:
    """Processa uma mensagem sem nunca levantar exceção. Devolve inserida, duplicada, invalida ou erro."""
    try:
        registro = parse_payload(topic, payload_bytes)
        inserida = insert_reading(engine, registro)
        if not inserida:
            log.debug("duplicada ignorada: %s %s", registro["station_id"], registro["ts"])
            return "duplicada"
        if registro["is_valid"]:
            log.info("leitura gravada: %s %s", registro["station_id"], registro["ts"])
            return "inserida"
        log.warning("leitura inválida gravada (%s): %s", registro["station_id"], registro["invalid_reason"])
        return "invalida"
    except Exception:
        log.exception("erro ao processar mensagem do tópico %s", topic)
        return "erro"


def build_client(engine, host: str = config.MQTT_HOST, port: int = config.MQTT_PORT,
                 client_id: str = "antecedengue-ingestor"):
    import paho.mqtt.client as mqtt

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, clean_session=False)
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(cli, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            log.error("conexão recusada: %s", reason_code)
            return
        log.info("conectado a %s:%s; assinando %s (QoS 1)", host, port, config.MQTT_TOPIC)
        cli.subscribe(config.MQTT_TOPIC, qos=1)

    def on_disconnect(cli, userdata, flags, reason_code, properties):
        log.warning("desconectado (%s); o cliente tenta reconectar sozinho", reason_code)

    def on_message(cli, userdata, msg):
        handle_message(engine, msg.topic, msg.payload)

    client.on_connect, client.on_disconnect, client.on_message = on_connect, on_disconnect, on_message
    return client


def run(host: str = config.MQTT_HOST, port: int = config.MQTT_PORT, database_url: str | None = None) -> None:
    engine = get_engine(database_url)
    init_db(engine)
    client = build_client(engine, host, port)
    signal.signal(signal.SIGTERM, lambda *_: client.disconnect())
    client.connect_async(host, port)
    try:
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        log.info("encerrando (Ctrl+C)")
    finally:
        client.disconnect()
        engine.dispose()
        log.info("ingestor encerrado")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Ingestor MQTT do AnteceDengue")
    parser.add_argument("--host", default=config.MQTT_HOST)
    parser.add_argument("--port", type=int, default=config.MQTT_PORT)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run(args.host, args.port, args.database_url)


if __name__ == "__main__":
    main()
