import json
import re
from pathlib import Path

import pandas as pd
import pytest
import requests
from streamlit.testing.v1 import AppTest

import app.api_client as api_client
from app import data
from app.api_client import ApiClient, ApiError, ApiUnavailable
from src import config

DASHBOARD = Path(__file__).resolve().parent.parent / "app" / "dashboard.py"
GEOJSON = json.loads(data.GEOJSON_PATH.read_text(encoding="utf-8"))
BAIRROS = sorted(f["properties"]["bairro"] for f in GEOJSON["features"])


def prediction_payload(bairros=BAIRROS):
    itens = []
    for i, b in enumerate(bairros):
        alto = max(0.0, 1 - i / len(bairros))
        medio = min(1 - alto, 0.2)
        classe = 2 if alto > 0.5 else (1 if alto + medio > 0.4 else 0)
        itens.append({"bairro": b, "week_start": "2025-08-17", "target_week": "2025-08-24", "classe_prevista": classe,
                      "rotulo_previsto": data.CLASSES[classe], "prob_baixo": 1 - alto - medio, "prob_medio": medio,
                      "prob_alto": alto, "risk_score": 50 * medio + 100 * alto, "rank": i + 1})
    return {"week_start": "2025-08-17", "target_week": "2025-08-24", "total": len(itens), "classe": None, "top": None,
            "predictions": itens}


MODEL_INFO = {
    "name": "RandomForest", "version": "1", "alias": "champion", "source": "teste", "mlflow_run_id": "x",
    "sklearn_version_treino": "1.9.1", "sklearn_version_api": "1.9.1", "classes": data.CLASSES,
    "features": ["casos_t", "casos_mm4"], "thresholds": [0.0, 1.0],
    "train_period": {"inicio": "2015-03-01", "fim": "2025-02-02"}, "best_params": {},
    "validation_metrics": {"f1_macro": 0.599, "recall_alto": 0.511, "auc_macro": 0.838, "persistencia_f1_macro": 0.558,
                           "persistencia_recall_alto": 0.533},
    "test_metrics": {"f1_macro": 0.611, "recall_alto": 0.702, "auc_macro": 0.817, "persistencia_f1_macro": 0.570,
                     "persistencia_recall_alto": 0.652, "f1_diff_ic95": [0.021, 0.054]},
    "trained_at": None}

SENSOR_ITEMS = [
    {"bairro": "BOA VIAGEM", "week_start": "2025-08-03", "temp_media": 27.5, "umid_media": 70.0, "chuva_mm": 3.0,
     "n_leituras": 10, "bateria_min": 3.8},
    {"bairro": "BOA VIAGEM", "week_start": "2025-08-10", "temp_media": 28.0, "umid_media": 72.0, "chuva_mm": 0.0,
     "n_leituras": 12, "bateria_min": 3.7}]


class FakeResponse:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo
        self.text = json.dumps(corpo)

    def json(self):
        return self._corpo


def instalar_api(monkeypatch, sensor=SENSOR_ITEMS, predicoes=True, fora_do_ar=False):
    chamadas = []

    def falso_get(url, params=None, timeout=None):
        chamadas.append(url)
        if fora_do_ar:
            raise requests.ConnectionError("recusada")
        caminho = url.split("://", 1)[1].split("/", 1)[1]
        caminho = "/" + caminho
        if caminho == "/health":
            return FakeResponse(200, {"status": "ok"})
        if caminho == "/model":
            return FakeResponse(200, MODEL_INFO)
        if caminho == "/predictions/latest":
            if not predicoes:
                return FakeResponse(503, {"detail": "Arquivo de previsões não encontrado."})
            return FakeResponse(200, prediction_payload())
        if caminho == "/bairros":
            return FakeResponse(200, {"total": len(BAIRROS), "bairros": BAIRROS})
        if caminho.startswith("/bairros/"):
            nome = requests.utils.unquote(caminho.split("/bairros/")[1])
            previsao = next((p for p in prediction_payload()["predictions"] if p["bairro"] == nome), None)
            casos = [{"week_start": str(d.date()), "casos": i % 7} for i, d in
                     enumerate(pd.date_range("2025-02-23", periods=26, freq="7D"))]
            return FakeResponse(200, {"bairro": nome, "previsao": previsao, "casos_semanais": casos,
                                      "sensor_semanal": [], "nota": None})
        if caminho == "/sensor/weekly":
            return FakeResponse(200, {"total": len(sensor), "items": sensor, "nota": "x"})
        return FakeResponse(404, {"detail": "?"})

    monkeypatch.setattr(api_client.requests, "get", falso_get)
    return chamadas


