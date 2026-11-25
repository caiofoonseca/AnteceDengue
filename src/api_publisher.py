"""Estação simulada: publica no MQTT leituras da API pública Open-Meteo, no contrato de payload do projeto.

Não existe sensor físico. A cada ciclo, para cada estação de config/stations_bairros.json, o publicador consulta a
Open-Meteo (temperatura, umidade relativa e precipitação atuais, sem chave) e publica o JSON em
antecedengue/estacoes/<station_id>/leituras (QoS 1). Fluxo: API Open-Meteo -> publicador -> MQTT/Mosquitto ->
ingestor -> Postgres -> sensor_weekly -> API -> dashboard.

Observações de método:
  - Os dados da Open-Meteo vêm de modelos meteorológicos e reanálise; a precipitação é modelada, não medida.
    A API gratuita é só para uso não comercial. Crédito obrigatório: "Weather data by Open-Meteo.com".
  - O timestamp publicado é o instante da consulta (UTC). rainfall_mm é a precipitação do bloco de 15 minutos
    da API, contada UMA vez (nas consultas seguintes ao mesmo bloco vale 0.0), então a soma semanal não duplica.
  - battery_voltage é só um campo do contrato; na simulação não tem sentido físico e vale sempre
    BATTERY_VOLTAGE_PLACEHOLDER.
  - No máximo uma chamada por estação por minuto (MIN_INTERVAL_SECONDS). Se a API falhar, a leitura é pulada.
"""
import datetime as dt
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Callable
from zoneinfo import ZoneInfo

import requests

from src import config
from src.stations import load_station_coordinates, load_station_map

log = logging.getLogger("api_publisher")

API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = config.SENSOR_TIMEZONE
USER_AGENT = os.getenv("OPEN_METEO_USER_AGENT", "AnteceDengue-estacao-simulada/1.0 (projeto academico, CESAR School)")
TOPIC = "antecedengue/estacoes/{}/leituras"
MIN_INTERVAL_SECONDS = 60.0
BATTERY_VOLTAGE_PLACEHOLDER = 4.0
SOURCE_LABEL = "api_open_meteo_via_mqtt"
MAX_BACKFILL_DAYS = 92


class ApiError(RuntimeError):
    pass


@dataclass(frozen=True)
class Observation:
    """Um ponto da API: instante em UTC (ingênuo), temperatura, umidade e precipitação do intervalo."""
    time_utc: dt.datetime
    temperature_c: float
    relative_humidity: float
    precipitation_mm: float


def _number(valor, nome: str) -> float:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(f"campo {nome} ausente ou não numérico: {valor!r}")
    return float(valor)


def _naive_utc(instante: dt.datetime) -> dt.datetime:
    """Datas com fuso viram UTC ingênuo; as ingênuas já são tratadas como UTC."""
    if instante.tzinfo is not None:
        return instante.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return instante


def _local_to_utc(texto: str) -> dt.datetime:
    """'2026-11-25T10:15' (horário local de Recife, como a API devolve com timezone=) -> UTC ingênuo."""
    local = dt.datetime.fromisoformat(texto).replace(tzinfo=ZoneInfo(TIMEZONE))
    return local.astimezone(dt.timezone.utc).replace(tzinfo=None)


def parse_current(resposta: dict) -> Observation:
    """Interpreta o bloco "current" da resposta; levanta ValueError se faltar algo."""
    try:
        atual = resposta["current"]
        return Observation(_local_to_utc(atual["time"]), _number(atual.get("temperature_2m"), "temperature_2m"),
                           _number(atual.get("relative_humidity_2m"), "relative_humidity_2m"),
                           max(0.0, _number(atual.get("precipitation"), "precipitation")))
    except (KeyError, TypeError) as erro:
        raise ValueError(f"resposta inesperada da Open-Meteo: {erro!r}") from erro


