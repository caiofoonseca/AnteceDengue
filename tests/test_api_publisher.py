import datetime as dt
import importlib.util
import json
from pathlib import Path

import pytest
import requests

from src import api_publisher as ap
from src.ingest_mqtt import parse_payload
from src.stations import StationConfigError, load_station_coordinates

ROOT = Path(__file__).resolve().parent.parent
TOPIC = "antecedengue/estacoes/recife-001/leituras"
RESPOSTA_ATUAL = {"current": {"time": "2026-11-25T10:15", "interval": 900, "temperature_2m": 28.4,
                              "relative_humidity_2m": 74, "precipitation": 0.3}}
RESPOSTA_HORARIA = {"hourly": {
    "time": ["2026-11-25T08:00", "2026-11-25T09:00", "2026-11-25T10:00", "2026-11-25T11:00"],
    "temperature_2m": [26.0, None, 28.0, 29.0], "relative_humidity_2m": [80, 78, 75, 70],
    "precipitation": [0.0, 0.0, 1.2, 0.0]}}


@pytest.fixture(autouse=True)
def sem_internet(monkeypatch):
    def proibido(*args, **kwargs):
        raise AssertionError("os testes não podem acessar a internet")

    monkeypatch.setattr(requests.Session, "request", proibido)
    monkeypatch.setattr(requests, "get", proibido)


class Resposta:
    def __init__(self, status=200, corpo=None):
        self.status_code = status
        self._corpo = corpo if corpo is not None else RESPOSTA_ATUAL

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._corpo


def test_parse_current_converte_horario_local_de_recife_para_utc():
    obs = ap.parse_current(RESPOSTA_ATUAL)
    assert obs.time_utc == dt.datetime(2026, 11, 25, 13, 15)
    assert (obs.temperature_c, obs.relative_humidity, obs.precipitation_mm) == (28.4, 74.0, 0.3)


@pytest.mark.parametrize("quebra", [
    {},
    {"current": {}},
    {"current": {"time": "2026-11-25T10:15", "temperature_2m": None, "relative_humidity_2m": 70, "precipitation": 0}},
    {"current": {"time": "2026-11-25T10:15", "temperature_2m": "x", "relative_humidity_2m": 70, "precipitation": 0}},
])
def test_parse_current_rejeita_resposta_invalida(quebra):
    with pytest.raises(ValueError):
        ap.parse_current(quebra)


def test_precipitacao_negativa_vira_zero():
    resposta = {"current": dict(RESPOSTA_ATUAL["current"], precipitation=-0.4)}
    assert ap.parse_current(resposta).precipitation_mm == 0.0


def test_parse_hourly_descarta_nulos_e_horas_futuras():
    limite = dt.datetime(2026, 11, 25, 13, 0)
    pontos = ap.parse_hourly(RESPOSTA_HORARIA, limite)
    assert [p.time_utc.hour for p in pontos] == [11, 13]
    assert pontos[1].precipitation_mm == 1.2
    with pytest.raises(ValueError):
        ap.parse_hourly({}, limite)


def test_payload_segue_o_contrato_e_passa_no_parse_do_ingestor():
    quando = dt.datetime(2026, 11, 25, 13, 20, 5)
    payload = ap.make_payload("recife-001", -8.119, -34.9, quando, 28.44, 74.04, 0.3)
    assert set(payload) == {"station_id", "timestamp", "latitude", "longitude", "temperature_c", "relative_humidity",
                            "rainfall_mm", "battery_voltage"}
    assert payload["timestamp"] == "2026-11-25T13:20:05Z"
    assert payload["battery_voltage"] == ap.BATTERY_VOLTAGE_PLACEHOLDER
    registro = parse_payload(TOPIC, json.dumps(payload).encode())
    assert registro["is_valid"] is True and registro["temperature_c"] == 28.4 and registro["rainfall_mm"] == 0.3