@pytest.fixture(autouse=True)
def limpar_cache(monkeypatch):
    import streamlit as st

    st.cache_data.clear()
    monkeypatch.setenv("API_URL", "http://api.teste:9000")
    monkeypatch.delenv("SENSOR_FONTE", raising=False)
    yield
    st.cache_data.clear()


def rodar():
    return AppTest.from_file(str(DASHBOARD), default_timeout=60).run()


def test_formatacao_e_aviso_de_semanas():
    assert data.format_date("2025-08-17") == "17/08/2025"
    aviso = data.weeks_notice("2025-08-17", "2025-08-24")
    assert "17/08/2025" in aviso and "24/08/2025" in aviso
    assert "tempo real" in aviso and "diagnóstico" in aviso


def test_predictions_frame_ordenado_e_em_portugues():
    payload = prediction_payload()
    payload["predictions"] = list(reversed(payload["predictions"]))
    frame = data.predictions_frame(payload)
    assert list(frame["rank"]) == list(range(1, 95))
    assert set(frame["classe"]) <= {"Baixo", "Médio", "Alto"}
    assert data.predictions_frame({"predictions": []}).empty


def test_geojson_oficial_cobre_os_94_bairros_e_e_leve():
    assert len(GEOJSON["features"]) == 94 and len(set(BAIRROS)) == 94
    assert data.GEOJSON_PATH.stat().st_size < 3_000_000
    painel = config.PANEL_PATH
    if painel.exists():
        assert set(pd.read_csv(painel, usecols=["bairro"])["bairro"]) == set(BAIRROS)


def test_cobertura_e_map_ready():
    frame = data.predictions_frame(prediction_payload())
    cobertura = data.geojson_coverage(GEOJSON, frame)
    assert cobertura == {"sem_previsao": [], "sem_poligono": [], "casados": 94}
    assert data.map_ready(GEOJSON, frame) is True
    com_extra = pd.concat([frame, frame.iloc[[0]].assign(bairro="ATLANTIDA")], ignore_index=True)
    assert data.geojson_coverage(GEOJSON, com_extra)["sem_poligono"] == ["ATLANTIDA"]
    assert data.map_ready(GEOJSON, com_extra) is False
    assert data.map_ready(None, frame) is False
    assert data.map_ready(GEOJSON, frame.iloc[0:0]) is False


def test_contagem_ranking_e_rotulos():
    frame = data.predictions_frame(prediction_payload())
    assert sum(data.class_counts(frame).values()) == 94
    top = data.ranking_table(frame, 5)
    assert list(top.columns) == ["posição", "bairro", "classe", "índice de risco"] and len(top) == 5
    assert top["índice de risco"].is_monotonic_decreasing
    so_alto = data.ranking_table(frame, 200, ["Alto"])
    assert set(so_alto["classe"]) == {"Alto"} and 0 < len(so_alto) < 94
    assert data.ranking_table(frame, 5, ["Médio"])["classe"].eq("Médio").all()
    assert all("(" in r and r.endswith(")") for r in data.ranking_labels(top))
    assert data.ranking_labels(top).iloc[0].endswith("(Alto)")


def test_probabilidades_casos_e_sensor():
    item = prediction_payload()["predictions"][3]
    probs = data.probabilities_frame(item)
    assert list(probs["classe"]) == ["Baixo", "Médio", "Alto"]
    assert probs["probabilidade (%)"].sum() == pytest.approx(100.0)
    casos = data.cases_frame({"casos_semanais": [{"week_start": "2025-08-10", "casos": 3}]})
    assert casos["casos"].tolist() == [3] and str(casos["semana"].iloc[0].date()) == "2025-08-10"
    assert data.cases_frame({"casos_semanais": []}).empty
    frame = data.sensor_frame(SENSOR_ITEMS)
    assert list(frame.columns)[:2] == ["bairro", "semana"] and len(frame) == 2
    status = data.sensor_status(frame)
    assert status.loc[0, "última semana"] == "10/08/2025" and status.loc[0, "semanas com dados"] == 2
    assert status.loc[0, "bateria mínima (V)"] == pytest.approx(3.7)
    assert data.sensor_frame([]).empty and data.sensor_status(data.sensor_frame([])).empty


