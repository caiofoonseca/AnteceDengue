import json
import logging
import socket
import time

import pandas as pd
import pytest
from sqlalchemy import create_engine, func, select

from src import config
from src.db import init_db, insert_reading, sensor_readings, sensor_weekly
from src.ingest_mqtt import build_client, handle_message, parse_payload
from src.sensor_agg import aggregate_weekly, run as run_agg, week_start_recife
from src.stations import StationConfigError, load_station_map, panel_bairros, validate_station_map

TOPIC = "antecedengue/estacoes/recife-001/leituras"
MAPA = {"recife-001": "BOA VIAGEM", "recife-002": "VARZEA"}


def payload(**mudancas):
    base = {"station_id": "recife-001", "timestamp": "2025-03-03T12:00:00Z", "latitude": -8.12, "longitude": -34.9,
            "temperature_c": 28.5, "relative_humidity": 75.0, "rainfall_mm": 1.2, "battery_voltage": 3.9}
    base.update(mudancas)
    return {k: v for k, v in base.items() if v is not None}


def enviar(dados, topic=TOPIC):
    return json.dumps(dados).encode("utf-8"), topic


@pytest.fixture
def engine():
    eng = create_engine("sqlite://")
    init_db(eng)
    return eng


def test_payload_valido():
    r = parse_payload(TOPIC, json.dumps(payload()).encode())
    assert r["is_valid"] is True and r["invalid_reason"] is None
    assert r["station_id"] == "recife-001"
    assert r["ts"].isoformat() == "2025-03-03T12:00:00"
    assert r["temperature_c"] == 28.5 and r["rainfall_mm"] == 1.2


def test_limites_das_faixas_sao_validos():
    for temp, umid, chuva in ((-10, 0, 0), (60, 100, 0), (25, 50, 1000)):
        corpo = json.dumps(payload(temperature_c=temp, relative_humidity=umid, rainfall_mm=chuva)).encode()
        assert parse_payload(TOPIC, corpo)["is_valid"] is True


@pytest.mark.parametrize("mudanca,trecho", [
    ({"temperature_c": 60.1}, "temperature_c fora da faixa"),
    ({"temperature_c": -10.1}, "temperature_c fora da faixa"),
    ({"relative_humidity": 100.5}, "relative_humidity fora da faixa"),
    ({"relative_humidity": -1}, "relative_humidity fora da faixa"),
    ({"rainfall_mm": -0.1}, "rainfall_mm fora da faixa"),
    ({"temperature_c": "28.5"}, "temperature_c deve ser número"),
    ({"relative_humidity": "75"}, "relative_humidity deve ser número"),
    ({"rainfall_mm": True}, "rainfall_mm deve ser número"),
    ({"temperature_c": 1e999}, "não é finito"),
    ({"timestamp": "2025-03-03T12:00:00"}, "timestamp inválido"),
    ({"timestamp": "2025-03-03T12:00:00+00:00"}, "timestamp inválido"),
    ({"timestamp": "2025-03-03T09:00:00-03:00"}, "timestamp inválido"),
    ({"timestamp": "ontem"}, "timestamp inválido"),
    ({"timestamp": 1741000000}, "timestamp inválido"),
    ({"station_id": "recife-999"}, "difere do tópico"),
    ({"station_id": 7}, "station_id deve ser texto"),
    ({"temperature_c": None}, "campo obrigatório ausente: temperature_c"),
    ({"timestamp": None}, "campo obrigatório ausente: timestamp"),
    ({"station_id": None}, "campo obrigatório ausente: station_id"),
    ({"battery_voltage": "3.9"}, "battery_voltage deve ser número"),
])
def test_payload_invalido_com_motivo(mudanca, trecho):
    corpo = json.dumps(payload(**mudanca)).encode()
    if mudanca.get("temperature_c") == 1e999:
        corpo = corpo.replace(b"Infinity", b"1e999")
    r = parse_payload(TOPIC, corpo)
    assert r["is_valid"] is False
    assert trecho in r["invalid_reason"]