def test_params_pedem_current_ou_hourly_com_fuso_de_recife():
    atual = ap.build_params(-8.119, -34.9)
    assert atual["timezone"] == "America/Recife" and "current" in atual and "hourly" not in atual
    historico = ap.build_params(-8.119, -34.9, past_days=500)
    assert historico["past_days"] == ap.MAX_BACKFILL_DAYS and "hourly" in historico and "current" not in historico


def test_fetch_json_tenta_de_novo_com_espera_crescente_e_manda_user_agent():
    chamadas, esperas = [], []

    class Cliente:
        def get(self, url, params, timeout, headers):
            chamadas.append(headers)
            if len(chamadas) < 3:
                raise requests.ConnectionError("fora")
            return Resposta()

    assert ap.fetch_json({}, sleep=esperas.append, session=Cliente()) == RESPOSTA_ATUAL
    assert len(chamadas) == 3 and esperas == [2.0, 4.0]
    assert "AnteceDengue" in chamadas[0]["User-Agent"]


def test_fetch_json_repete_em_5xx_e_desiste_com_apierror():
    chamadas = []

    class Cliente:
        def get(self, *args, **kwargs):
            chamadas.append(1)
            return Resposta(status=503)

    with pytest.raises(ap.ApiError):
        ap.fetch_json({}, retries=3, sleep=lambda s: None, session=Cliente())
    assert len(chamadas) == 3


def test_chuva_conta_cada_bloco_da_api_uma_unica_vez():
    t = ap.RainTracker()
    bloco = dt.datetime(2026, 11, 25, 13, 15)
    assert t.since_last("a", bloco, 0.3) == 0.3
    assert t.since_last("a", bloco, 0.3) == 0.0
    assert t.since_last("b", bloco, 0.3) == 0.3
    assert t.since_last("a", bloco + dt.timedelta(minutes=15), 0.0) == 0.0
    assert t.since_last("a", bloco + dt.timedelta(minutes=30), 1.1) == 1.1
    assert t.since_last("a", bloco + dt.timedelta(minutes=45), -2) == 0.0


def test_cache_chama_a_api_no_maximo_uma_vez_por_minuto_por_estacao():
    chamadas, relogio = [], [0.0]

    def buscar(lat, lon):
        chamadas.append((lat, lon))
        return ap.parse_current(RESPOSTA_ATUAL)

    cache = ap.CurrentCache(buscar, relogio=lambda: relogio[0])
    cache.get("a", 1, 1)
    relogio[0] = 30
    cache.get("a", 1, 1)
    cache.get("b", 2, 2)
    assert len(chamadas) == 2
    relogio[0] = 61
    cache.get("a", 1, 1)
    assert len(chamadas) == 3


def test_poll_pula_a_estacao_quando_a_api_falha_sem_derrubar_o_ciclo(caplog):
    obs = ap.parse_current(RESPOSTA_ATUAL)

    def buscar(lat, lon):
        if lat == 1:
            raise ap.ApiError("fora do ar")
        return obs

    publicados = []
    cache = ap.CurrentCache(buscar, relogio=lambda: 0.0)
    estacoes = {"a": (1.0, 1.0), "b": (2.0, 2.0)}
    with caplog.at_level("WARNING"):
        n = ap.poll_once(publicados.append, estacoes, cache, ap.RainTracker(),
                         lambda: dt.datetime(2026, 11, 25, 13, 20, 0))
    assert n == 1 and [p["station_id"] for p in publicados] == ["b"]
    assert "sem leitura para a" in caplog.text


def test_poll_repetido_no_mesmo_bloco_nao_duplica_a_chuva():
    cache = ap.CurrentCache(lambda lat, lon: ap.parse_current(RESPOSTA_ATUAL), relogio=lambda: 0.0)
    chuva, publicados = ap.RainTracker(), []
    relogio = iter(dt.datetime(2026, 11, 25, 13, 20, s) for s in range(0, 40, 10))
    for _ in range(3):
        ap.poll_once(publicados.append, {"a": (1.0, 1.0)}, cache, chuva, lambda: next(relogio))
    assert [p["rainfall_mm"] for p in publicados] == [0.3, 0.0, 0.0]