def test_sensor_de_teste_e_tabela_do_modelo():
    assert data.sensor_is_test("simulado") and data.sensor_is_test("Teste") and not data.sensor_is_test("real")
    assert not data.sensor_is_test(None)
    tabela = data.model_comparison_table(MODEL_INFO)
    assert tabela.loc[0, "RandomForest (teste)"] == "0.611" and tabela.loc[0, "Persistência (teste)"] == "0.570"
    assert tabela.loc[0, "Persistência (validação)"] == "0.558"
    sem_pers = json.loads(json.dumps(MODEL_INFO))
    del sem_pers["validation_metrics"]["persistencia_f1_macro"]
    assert data.model_comparison_table(sem_pers).loc[0, "Persistência (validação)"] == "—"
    assert "não inclui zero" in data.difference_sentence(MODEL_INFO)
    incerto = json.loads(json.dumps(MODEL_INFO))
    incerto["test_metrics"]["f1_diff_ic95"] = [-0.01, 0.05]
    assert "inclui zero" in data.difference_sentence(incerto) and "não inclui" not in data.difference_sentence(incerto)


def test_cliente_da_api(monkeypatch):
    instalar_api(monkeypatch)
    cliente = ApiClient("http://api.teste:9000/")
    assert cliente.bairros()["total"] == 94
    assert cliente.bairro("BOA VIAGEM")["bairro"] == "BOA VIAGEM"
    instalar_api(monkeypatch, predicoes=False)
    with pytest.raises(ApiError) as erro:
        ApiClient("http://api.teste:9000").predictions()
    assert erro.value.status == 503
    instalar_api(monkeypatch, fora_do_ar=True)
    with pytest.raises(ApiUnavailable) as fora:
        ApiClient("http://api.teste:9000").health()
    assert "http://api.teste:9000" in str(fora.value)


def test_dashboard_caminho_feliz(monkeypatch):
    instalar_api(monkeypatch)
    at = rodar()
    assert not at.exception and not at.error
    assert [t.label for t in at.tabs] == ["Mapa de risco", "Ranking", "Bairro", "Sensor", "Modelo"]
    avisos = " ".join(i.value for i in at.info)
    assert "17/08/2025" in avisos and "24/08/2025" in avisos and "não é monitoramento em tempo real" in avisos
    assert len(at.get("plotly_chart")) >= 5
    metricas = {m.label: m.value for m in at.metric}
    assert metricas["Modelo"] == "RandomForest" and metricas["Versão no Registry"] == "1 (champion)"
    html = " ".join(e.value for e in at.markdown if isinstance(e.value, str))
    assert "Bairros em risco Alto" in html and "Maior índice de risco" in html and "Top 5 bairros" in html
    for trecho in re.finditer("probabilidade de surto", html.lower()):
        assert "não" in html.lower()[max(0, trecho.start() - 8):trecho.start()]


def test_dashboard_interacoes(monkeypatch):
    instalar_api(monkeypatch)
    at = rodar()
    at.selectbox(key="bairro_sel").select(BAIRROS[10]).run()
    assert not at.exception
    assert any(m.label == "Posição no ranking" and m.value.startswith("11º") for m in at.metric)
    at.multiselect(key="rank_classes").set_value(["Alto"]).run()
    assert not at.exception
    at.text_input(key="rank_busca").set_value("boa vi").run()
    assert not at.exception
    assert any("Nenhum bairro" in i.value for i in at.info) or at.dataframe
    at.text_input(key="rank_busca").set_value("zzzz").run()
    assert any("Nenhum bairro encontrado" in i.value for i in at.info)
    at.text_input(key="rank_busca").set_value("").run()
    at.slider(key="rank_n").set_value(10).run()
    assert not at.exception


def test_sensor_sem_dados_explica(monkeypatch):
    instalar_api(monkeypatch, sensor=[])
    at = rodar()
    assert not at.exception
    assert any("ainda não enviaram leituras" in i.value for i in at.info)
    assert any("não alimentam o modelo" in i.value for i in at.info)