def parse_hourly(resposta: dict, ate_utc: dt.datetime) -> list[Observation]:
    """Série horária (past_days): descarta pontos nulos e os posteriores a ate_utc."""
    try:
        bloco = resposta["hourly"]
        tempos, temps = bloco["time"], bloco["temperature_2m"]
        umids, chuvas = bloco["relative_humidity_2m"], bloco["precipitation"]
    except (KeyError, TypeError) as erro:
        raise ValueError(f"resposta horária inesperada da Open-Meteo: {erro!r}") from erro
    itens = []
    for tempo, temp, umid, chuva in zip(tempos, temps, umids, chuvas):
        if temp is None or umid is None or chuva is None:
            continue
        instante = _local_to_utc(tempo)
        if instante <= ate_utc:
            itens.append(Observation(instante, float(temp), float(umid), max(0.0, float(chuva))))
    return itens


def build_params(latitude: float, longitude: float, past_days: int = 0) -> dict:
    params = {"latitude": f"{latitude:.4f}", "longitude": f"{longitude:.4f}", "timezone": TIMEZONE}
    if past_days > 0:
        params.update({"hourly": "temperature_2m,relative_humidity_2m,precipitation", "past_days": min(past_days, MAX_BACKFILL_DAYS),
                       "forecast_days": 1})
    else:
        params["current"] = "temperature_2m,relative_humidity_2m,precipitation"
    return params