def test_backfill_publica_so_pontos_validos_ate_a_hora_atual(monkeypatch):
    monkeypatch.setattr(ap, "fetch_json", lambda params, **kw: RESPOSTA_HORARIA)
    publicados = []

    def agora():
        return dt.datetime(2026, 11, 25, 13, 40, 0)

    total = ap.backfill(publicados.append, {"a": (1.0, 1.0)}, 3, agora)
    assert total == len(publicados) == 2
    assert ap.backfill(publicados.append, {"a": (1.0, 1.0)}, 0, agora) == 0


def test_backfill_com_api_fora_do_ar_nao_levanta(monkeypatch):
    def falha(params, **kw):
        raise ap.ApiError("fora")

    monkeypatch.setattr(ap, "fetch_json", falha)
    assert ap.backfill(lambda p: None, {"a": (1.0, 1.0)}, 3, lambda: dt.datetime(2026, 11, 25, 13, 0)) == 0


def test_estacoes_do_config_tem_coordenadas():
    estacoes = ap.stations_config()
    assert set(estacoes) == {f"recife-{i:03d}" for i in range(1, 9)}
    assert all(-9 < lat < -7 and -36 < lon < -34 for lat, lon in estacoes.values())


def test_coordenadas_ausentes_geram_erro_claro(tmp_path):
    arquivo = tmp_path / "s.json"
    arquivo.write_text(json.dumps({"stations": {"x": "BOA VIAGEM"}, "coordinates": {}}), encoding="utf-8")
    with pytest.raises(StationConfigError, match="x"):
        load_station_coordinates(arquivo)


def carregar_cli():
    spec = importlib.util.spec_from_file_location("sim_publisher_cli", ROOT / "scripts" / "sim_publisher.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_cli_usa_a_api_por_padrao_e_aceita_synthetic(monkeypatch):
    cli = carregar_cli()
    chamadas = {}
    monkeypatch.setattr(cli.api_publisher, "run", lambda *a: chamadas.setdefault("api", a))
    monkeypatch.setattr(cli, "run", lambda *a: chamadas.setdefault("synthetic", a))
    cli.main(["--host", "h", "--max-ao-vivo", "1"])
    assert chamadas["api"] == ("h", 1883, 60.0, 7, 1) and "synthetic" not in chamadas
    cli.main(["--source", "synthetic", "--intervalo", "3"])
    assert chamadas["synthetic"][3] == 3.0


def test_relogio_com_fuso_funciona_no_backfill_e_no_poll(monkeypatch):
    monkeypatch.setattr(ap, "fetch_json", lambda params, **kw: RESPOSTA_HORARIA)
    publicados = []

    def agora():
        return dt.datetime(2026, 11, 25, 13, 40, 0, tzinfo=dt.timezone.utc)

    assert ap.backfill(publicados.append, {"a": (1.0, 1.0)}, 3, agora) == 2
    cache = ap.CurrentCache(lambda lat, lon: ap.parse_current(RESPOSTA_ATUAL), relogio=lambda: 0.0)
    assert ap.poll_once(publicados.append, {"a": (1.0, 1.0)}, cache, ap.RainTracker(), agora) == 1
    assert publicados[-1]["timestamp"] == "2026-11-25T13:40:00Z"


def test_estacoes_apontam_para_bairros_do_painel_com_coordenadas_dentro_do_recife():
    import pandas as pd

    from src import config
    from src.stations import load_station_map

    painel = set(pd.read_csv(config.PANEL_PATH)["bairro"])
    mapa = load_station_map()
    assert len(mapa) == 8 and set(mapa.values()) <= painel and len(set(mapa.values())) == 8
    assert {"BOA VISTA", "CASA FORTE", "IPUTINGA", "PINA", "AFOGADOS", "IBURA"} <= set(mapa.values())