def test_sensor_de_teste_mostra_aviso(monkeypatch):
    monkeypatch.setenv("SENSOR_FONTE", "simulado")
    instalar_api(monkeypatch)
    at = rodar()
    assert not at.exception
    assert any("simulados ou de teste" in w.value for w in at.warning)


def test_api_fora_do_ar_mostra_mensagem_amigavel(monkeypatch):
    instalar_api(monkeypatch, fora_do_ar=True)
    at = rodar()
    assert not at.exception
    assert len(at.error) == 1
    mensagem = at.error[0].value
    assert "http://api.teste:9000" in mensagem and "ConnectionError" in mensagem
    assert any("uvicorn api.main:app" in m.value for m in at.markdown)
    assert len(at.tabs) == 0


def test_sem_predicoes_a_dashboard_continua(monkeypatch):
    instalar_api(monkeypatch, predicoes=False)
    at = rodar()
    assert not at.exception
    assert any("Arquivo de previsões não encontrado" in w.value for w in at.warning)
    assert len(at.tabs) == 5


def test_sem_geojson_cai_no_ranking(monkeypatch):
    instalar_api(monkeypatch)
    monkeypatch.setattr(data, "GEOJSON_PATH", Path("nao_existe.geojson"))
    monkeypatch.setattr(data, "load_geojson", lambda path=Path("nao_existe.geojson"): None)
    at = rodar()
    assert not at.exception
    assert any("Mostrando o ranking em barras" in w.value for w in at.warning)


def test_formatacao_e_componentes_visuais():
    from app import ui

    assert ui.fmt_num(73.44) == "73,4" and ui.fmt_num(100) == "100,0" and ui.fmt_num(5.678, 2) == "5,68"
    assert ui.class_label("Alto") == "▲ Alto" and ui.class_label("Médio") == "● Médio" and ui.class_label("Baixo") == "▼ Baixo"
    assert "▲ Alto" in ui.class_chip("Alto")
    assert ui.risk_color(0) == ui.RISK_SCALE[0] and ui.risk_color(100) == ui.RISK_SCALE[-1]
    assert ui.risk_color(-5) == ui.risk_color(0) and ui.risk_color(500) == ui.risk_color(100)
    assert ui.esc("<b>x</b>") == "&lt;b&gt;x&lt;/b&gt;"
    assert "&lt;script&gt;" in ui.kpi_card("r", "<script>")


def test_hero_e_selos():
    from app import ui

    topo = ui.hero("2025-08-17", "2025-08-24", simulated=True)
    assert "AnteceDengue" in topo and "24/08/2025" in topo and "17/08/2025" in topo and "Dados simulados" in topo
    assert "Dados simulados" not in ui.hero("2025-08-17", "2025-08-24")
    assert "Previsão para a semana" not in ui.hero()
    assert chr(10) not in topo


def test_painel_top_cartoes_e_tabela_do_ranking():
    from app import ui

    frame = data.predictions_frame(prediction_payload())
    top = ui.top_panel(frame, 5)
    assert top.count('class="top-item"') == 5 and "Top 5 bairros" in top and "não calibrado" in top and chr(10) not in top
    cartoes = ui.summary_cards(frame, "2025-08-17", "2025-08-24")
    assert "Bairros em risco Baixo" in cartoes and "24/08/2025" in cartoes and "índice" in cartoes
    visao = ui.ranking_view(data.ranking_table(frame, 3))
    assert list(visao.columns) == ["Posição", "Bairro", "Classe", "Índice (0 a 100)", "Barra"]
    assert visao["Classe"].str.contains("Alto|Médio|Baixo").all() and "," in visao["Índice (0 a 100)"].iloc[0]


def test_busca_por_bairro_ignora_acentos_e_caixa():
    frame = data.predictions_frame(prediction_payload(["BOA VIAGEM", "SÃO JOSÉ", "VARZEA"]))
    tabela = data.ranking_table(frame, 10)
    assert list(data.filter_by_name(tabela, "boa v")["bairro"]) == ["BOA VIAGEM"]
    assert list(data.filter_by_name(tabela, "sao jose")["bairro"]) == ["SÃO JOSÉ"]
    assert len(data.filter_by_name(tabela, "  ")) == 3 and len(data.filter_by_name(tabela, None)) == 3
    assert data.filter_by_name(tabela, "zzz").empty