def fetch_json(params: dict, timeout: float = 10.0, retries: int = 3, backoff: float = 2.0,
               sleep: Callable[[float], None] = time.sleep, session: requests.Session | None = None) -> dict:
    """GET com timeout e repetição com espera crescente (erros de rede, 429 e 5xx). Levanta ApiError ao desistir."""
    cliente = session or requests
    ultimo = None
    for tentativa in range(retries):
        try:
            resposta = cliente.get(API_URL, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if resposta.status_code == 429 or resposta.status_code >= 500:
                raise requests.HTTPError(f"HTTP {resposta.status_code}")
            resposta.raise_for_status()
            return resposta.json()
        except (requests.RequestException, ValueError) as erro:
            ultimo = erro
            if tentativa < retries - 1:
                sleep(backoff * (2 ** tentativa))
    raise ApiError(f"Open-Meteo indisponível após {retries} tentativas: {ultimo}")


def make_payload(station_id: str, latitude: float, longitude: float, quando_utc: dt.datetime, temperatura: float,
                 umidade: float, chuva_mm: float) -> dict:
    """Payload no contrato do projeto (os mesmos campos do ingestor MQTT)."""
    return {
        "station_id": station_id, "timestamp": quando_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": latitude, "longitude": longitude, "temperature_c": round(temperatura, 1),
        "relative_humidity": round(umidade, 1), "rainfall_mm": round(max(0.0, chuva_mm), 2),
        "battery_voltage": BATTERY_VOLTAGE_PLACEHOLDER}


class RainTracker:
    """Conta a precipitação de cada bloco da API uma única vez por estação (consultas repetidas valem 0.0)."""

    def __init__(self):
        self._ultimo_bloco: dict[str, dt.datetime] = {}

    def since_last(self, estacao: str, bloco: dt.datetime, precipitacao: float) -> float:
        if self._ultimo_bloco.get(estacao) == bloco:
            return 0.0
        self._ultimo_bloco[estacao] = bloco
        return max(0.0, precipitacao)


class CurrentCache:
    """Guarda a última resposta de cada estação e só chama a API de novo depois de MIN_INTERVAL_SECONDS."""

    def __init__(self, buscar: Callable[[float, float], Observation], relogio: Callable[[], float] = time.monotonic,
                 intervalo: float = MIN_INTERVAL_SECONDS):
        self._buscar, self._relogio, self._intervalo = buscar, relogio, intervalo
        self._guardado: dict[str, tuple[float, Observation]] = {}

    def get(self, estacao: str, latitude: float, longitude: float) -> Observation:
        agora = self._relogio()
        if estacao in self._guardado and agora - self._guardado[estacao][0] < self._intervalo:
            return self._guardado[estacao][1]
        observacao = self._buscar(latitude, longitude)
        self._guardado[estacao] = (agora, observacao)
        return observacao


def fetch_current(latitude: float, longitude: float, **kwargs) -> Observation:
    return parse_current(fetch_json(build_params(latitude, longitude), **kwargs))


def stations_config() -> dict[str, tuple[float, float]]:
    """Só as estações que têm bairro E coordenadas no config."""
    coordenadas = load_station_coordinates()
    return {e: coordenadas[e] for e in load_station_map() if e in coordenadas}


def poll_once(publicar: Callable[[dict], None], estacoes: dict[str, tuple[float, float]], cache: CurrentCache,
              chuva: RainTracker, agora: Callable[[], dt.datetime]) -> int:
    """Um ciclo: devolve quantas leituras foram publicadas. Falha da API em uma estação só pula aquela leitura."""
    publicadas = 0
    for estacao, (latitude, longitude) in estacoes.items():
        try:
            obs = cache.get(estacao, latitude, longitude)
        except (ApiError, ValueError) as erro:
            log.warning("sem leitura para %s neste ciclo: %s", estacao, erro)
            continue
        mm = chuva.since_last(estacao, obs.time_utc, obs.precipitation_mm)
        quando = _naive_utc(agora()).replace(microsecond=0)
        publicar(make_payload(estacao, latitude, longitude, quando, obs.temperature_c, obs.relative_humidity, mm))
        publicadas += 1
    return publicadas


def backfill(publicar: Callable[[dict], None], estacoes: dict[str, tuple[float, float]], dias: int,
             agora: Callable[[], dt.datetime], **kwargs) -> int:
    """Histórico recente horário da própria Open-Meteo (past_days), publicado como leituras. Idempotente no banco."""
    if dias <= 0:
        return 0
    limite = _naive_utc(agora()).replace(minute=0, second=0, microsecond=0)
    total = 0
    for estacao, (latitude, longitude) in estacoes.items():
        try:
            resposta = fetch_json(build_params(latitude, longitude, past_days=dias), **kwargs)
            pontos = parse_hourly(resposta, limite)
        except (ApiError, ValueError) as erro:
            log.warning("sem histórico para %s: %s", estacao, erro)
            continue
        for p in pontos:
            publicar(make_payload(estacao, latitude, longitude, p.time_utc, p.temperature_c, p.relative_humidity,
                                  p.precipitation_mm))
            total += 1
    return total


def run(host: str, port: int, interval: float, backfill_days: int, max_live: int | None) -> None:
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion

    estacoes = stations_config()
    if not estacoes:
        raise SystemExit("Nenhuma estação com bairro e coordenadas em config/stations_bairros.json")
    if interval < MIN_INTERVAL_SECONDS:
        log.warning("intervalo %.0fs abaixo do mínimo; usando %.0fs (limite da API gratuita)", interval, MIN_INTERVAL_SECONDS)
        interval = MIN_INTERVAL_SECONDS
    cliente = mqtt.Client(CallbackAPIVersion.VERSION2, client_id="antecedengue-api-publisher")
    cliente.reconnect_delay_set(min_delay=1, max_delay=30)
    cliente.connect_async(host, port)
    cliente.loop_start()
    time.sleep(2)

    def publicar(payload: dict) -> None:
        info = cliente.publish(TOPIC.format(payload["station_id"]), json.dumps(payload), qos=1)
        info.wait_for_publish(timeout=10)

    def agora() -> dt.datetime:
        return dt.datetime.now(dt.timezone.utc)

    log.info("estação simulada: dados da API Open-Meteo (Weather data by Open-Meteo.com); não há sensor físico")
    log.info("histórico publicado: %d leituras", backfill(publicar, estacoes, backfill_days, agora))
    cache, chuva, ciclo, total = CurrentCache(fetch_current), RainTracker(), 0, 0
    while max_live is None or ciclo < max_live:
        total += poll_once(publicar, estacoes, cache, chuva, agora)
        ciclo += 1
        log.info("leituras publicadas até agora: %d", total)
        if max_live is None or ciclo < max_live:
            time.sleep(interval)
    cliente.loop_stop()
    cliente.disconnect()