@pytest.mark.parametrize("bruto,trecho", [
    (b'{"station_id": "recife-001", "timestamp": "2025-03-03T12:00:00Z", "temperature_c": NaN, '
     b'"relative_humidity": 70, "rainfall_mm": 0}', "não finito"),
    (b'{"station_id": "recife-001", "timestamp": "2025-03-03T12:00:00Z", "temperature_c": 20, '
     b'"relative_humidity": Infinity, "rainfall_mm": 0}', "não finito"),
    (b'{"temperature_c": -Infinity}', "não finito"),
    (b"isto nao e json", "não é JSON válido"),
    (b"", "não é JSON válido"),
    (b'{"station_id": ', "não é JSON válido"),
    (b"[1, 2, 3]", "deve ser um objeto"),
    (b'"texto"', "deve ser um objeto"),
    (b"\xff\xfe\x00", "não é UTF-8"),
    (b"{}", "campo obrigatório ausente"),
])
def test_payload_malformado(bruto, trecho):
    r = parse_payload(TOPIC, bruto)
    assert r["is_valid"] is False
    assert trecho in r["invalid_reason"]
    assert isinstance(r["raw_payload"], str)


def test_topico_inesperado_e_invalido():
    r = parse_payload("outro/topico", json.dumps(payload()).encode())
    assert r["is_valid"] is False and "tópico inesperado" in r["invalid_reason"]


def test_motivos_acumulam():
    r = parse_payload(TOPIC, json.dumps(payload(temperature_c=99, relative_humidity=500)).encode())
    assert "temperature_c" in r["invalid_reason"] and "relative_humidity" in r["invalid_reason"]


def test_insercao_idempotente(engine):
    corpo, topic = enviar(payload())
    assert handle_message(engine, topic, corpo) == "inserida"
    assert handle_message(engine, topic, corpo) == "duplicada"
    assert handle_message(engine, topic, corpo) == "duplicada"
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(sensor_readings)).scalar() == 1


def test_insert_reading_devolve_se_inseriu(engine):
    registro = parse_payload(TOPIC, json.dumps(payload()).encode())
    assert insert_reading(engine, registro) is True
    assert insert_reading(engine, registro) is False


def test_leitura_invalida_e_gravada_com_motivo(engine, caplog):
    corpo, topic = enviar(payload(temperature_c=120, timestamp="2025-03-03T13:00:00Z"))
    with caplog.at_level(logging.WARNING, logger="ingest_mqtt"):
        assert handle_message(engine, topic, corpo) == "invalida"
    assert any("inválida" in m for m in caplog.messages)
    with engine.connect() as conn:
        linha = conn.execute(select(sensor_readings)).mappings().one()
    assert linha["is_valid"] == 0 and "temperature_c fora da faixa" in linha["invalid_reason"]
    assert json.loads(linha["raw_payload"])["temperature_c"] == 120


def test_payload_nao_json_vai_como_texto(engine):
    assert handle_message(engine, TOPIC, b"lixo %%% nao json") == "invalida"
    with engine.connect() as conn:
        linha = conn.execute(select(sensor_readings)).mappings().one()
    assert linha["raw_payload"] == "lixo %%% nao json" and linha["ts"] is None and linha["is_valid"] == 0


def test_mensagem_ruim_nunca_derruba(engine, monkeypatch, caplog):
    for ruim in (b"", b"\xff\xff", b"null", b"[]", b"{" * 5000, b'{"a": NaN}'):
        assert handle_message(engine, TOPIC, ruim) in ("invalida", "duplicada")
    import src.ingest_mqtt as ing

    def explode(*args, **kwargs):
        raise RuntimeError("banco fora do ar")

    monkeypatch.setattr(ing, "insert_reading", explode)
    with caplog.at_level(logging.ERROR, logger="ingest_mqtt"):
        assert handle_message(engine, TOPIC, json.dumps(payload()).encode()) == "erro"
    assert any("erro ao processar" in m for m in caplog.messages)


def test_cliente_usa_api_v2_e_assina_qos1(engine):
    from paho.mqtt.enums import CallbackAPIVersion

    cliente = build_client(engine)
    assert cliente._callback_api_version == CallbackAPIVersion.VERSION2
    assert cliente.on_connect is not None and cliente.on_message is not None


def leitura(station, ts, temp=28.0, umid=70.0, chuva=0.0, bateria=3.9, valida=True):
    return {"station_id": station, "ts": pd.Timestamp(ts), "temperature_c": temp, "relative_humidity": umid,
            "rainfall_mm": chuva, "battery_voltage": bateria, "is_valid": valida}


def test_semana_comeca_no_domingo_em_recife():
    ts = pd.Series(pd.to_datetime(["2025-03-02T02:30:00", "2025-03-02T03:00:00", "2025-03-03T12:00:00",
                                   "2025-03-09T02:59:00", "2025-03-09T03:00:00"]))
    esperado = ["2025-02-23", "2025-03-02", "2025-03-02", "2025-03-02", "2025-03-09"]
    assert [d.isoformat() for d in week_start_recife(ts)] == esperado


def test_agregacao_borda_de_fuso_e_chuva_somada(engine):
    mensagens = [
        payload(timestamp="2025-03-02T02:30:00Z", temperature_c=30, relative_humidity=60, rainfall_mm=2.0,
                battery_voltage=3.8),
        payload(timestamp="2025-02-26T15:00:00Z", temperature_c=26, relative_humidity=80, rainfall_mm=1.5,
                battery_voltage=3.9),
        payload(timestamp="2025-03-02T03:30:00Z", temperature_c=24, relative_humidity=90, rainfall_mm=4.0,
                battery_voltage=3.7),
        payload(timestamp="2025-03-03T12:00:00Z", temperature_c=28, relative_humidity=70, rainfall_mm=0.5,
                battery_voltage=3.6),
        payload(timestamp="2025-03-04T12:00:00Z", temperature_c=999, rainfall_mm=50.0),
    ]
    for m in mensagens:
        corpo, topic = enviar(m)
        handle_message(engine, topic, corpo)
    semanal = run_agg(engine, MAPA).set_index("week_start")
    antiga = semanal.loc[pd.Timestamp("2025-02-23").date()]
    nova = semanal.loc[pd.Timestamp("2025-03-02").date()]
    assert antiga["n_leituras"] == 2
    assert antiga["chuva_mm"] == pytest.approx(3.5)
    assert antiga["temp_media"] == pytest.approx(28.0)
    assert antiga["umid_media"] == pytest.approx(70.0)
    assert antiga["bateria_min"] == pytest.approx(3.8)
    assert nova["n_leituras"] == 2
    assert nova["chuva_mm"] == pytest.approx(4.5)
    assert nova["bateria_min"] == pytest.approx(3.6)
    assert semanal["chuva_mm"].sum() == pytest.approx(8.0)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(sensor_weekly)).scalar() == 2


def test_agregacao_idempotente_e_recalcula(engine):
    for ts, chuva in (("2025-03-03T12:00:00Z", 1.0), ("2025-03-04T12:00:00Z", 2.0)):
        corpo, topic = enviar(payload(timestamp=ts, rainfall_mm=chuva))
        handle_message(engine, topic, corpo)
    primeiro = run_agg(engine, MAPA)
    segundo = run_agg(engine, MAPA)
    pd.testing.assert_frame_equal(primeiro, segundo)
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(sensor_weekly)).scalar() == 1
    corpo, topic = enviar(payload(timestamp="2025-03-05T12:00:00Z", rainfall_mm=4.0))
    handle_message(engine, topic, corpo)
    terceiro = run_agg(engine, MAPA)
    assert terceiro["chuva_mm"].iloc[0] == pytest.approx(7.0) and terceiro["n_leituras"].iloc[0] == 3
    with engine.connect() as conn:
        assert conn.execute(select(func.count()).select_from(sensor_weekly)).scalar() == 1
        assert conn.execute(select(sensor_weekly.c.chuva_mm)).scalar() == pytest.approx(7.0)


def test_estacao_sem_bairro_e_ignorada_com_aviso(engine, caplog):
    corpo, topic = enviar(payload(station_id="sem-bairro"), "antecedengue/estacoes/sem-bairro/leituras")
    handle_message(engine, topic, corpo)
    corpo, topic = enviar(payload())
    handle_message(engine, topic, corpo)
    with caplog.at_level(logging.WARNING, logger="sensor_agg"):
        semanal = run_agg(engine, MAPA)
    assert list(semanal["bairro"]) == ["BOA VIAGEM"]
    assert any("sem-bairro" in m and "sem bairro mapeado" in m for m in caplog.messages)


def test_agregacao_sem_leituras_validas(engine):
    handle_message(engine, TOPIC, b"lixo")
    assert run_agg(engine, MAPA).empty


def test_agregacao_duas_estacoes_no_mesmo_bairro():
    leituras = pd.DataFrame([leitura("a", "2025-03-03T12:00:00", temp=20, chuva=1.0),
                             leitura("b", "2025-03-03T13:00:00", temp=30, chuva=2.0, bateria=3.1)])
    semanal = aggregate_weekly(leituras, {"a": "PINA", "b": "PINA"})
    assert len(semanal) == 1
    assert semanal["temp_media"].iloc[0] == pytest.approx(25.0)
    assert semanal["chuva_mm"].iloc[0] == pytest.approx(3.0)
    assert semanal["bateria_min"].iloc[0] == pytest.approx(3.1)


def test_valida_bairros_contra_o_painel():
    bairros = {"BOA VIAGEM", "VARZEA"}
    assert validate_station_map(MAPA, bairros) == MAPA
    with pytest.raises(StationConfigError, match="BOA VIAJEM"):
        validate_station_map({"x": "BOA VIAJEM"}, bairros)


def test_config_de_estacoes_confere_com_o_painel_real():
    painel = config.DATA_PROCESSED / "panel.csv"
    if not painel.exists():
        pytest.skip("data/processed/panel.csv não existe")
    mapa = load_station_map()
    assert mapa
    validate_station_map(mapa, panel_bairros(painel))


def broker_disponivel() -> bool:
    try:
        with socket.create_connection((config.MQTT_HOST, config.MQTT_PORT), timeout=1):
            return True
    except OSError:
        return False


@pytest.mark.integration
def test_integracao_com_mosquitto(tmp_path):
    if not broker_disponivel():
        pytest.skip(f"sem broker MQTT em {config.MQTT_HOST}:{config.MQTT_PORT}")
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion

    eng = create_engine(f"sqlite:///{(tmp_path / 'int.db').as_posix()}", connect_args={"check_same_thread": False})
    init_db(eng)
    estacao = f"teste-{int(time.time())}"
    topic = f"antecedengue/estacoes/{estacao}/leituras"
    cliente = build_client(eng, client_id=f"teste-ingestor-{estacao}")
    cliente.connect(config.MQTT_HOST, config.MQTT_PORT)
    cliente.loop_start()
    pub = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"teste-pub-{estacao}")
    pub.connect(config.MQTT_HOST, config.MQTT_PORT)
    pub.loop_start()
    time.sleep(1)
    valida = json.dumps(payload(station_id=estacao))
    invalida = json.dumps(payload(station_id=estacao, timestamp="2025-03-03T13:00:00Z", temperature_c=500))
    for corpo in (valida, valida, invalida, "nao e json"):
        pub.publish(topic, corpo, qos=1).wait_for_publish()
    for _ in range(50):
        with eng.connect() as conn:
            n = conn.execute(select(func.count()).select_from(sensor_readings)).scalar()
        if n >= 3:
            break
        time.sleep(0.2)
    pub.loop_stop()
    cliente.loop_stop()
    cliente.disconnect()
    with eng.connect() as conn:
        linhas = conn.execute(select(sensor_readings)).mappings().all()
    assert len(linhas) == 3
    assert sum(1 for linha in linhas if linha["is_valid"]) == 1
